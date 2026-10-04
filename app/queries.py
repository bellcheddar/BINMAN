"""The query object parser and executor (spec 6.1).

Deterministic. No language model is involved at any point: BINMAN-LM's only job
is to *propose* a query object, and this module is what validates and runs it.
The same parser validates every generated training pair in Phase 3, which is
what gives the Task A corpus zero label noise by construction (spec 3.2).

A query object:

    {
      "record_type": "bridge",
      "filters": [
        {"field": "bridging_balance", "op": "gte", "value": 0.5},
        {"field": "ccd_class", "op": "eq", "value": "glue_candidate"}
      ],
      "sort": {"field": "dsasa_total", "direction": "desc"},
      "limit": 100
    }

Everything is closed-world: an unknown record type, field, operator or
enumerated value is an error with a message naming what was allowed. That is
deliberate, because it is also the signal the LM is trained against.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Iterable, Sequence

# Six operators, exactly as spec 3.2 enumerates them.
OPERATORS: dict[str, str] = {
    "eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
}

MAX_LIMIT = 5000
DEFAULT_LIMIT = 200


@dataclass(frozen=True)
class FieldSpec:
    """One filterable column: its type, its label and its closed vocabulary."""

    name: str
    kind: str                     # "number" | "text" | "enum" | "bool"
    label: str
    unit: str = ""
    enum: tuple[str, ...] = ()
    description: str = ""

    def coerce(self, value: Any) -> Any:
        if self.kind == "number":
            if isinstance(value, bool):
                raise QueryError(f"field '{self.name}' takes a number, got a boolean")
            try:
                return float(value)
            except (TypeError, ValueError):
                raise QueryError(
                    f"field '{self.name}' takes a number{f' in {self.unit}' if self.unit else ''}, "
                    f"got {value!r}"
                ) from None
        if self.kind == "bool":
            if isinstance(value, bool):
                return int(value)
            if str(value).lower() in {"1", "true", "yes"}:
                return 1
            if str(value).lower() in {"0", "false", "no"}:
                return 0
            raise QueryError(f"field '{self.name}' takes a boolean, got {value!r}")
        text = str(value)
        if self.kind == "enum" and self.enum and text not in self.enum:
            raise QueryError(
                f"field '{self.name}' takes one of {list(self.enum)}, got {text!r}"
            )
        return text


@dataclass(frozen=True)
class RecordType:
    """One queryable record type, mapped to its table and its default sort."""

    name: str
    table: str
    label: str
    fields: dict[str, FieldSpec]
    default_sort: str
    # Which way the default sort runs. A rank field counts upward from the best,
    # so sorting it descending shows the worst record first, which is what the
    # E3 Triage table did before this was named per record type.
    default_direction: str
    default_columns: tuple[str, ...]
    identity_columns: tuple[str, ...]   # what "the same row set" means for set equality


class QueryError(ValueError):
    """A query object that is not valid against the schema."""


# --------------------------------------------------------------------------- #
# the schema: enumerated from spec Section 7, with vocabularies filled from the
# built database at runtime by `refresh_vocabularies`
# --------------------------------------------------------------------------- #

CCD_CLASSES = (
    "glue_candidate", "cofactor", "metal", "cryoprotectant", "buffer",
    "detergent", "lipid", "sugar", "peptide_like", "covalent_modifier", "unknown",
)
EVIDENCE_CLASSES = (
    "molecular_glue", "protac", "bivalent_inhibitor", "native_cofactor",
    "crystallisation_artefact",
)
VERDICTS = ("favourable", "marginal", "unfavourable")
EXPLOITATION = (
    "clinically validated", "chemically validated", "covalent handle only",
    "ligandable unproven", "orphan",
)


def _bridge_fields() -> dict[str, FieldSpec]:
    specs = [
        FieldSpec("pdb_id", "text", "PDB ID", description="RCSB entry identifier"),
        FieldSpec("ccd_id", "text", "Ligand CCD", description="chemical component identifier"),
        FieldSpec("ccd_class", "enum", "Ligand class", enum=CCD_CLASSES,
                  description="spec 4.3 classification"),
        FieldSpec("evidence_class", "enum", "Evidence class", enum=EVIDENCE_CLASSES,
                  description="LM Task B label"),
        FieldSpec("dsasa_a", "number", "ΔSASA chain A", unit="Å²"),
        FieldSpec("dsasa_b", "number", "ΔSASA chain B", unit="Å²"),
        FieldSpec("dsasa_total", "number", "ΔSASA total", unit="Å²"),
        FieldSpec("bridging_balance", "number", "Bridging balance",
                  description="min/max of the two buried areas, 0 to 1"),
        FieldSpec("buried_fraction", "number", "Buried fraction",
                  description="fraction of the ligand surface buried, 0 to 1"),
        FieldSpec("contacts_a", "number", "Contacts chain A"),
        FieldSpec("contacts_b", "number", "Contacts chain B"),
        FieldSpec("heavy_atoms", "number", "Ligand heavy atoms"),
        FieldSpec("symmetry_mediated", "bool", "Symmetry mediated"),
        FieldSpec("novel_bridge", "bool", "Novel bridge",
                  description="passes every filter and is in no curated glue database"),
        FieldSpec("resolution", "number", "Resolution", unit="Å",
                  description="from the entry table"),
        FieldSpec("method", "text", "Experimental method"),
        FieldSpec("organism", "text", "Source organism"),
        FieldSpec("release_date", "text", "Release date", description="ISO date"),
        FieldSpec("mw", "number", "Ligand MW", unit="Da"),
        FieldSpec("tier", "number", "Priority tier"),
    ]
    return {spec.name: spec for spec in specs}


def _degron_fields() -> dict[str, FieldSpec]:
    specs = [
        FieldSpec("uniprot_acc", "text", "UniProt accession"),
        FieldSpec("gene", "text", "Gene symbol"),
        FieldSpec("afdb_id", "text", "AlphaFold DB identifier"),
        FieldSpec("tip_res", "number", "Tip residue number"),
        FieldSpec("tip_aa", "text", "Tip residue type"),
        FieldSpec("turn_length", "number", "Turn length", unit="residues"),
        FieldSpec("mean_plddt", "number", "Mean pLDDT", description="tip region, 0 to 100"),
        FieldSpec("tip_rel_sasa", "number", "Tip relative SASA", description="0 to 1"),
        FieldSpec("degron_geometry_score", "number", "Degron geometry score",
                  description="a geometric filter rank, not a calibrated probability"),
        FieldSpec("imid_degradation_score", "number", "IMiD degradation score",
                  description=("predicted probability that this C2H2 zinc finger "
                               "is degraded by pomalidomide; empty where the "
                               "candidate carries no zinc finger")),
        FieldSpec("motif_family", "text", "Motif family"),
        FieldSpec("is_known_neosubstrate", "bool", "Known neosubstrate"),
    ]
    return {spec.name: spec for spec in specs}


def _ligase_fields() -> dict[str, FieldSpec]:
    specs = [
        FieldSpec("uniprot_acc", "text", "UniProt accession"),
        FieldSpec("gene", "text", "Gene symbol"),
        FieldSpec("family", "text", "Ligase family"),
        FieldSpec("subfamily", "text", "Subfamily"),
        FieldSpec("pdb_entries", "number", "PDB entries"),
        FieldSpec("pocket_score", "number", "Pocket druggability score",
                  description="fpocket top pocket"),
        FieldSpec("pocket_volume_a3", "number", "Pocket volume", unit="Å³"),
        FieldSpec("has_ligand", "bool", "Has a drug-like ligand"),
        FieldSpec("expression_breadth", "number", "Expression breadth",
                  unit="tissues", description="tissues above the expression threshold"),
        FieldSpec("tumour_enriched", "bool", "Tumour enriched"),
        FieldSpec("substrate_count", "number", "Curated substrate count"),
        FieldSpec("substrate_count_predicted", "number", "Predicted substrate count"),
        FieldSpec("exploitation_status", "enum", "Exploitation status", enum=EXPLOITATION),
        FieldSpec("triage_score", "number", "Triage score"),
        FieldSpec("triage_rank", "number", "Triage rank", description="1 is best"),
    ]
    return {spec.name: spec for spec in specs}


def _lysine_fields() -> dict[str, FieldSpec]:
    specs = [
        FieldSpec("uniprot_acc", "text", "UniProt accession"),
        FieldSpec("structure_id", "text", "Structure identifier"),
        FieldSpec("site_id", "text", "Site definition"),
        FieldSpec("res_num", "number", "Lysine residue number"),
        FieldSpec("nz_rel_sasa", "number", "NZ relative SASA", description="0 to 1"),
        FieldSpec("cb_cb_distance", "number", "Cβ–Cβ distance", unit="Å"),
        FieldSpec("nz_centroid_distance", "number", "NZ to site centroid", unit="Å"),
        FieldSpec("verdict", "enum", "Reach verdict", enum=VERDICTS),
        FieldSpec("observed_diGly", "bool", "Observed diGly site"),
    ]
    return {spec.name: spec for spec in specs}


# Bridge queries join the entry and ligand tables, so the FROM clause is a view
# rather than a bare table. Every other record type is a single table.
RECORD_TYPES: dict[str, RecordType] = {
    "bridge": RecordType(
        name="bridge", label="Glue Atlas",
        table=(
            "(SELECT b.*, e.resolution, e.method, e.organism, e.release_date, e.tier, "
            "l.mw, l.name AS ligand_name "
            "FROM bridge b "
            "LEFT JOIN entry e ON e.pdb_id = b.pdb_id "
            "LEFT JOIN ligand l ON l.ccd_id = b.ccd_id)"
        ),
        fields=_bridge_fields(), default_sort="dsasa_total",
        default_direction="desc",
        default_columns=(
            "pdb_id", "ccd_id", "ccd_class", "chain_a", "chain_b", "dsasa_a", "dsasa_b",
            "dsasa_total", "bridging_balance", "buried_fraction", "resolution",
        ),
        identity_columns=("id",),
    ),
    "degron": RecordType(
        name="degron", label="Degron Scan", table="degron",
        fields=_degron_fields(), default_sort="degron_geometry_score",
        default_direction="desc",
        default_columns=(
            "uniprot_acc", "gene", "tip_res", "tip_aa", "turn_length",
            "mean_plddt", "tip_rel_sasa", "degron_geometry_score",
            "imid_degradation_score",
        ),
        identity_columns=("id",),
    ),
    "ligase": RecordType(
        name="ligase", label="E3 Triage", table="ligase",
        fields=_ligase_fields(), default_sort="triage_rank",
        default_direction="asc",      # rank 1 is the best ligase
        default_columns=(
            "gene", "uniprot_acc", "family", "pdb_entries", "pocket_score",
            "pocket_volume_a3", "substrate_count", "exploitation_status", "triage_rank",
        ),
        identity_columns=("uniprot_acc",),
    ),
    "lysine": RecordType(
        name="lysine", label="Degradability", table="lysine",
        fields=_lysine_fields(), default_sort="nz_centroid_distance",
        default_direction="asc",      # closest to the site first
        default_columns=(
            "uniprot_acc", "structure_id", "site_id", "res_num", "nz_rel_sasa",
            "cb_cb_distance", "nz_centroid_distance", "verdict",
        ),
        identity_columns=("id",),
    ),
}

# Sort direction is closed too, so a corrupted value is caught rather than
# silently defaulting.
DIRECTIONS = ("asc", "desc")


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #

@dataclass
class Filter:
    field: str
    op: str
    value: Any

    def as_dict(self) -> dict:
        return {"field": self.field, "op": self.op, "value": self.value}

    def describe(self, spec: FieldSpec) -> str:
        """A readable line for the query stack, which pastes into a methods section."""
        words = {
            "eq": "is", "ne": "is not", "gt": "above", "gte": "at least",
            "lt": "below", "lte": "at most",
        }
        unit = f" {spec.unit}" if spec.unit else ""
        if spec.kind == "bool":
            return f"{spec.label} {'yes' if self.value else 'no'}"
        return f"{spec.label} {words[self.op]} {self.value}{unit}"


@dataclass
class Query:
    record_type: str
    filters: list[Filter] = dataclass_field(default_factory=list)
    sort_field: str | None = None
    sort_direction: str = "desc"
    limit: int = DEFAULT_LIMIT

    @property
    def spec(self) -> RecordType:
        return RECORD_TYPES[self.record_type]

    def as_dict(self) -> dict:
        out: dict[str, Any] = {
            "record_type": self.record_type,
            "filters": [f.as_dict() for f in self.filters],
        }
        if self.sort_field:
            out["sort"] = {"field": self.sort_field, "direction": self.sort_direction}
        out["limit"] = self.limit
        return out

    def describe(self) -> list[str]:
        spec = self.spec
        lines = [f"Record type: {spec.label}"]
        lines += [f.describe(spec.fields[f.field]) for f in self.filters]
        if self.sort_field:
            field_spec = spec.fields.get(self.sort_field)
            label = field_spec.label if field_spec else self.sort_field
            lines.append(
                f"Sorted by {label}, "
                f"{'highest first' if self.sort_direction == 'desc' else 'lowest first'}"
            )
        return lines


def parse(payload: Any) -> Query:
    """Validate a query object. Raises QueryError with a message naming what was allowed."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise QueryError(f"not valid JSON: {exc}") from None
    if not isinstance(payload, dict):
        raise QueryError("a query object must be a JSON object")

    record_type = payload.get("record_type")
    if record_type not in RECORD_TYPES:
        raise QueryError(
            f"record_type must be one of {list(RECORD_TYPES)}, got {record_type!r}"
        )
    spec = RECORD_TYPES[record_type]

    raw_filters = payload.get("filters", [])
    if raw_filters is None:
        raw_filters = []
    if not isinstance(raw_filters, list):
        raise QueryError("filters must be a list")

    filters: list[Filter] = []
    for index, item in enumerate(raw_filters):
        if not isinstance(item, dict):
            raise QueryError(f"filters[{index}] must be an object")
        name = item.get("field")
        if name not in spec.fields:
            raise QueryError(
                f"filters[{index}]: field {name!r} is not a field of {record_type}. "
                f"Allowed: {sorted(spec.fields)}"
            )
        op = item.get("op")
        if op not in OPERATORS:
            raise QueryError(
                f"filters[{index}]: op must be one of {list(OPERATORS)}, got {op!r}"
            )
        if "value" not in item:
            raise QueryError(f"filters[{index}]: a value is required")
        field_spec = spec.fields[name]
        # Ordering operators on free text are almost always a mistake, and on an
        # enum they are meaningless, so both are refused rather than guessed at.
        if field_spec.kind in {"enum", "bool"} and op not in {"eq", "ne"}:
            raise QueryError(
                f"filters[{index}]: field '{name}' is a {field_spec.kind} and only "
                f"supports eq or ne, got {op!r}"
            )
        filters.append(Filter(field=name, op=op, value=field_spec.coerce(item["value"])))

    sort_field = None
    sort_direction = "desc"
    sort = payload.get("sort")
    if sort is not None:
        if not isinstance(sort, dict):
            raise QueryError("sort must be an object with 'field' and 'direction'")
        sort_field = sort.get("field")
        if sort_field not in spec.fields:
            raise QueryError(
                f"sort.field {sort_field!r} is not a field of {record_type}. "
                f"Allowed: {sorted(spec.fields)}"
            )
        sort_direction = str(sort.get("direction", "desc")).lower()
        if sort_direction not in DIRECTIONS:
            raise QueryError(f"sort.direction must be one of {list(DIRECTIONS)}")

    limit = payload.get("limit", DEFAULT_LIMIT)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise QueryError(f"limit must be an integer, got {limit!r}") from None
    if limit < 1:
        raise QueryError("limit must be at least 1")
    limit = min(limit, MAX_LIMIT)

    return Query(
        record_type=record_type, filters=filters,
        sort_field=sort_field or spec.default_sort,
        sort_direction=sort_direction if sort is not None else spec.default_direction,
        limit=limit,
    )


# --------------------------------------------------------------------------- #
# execution
# --------------------------------------------------------------------------- #

def build_sql(query: Query, columns: Sequence[str] | None = None) -> tuple[str, list]:
    """Render a validated query to parameterised SQL.

    Every identifier here has already been checked against the schema, so no
    user string reaches the SQL text: values are always bound parameters.
    """
    spec = query.spec
    chosen = list(columns) if columns else list(spec.default_columns)
    for name in chosen:
        if name not in spec.fields and name not in spec.identity_columns \
                and name not in {"id", "chain_a", "chain_b", "ligand_name",
                                 "structure_file", "title"}:
            raise QueryError(f"column {name!r} is not selectable for {spec.name}")
    select = ", ".join(["id"] if "id" in spec.identity_columns else list(spec.identity_columns))
    for name in chosen:
        if name not in select.split(", "):
            select += f", {name}"

    where: list[str] = ["status = 'ok'"] if spec.name != "bridge" else ["b.status = 'ok'"]
    if spec.name == "bridge":
        where = ["status = 'ok'"]
    params: list = []
    for item in query.filters:
        where.append(f"{item.field} {OPERATORS[item.op]} ?")
        params.append(item.value)

    sql = (
        f"SELECT {select} FROM {spec.table} "
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY {query.sort_field} {query.sort_direction.upper()} "
        f"LIMIT ?"
    )
    params.append(query.limit)
    return sql, params


def execute(connection: sqlite3.Connection, query: Query,
            columns: Sequence[str] | None = None) -> list[dict]:
    sql, params = build_sql(query, columns)
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def count(connection: sqlite3.Connection, query: Query) -> int:
    spec = query.spec
    where = ["status = 'ok'"]
    params: list = []
    for item in query.filters:
        where.append(f"{item.field} {OPERATORS[item.op]} ?")
        params.append(item.value)
    sql = f"SELECT COUNT(*) FROM {spec.table} WHERE {' AND '.join(where)}"
    return int(connection.execute(sql, params).fetchone()[0])


def row_identity_set(connection: sqlite3.Connection, query: Query) -> frozenset:
    """The identity of the returned row set, for the spec 3.8 set-equality metric.

    Two syntactically different queries that select the same rows are both
    correct, so the metric compares row identities rather than SQL text. The
    sort order and the limit are deliberately ignored: a query's *answer* is the
    set of records it selects.
    """
    spec = query.spec
    where = ["status = 'ok'"]
    params: list = []
    for item in query.filters:
        where.append(f"{item.field} {OPERATORS[item.op]} ?")
        params.append(item.value)
    identity = ", ".join(spec.identity_columns)
    sql = f"SELECT {identity} FROM {spec.table} WHERE {' AND '.join(where)}"
    cursor = connection.execute(sql, params)
    return frozenset(tuple(row) for row in cursor.fetchall())


# --------------------------------------------------------------------------- #
# vocabularies, read from the built database so the LM corpus is grounded
# --------------------------------------------------------------------------- #

def refresh_vocabularies(connection: sqlite3.Connection) -> dict[str, list[str]]:
    """Read the real closed vocabularies out of the atlas (spec 3.2).

    The generated Task A corpus must use values that exist, so these come from
    the database rather than from a hand-written list.
    """
    vocabularies: dict[str, list[str]] = {}
    probes = {
        "ccd_id": "SELECT DISTINCT ccd_id FROM ligand WHERE ccd_class = 'glue_candidate' LIMIT 4000",
        "ccd_class": "SELECT DISTINCT ccd_class FROM ligand",
        "ligase_gene": "SELECT DISTINCT gene FROM ligase WHERE gene IS NOT NULL AND gene != ''",
        "ligase_acc": "SELECT DISTINCT uniprot_acc FROM ligase",
        "ligase_family": "SELECT DISTINCT family FROM ligase WHERE family IS NOT NULL AND family != ''",
        "verdict": "SELECT DISTINCT verdict FROM lysine WHERE verdict IS NOT NULL",
        "evidence_class": "SELECT DISTINCT evidence_class FROM bridge WHERE evidence_class IS NOT NULL",
        "motif_family": "SELECT DISTINCT motif_family FROM degron WHERE motif_family IS NOT NULL",
        "method": "SELECT DISTINCT method FROM entry WHERE method IS NOT NULL AND method != ''",
    }
    for name, sql in probes.items():
        try:
            rows = connection.execute(sql).fetchall()
        except sqlite3.Error:
            vocabularies[name] = []
            continue
        vocabularies[name] = sorted({str(row[0]) for row in rows if row[0] is not None})
    return vocabularies


def schema_summary() -> dict:
    """The schema as data, for the UI query builder and the LM corpus generator."""
    return {
        name: {
            "label": spec.label,
            "default_sort": spec.default_sort,
            "default_direction": spec.default_direction,
            "default_columns": list(spec.default_columns),
            "fields": {
                field_name: {
                    "kind": field_spec.kind, "label": field_spec.label,
                    "unit": field_spec.unit, "enum": list(field_spec.enum),
                    "description": field_spec.description,
                }
                for field_name, field_spec in spec.fields.items()
            },
        }
        for name, spec in RECORD_TYPES.items()
    }
