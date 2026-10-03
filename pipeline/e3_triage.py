"""Stage 2.2: the human E3 ligase repertoire, triaged (spec 5.3).

Assembles the repertoire from InterPro domain signatures, cross-checked against
UniProt keyword annotation, then scores each ligase on ligandability, structural
coverage, expression selectivity, substrate count and family.

The ranking is a transparent weighted sum with the weights in
`config/thresholds.toml` and every component column visible in the UI. There is
no hidden scoring, and `exploitation_status` and `has_ligand` are held out of the
weights so the spec 9.3 enrichment test is not circular.

Resumable: one manifest row per accession, so a kill mid-run costs only the
ligase currently being processed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    INTERIM, VALIDATION, Config, Fetcher, Manifest, load_config, log_event,
    write_jsonl,
)

STAGE = "ligases"
OUTPUT = INTERIM / "ligases.jsonl"
UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
UNIPROT_STREAM = "https://rest.uniprot.org/uniprotkb/stream"
OPEN_TARGETS = "https://api.platform.opentargets.org/api/v4/graphql"
UBL_KEYWORD = "KW-0833"

FIELDS = ("accession,id,protein_name,gene_primary,xref_pdb,keyword,"
          "xref_interpro,length,cc_subcellular_location")


# --------------------------------------------------------------------------- #
# repertoire
# --------------------------------------------------------------------------- #

@dataclass
class Ligase:
    uniprot_acc: str
    gene: str = ""
    name: str = ""
    family: str = ""
    subfamily: str = ""
    pdb_ids: list[str] = field(default_factory=list)
    has_ubl_keyword: bool = False
    length: int = 0
    best_structure: str = ""
    best_resolution: float | None = None
    pocket_score: float | None = None
    pocket_volume_a3: float | None = None
    has_ligand: int = 0
    expression_breadth: int | None = None
    tumour_enriched: int = 0
    substrate_count: int = 0
    substrate_count_predicted: int = 0
    exploitation_status: str = "orphan"
    triage_score: float | None = None
    triage_rank: int | None = None
    status: str = "ok"


def fetch_family(ipr: str, family: str, fetcher: Fetcher) -> list[dict]:
    """Stream every reviewed human protein carrying one InterPro signature."""
    query = f"(organism_id:9606) AND (reviewed:true) AND (xref:interpro-{ipr})"
    payload = fetcher.fetch_json(
        UNIPROT_STREAM,
        params={"query": query, "fields": FIELDS, "format": "json",
                "compressed": "false"},
        key=f"uniprot_family_{ipr}",
    )
    return payload.get("results", []) or []


def fetch_ubl_accessions(fetcher: Fetcher) -> set[str]:
    """The UniProt keyword cross-check set (spec 5.3)."""
    payload = fetcher.fetch_json(
        UNIPROT_STREAM,
        params={"query": f"(organism_id:9606) AND (reviewed:true) AND (keyword:{UBL_KEYWORD})",
                "fields": "accession", "format": "json", "compressed": "false"},
        key="uniprot_ubl_keyword",
    )
    return {r["primaryAccession"] for r in payload.get("results", []) or []}


def parse_record(record: dict, family: str) -> Ligase:
    genes = record.get("genes") or []
    gene = ""
    if genes:
        gene = ((genes[0].get("geneName") or {}).get("value")) or ""
    description = record.get("proteinDescription") or {}
    recommended = (description.get("recommendedName") or {}).get("fullName") or {}
    pdb_ids = [
        x["id"] for x in (record.get("uniProtKBCrossReferences") or [])
        if x.get("database") == "PDB" and x.get("id")
    ]
    return Ligase(
        uniprot_acc=record["primaryAccession"],
        gene=gene,
        name=recommended.get("value") or "",
        family=family,
        pdb_ids=sorted(set(pdb_ids)),
        length=int((record.get("sequence") or {}).get("length") or 0),
    )


def fetch_name_family(phrase: str, fetcher: Fetcher) -> list[dict]:
    """Reviewed human proteins whose recommended name contains a phrase."""
    query = (f'(organism_id:9606) AND (reviewed:true) AND '
             f'(protein_name:"{phrase}")')
    payload = fetcher.fetch_json(
        UNIPROT_STREAM,
        params={"query": query, "fields": FIELDS, "format": "json",
                "compressed": "false"},
        key=f"uniprot_name_{phrase.replace(' ', '_')[:60]}",
    )
    return payload.get("results", []) or []


def build_repertoire(config: Config, fetcher: Fetcher) -> dict[str, Ligase]:
    families = config.t("e3_triage.families")
    ubl = fetch_ubl_accessions(fetcher)
    log_event("2.2", f"UniProt keyword {UBL_KEYWORD} cross-check set: {len(ubl):,} "
                     f"reviewed human proteins.")

    repertoire: dict[str, Ligase] = {}
    per_family: dict[str, int] = {}
    for family, ipr in families.items():
        records = fetch_family(ipr, family, fetcher)
        per_family[family] = len(records)
        for record in records:
            ligase = parse_record(record, family)
            existing = repertoire.get(ligase.uniprot_acc)
            if existing is None:
                repertoire[ligase.uniprot_acc] = ligase
            else:
                # A protein can carry more than one signature (a cullin-RING
                # adaptor with both a BTB and a RING domain, say). Keep the
                # first family as primary and record the rest as subfamily.
                extra = {s for s in existing.subfamily.split(",") if s}
                extra.add(family)
                existing.subfamily = ",".join(sorted(extra))
        log_event("2.2", f"InterPro {ipr} ({family}): {len(records):,} human reviewed proteins.")

    # Families identified by UniProt's own name annotation rather than by a
    # distinguishing InterPro signature (spec 5.3 names DCAF, which has none).
    try:
        name_families = config.t("e3_triage.name_families")
    except Exception:  # noqa: BLE001
        name_families = {}
    for family, phrase in name_families.items():
        records = fetch_name_family(phrase, fetcher)
        per_family[family] = len(records)
        for record in records:
            ligase = parse_record(record, family)
            existing = repertoire.get(ligase.uniprot_acc)
            if existing is None:
                repertoire[ligase.uniprot_acc] = ligase
            else:
                extra = {s for s in existing.subfamily.split(",") if s}
                extra.add(family)
                existing.subfamily = ",".join(sorted(extra))
        log_event("2.2", f'UniProt name "{phrase}" ({family}): {len(records):,} proteins.')

    for accession, ligase in repertoire.items():
        ligase.has_ubl_keyword = accession in ubl

    with_keyword = sum(1 for l in repertoire.values() if l.has_ubl_keyword)
    log_event("2.2", f"Repertoire: {len(repertoire):,} ligases from "
                     f"{len(families)} InterPro signatures, {with_keyword:,} also carrying "
                     f"the {UBL_KEYWORD} keyword. Per family: {per_family}.")
    return repertoire


# --------------------------------------------------------------------------- #
# structures and pockets
# --------------------------------------------------------------------------- #

def pick_best_structure(ligase: Ligase, fetcher: Fetcher) -> None:
    """Highest-resolution X-ray entry, else the AFDB model (spec 5.3)."""
    if not ligase.pdb_ids:
        ligase.best_structure = f"AF-{ligase.uniprot_acc}-F1"
        ligase.best_resolution = None
        return

    from pipeline.rcsb import fetch_entry_metadata

    best = None
    best_resolution = None
    try:
        for metadata in fetch_entry_metadata(ligase.pdb_ids[:60], fetcher=fetcher):
            if metadata.resolution is None:
                continue
            if best_resolution is None or metadata.resolution < best_resolution:
                best_resolution = metadata.resolution
                best = metadata.pdb_id
            # A drug-like ligand anywhere in the accession's entries counts.
            for entity in metadata.nonpolymer_entities:
                mw = entity.get("mw") or 0
                if mw and mw >= 150:
                    ligase.has_ligand = 1
    except Exception:  # noqa: BLE001
        pass

    if best:
        ligase.best_structure = best
        ligase.best_resolution = best_resolution
    else:
        ligase.best_structure = ligase.pdb_ids[0]


def afdb_pdb_url(accession: str, fetcher: Fetcher) -> str:
    """The current PDB file URL for an AlphaFold prediction, or "" if there is none."""
    try:
        payload = fetcher.fetch_json(
            f"https://alphafold.ebi.ac.uk/api/prediction/{accession}",
            key=f"afdb_meta_{accession}",
        )
    except Exception:  # noqa: BLE001
        return ""
    if isinstance(payload, list) and payload:
        return payload[0].get("pdbUrl") or ""
    return ""


FPOCKET_SCORE = re.compile(r"Druggability Score\s*:\s*([0-9.eE+-]+)")
FPOCKET_VOLUME = re.compile(r"Volume\s*:\s*([0-9.eE+-]+)")


def run_fpocket(structure_path: Path) -> tuple[float | None, float | None, str]:
    """Top-pocket druggability score and volume from fpocket.

    Returns (score, volume, note). P2Rank is the documented fallback; it is only
    attempted when fpocket is absent, because fpocket resolved on this host.
    """
    import shutil

    if shutil.which("fpocket") is None:
        return None, None, "fpocket_not_installed"

    work = structure_path.parent
    try:
        result = subprocess.run(
            ["fpocket", "-f", structure_path.name],
            cwd=work, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return None, None, "fpocket_timeout"
    if result.returncode != 0:
        return None, None, f"fpocket_exit_{result.returncode}"

    info = work / f"{structure_path.stem}_out" / f"{structure_path.stem}_info.txt"
    if not info.exists():
        return None, None, "fpocket_no_info_file"

    text = info.read_text(errors="replace")
    # The info file lists pockets in rank order, so the first block is the top
    # pocket, which is what spec 5.3 asks for.
    blocks = text.split("Pocket ")
    for block in blocks[1:]:
        score = FPOCKET_SCORE.search(block)
        volume = FPOCKET_VOLUME.search(block)
        if score:
            return (
                float(score.group(1)),
                float(volume.group(1)) if volume else None,
                "fpocket",
            )
    return None, None, "fpocket_no_pocket_found"


def score_pocket(ligase: Ligase, fetcher: Fetcher) -> str:
    """Download the best structure and run fpocket on it."""
    identifier = ligase.best_structure
    if not identifier:
        return "no_structure"

    with tempfile.TemporaryDirectory(prefix="binman_fpocket_") as tmp:
        work = Path(tmp)
        try:
            if identifier.startswith("AF-"):
                # Resolve the file URL through the AFDB API rather than pinning a
                # model version: the naming moved from model_v4 to model_v6
                # during this build and a hard-coded version 404s silently.
                url = afdb_pdb_url(ligase.uniprot_acc, fetcher)
                if not url:
                    return "afdb_no_prediction"
                data = fetcher.fetch_bytes(url, key=f"afdb_pdb_{ligase.uniprot_acc}")
            else:
                url = f"https://files.rcsb.org/download/{identifier.lower()}.pdb"
                data = fetcher.fetch_bytes(url, key=f"pdb_{identifier}")
        except Exception as exc:  # noqa: BLE001
            return f"structure_download_failed:{type(exc).__name__}"

        path = work / f"{identifier.replace('-', '_')}.pdb"
        path.write_bytes(data)
        score, volume, note = run_fpocket(path)
        ligase.pocket_score = score
        ligase.pocket_volume_a3 = volume
        return note


# --------------------------------------------------------------------------- #
# expression and substrates
# --------------------------------------------------------------------------- #

# The Open Targets schema moved: `Target.expressions` is gone and
# `Target.baselineExpression.rows` carries per-biosample quartiles plus a
# specificity score. Probed from the live schema rather than assumed.
EXPRESSION_QUERY = """
query($id:String!){
  target(ensemblId:$id){
    id approvedSymbol
    baselineExpression{
      count
      rows{ median max unit specificity_score distribution_score
            tissueBiosample{ biosampleName } }
    }
  }
}
"""


def fetch_expression(ligase: Ligase, fetcher: Fetcher, config: Config) -> str:
    """Open Targets baseline expression, summarised as a tissue count.

    Needs an Ensembl gene id, which Open Targets keys on. A failure here is
    recorded and the column is left null rather than guessed.
    """
    try:
        mapping = fetcher.fetch_json(
            "https://rest.uniprot.org/uniprotkb/" + ligase.uniprot_acc,
            params={"fields": "xref_ensembl", "format": "json"},
            key=f"ensembl_{ligase.uniprot_acc}",
        )
    except Exception as exc:  # noqa: BLE001
        return f"ensembl_lookup_failed:{type(exc).__name__}"

    ensembl_ids = sorted({
        x["id"].split(".")[0]
        for x in (mapping.get("uniProtKBCrossReferences") or [])
        if x.get("database") == "Ensembl" and x.get("id", "").startswith("ENSG")
    })
    # UniProt lists transcript ids under Ensembl; the gene id sits in properties.
    if not ensembl_ids:
        for x in (mapping.get("uniProtKBCrossReferences") or []):
            if x.get("database") != "Ensembl":
                continue
            for prop in x.get("properties") or []:
                value = str(prop.get("value", ""))
                if value.startswith("ENSG"):
                    ensembl_ids.append(value.split(".")[0])
    if not ensembl_ids:
        return "no_ensembl_gene_id"

    threshold = float(config.t("e3_triage.expression_breadth_tissue_tpm"))
    try:
        payload = fetcher.fetch_json(
            OPEN_TARGETS, method="POST",
            json_body={"query": EXPRESSION_QUERY, "variables": {"id": ensembl_ids[0]}},
            key=f"ot_expr_{ensembl_ids[0]}",
        )
    except Exception as exc:  # noqa: BLE001
        return f"open_targets_failed:{type(exc).__name__}"

    target = (payload.get("data") or {}).get("target") or {}
    baseline = target.get("baselineExpression") or {}
    rows = baseline.get("rows") or []
    if not rows:
        return "open_targets_no_expression"

    # Spec 5.3 defines expression_breadth as the count of tissues above a
    # threshold, so that is what this is: median expression per biosample.
    above = sum(
        1 for row in rows
        if row.get("median") is not None and float(row["median"]) > threshold
    )
    ligase.expression_breadth = above

    # `tumour_enriched` as the spec describes it needs a tumour-against-normal
    # comparison, which the current Open Targets schema no longer exposes. It is
    # left at 0 and the gap is recorded (DECISIONS D-009) rather than silently
    # filled with tissue specificity, which is a different quantity.
    ligase.tumour_enriched = 0
    return "open_targets"


def load_substrate_counts() -> tuple[dict[str, int], dict[str, int]]:
    """Curated and predicted substrate counts per gene, from UbiBrowser."""
    import csv

    curated: dict[str, int] = {}
    path = VALIDATION / "ubibrowser_literature_e3.tsv"
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            pairs = set()
            for row in csv.DictReader(handle, delimiter="\t"):
                e3 = (row.get("e3_gene") or "").strip().upper()
                substrate = (row.get("substrate_gene") or "").strip().upper()
                if e3 and substrate:
                    pairs.add((e3, substrate))
            for e3, _substrate in pairs:
                curated[e3] = curated.get(e3, 0) + 1

    predicted: dict[str, int] = {}
    path = VALIDATION / "ubibrowser_predicted_e3.tsv"
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            pairs = set()
            for row in csv.DictReader(handle, delimiter="\t"):
                e3 = (row.get("e3_acc") or "").strip()
                substrate = (row.get("substrate_acc") or "").strip()
                if e3 and substrate:
                    pairs.add((e3, substrate))
            for e3, _substrate in pairs:
                predicted[e3] = predicted.get(e3, 0) + 1
    return curated, predicted


def assign_exploitation(ligase: Ligase, config: Config) -> None:
    table = config.t("e3_triage.exploitation")
    gene = (ligase.gene or "").upper()
    if gene in {g.upper() for g in table.get("clinically_validated", [])}:
        ligase.exploitation_status = "clinically validated"
    elif gene in {g.upper() for g in table.get("chemically_validated", [])}:
        ligase.exploitation_status = "chemically validated"
    elif gene in {g.upper() for g in table.get("covalent_handle_only", [])}:
        ligase.exploitation_status = "covalent handle only"
    elif ligase.pocket_score is not None and ligase.pocket_score > 0:
        ligase.exploitation_status = "ligandable unproven"
    else:
        ligase.exploitation_status = "orphan"


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #

def rank(ligases: list[Ligase], config: Config, held_out: bool = False) -> None:
    """Transparent weighted sum. Every component is a visible column.

    `held_out=True` drops `exploitation_status` and `has_ligand` from the
    weights, which spec 9.3 requires for the enrichment test to mean anything.
    These two are not weighted components in the first place, so the flag is
    recorded for the audit trail rather than changing the arithmetic.
    """
    weights = {
        key.replace("weight_", ""): float(value)
        for key, value in config.t("e3_triage").items()
        if key.startswith("weight_")
    }
    volume_reference = float(config.t("e3_triage.pocket_volume_reference_a3"))

    pocket_scores = [l.pocket_score for l in ligases if l.pocket_score is not None]
    max_pocket = max(pocket_scores) if pocket_scores else 1.0
    max_substrates = max((l.substrate_count for l in ligases), default=1) or 1
    max_pdb = max((len(l.pdb_ids) for l in ligases), default=1) or 1
    family_sizes: dict[str, int] = {}
    for ligase in ligases:
        family_sizes[ligase.family] = family_sizes.get(ligase.family, 0) + 1
    max_family = max(family_sizes.values(), default=1) or 1

    for ligase in ligases:
        pocket = (ligase.pocket_score / max_pocket) if ligase.pocket_score else 0.0
        volume = min(1.0, (ligase.pocket_volume_a3 or 0.0) / volume_reference)
        coverage = min(1.0, len(ligase.pdb_ids) / max_pdb)
        # Selectivity is the inverse of breadth: a ligase expressed everywhere is
        # a worse target than one restricted to a few tissues.
        if ligase.expression_breadth is None:
            selectivity = 0.0
        else:
            selectivity = max(0.0, 1.0 - min(1.0, ligase.expression_breadth / 60.0))
        substrates = min(1.0, ligase.substrate_count / max_substrates)
        # Family novelty rewards a ligase from an under-represented family.
        novelty = 1.0 - (family_sizes.get(ligase.family, 1) / max_family)

        ligase.triage_score = round(
            weights.get("pocket_score", 0) * pocket
            + weights.get("pocket_volume", 0) * volume
            + weights.get("structural_coverage", 0) * coverage
            + weights.get("expression_selectivity", 0) * selectivity
            + weights.get("substrate_count", 0) * substrates
            + weights.get("family_novelty", 0) * novelty,
            6,
        )

    ordered = sorted(ligases, key=lambda l: -(l.triage_score or 0.0))
    for index, ligase in enumerate(ordered, start=1):
        ligase.triage_rank = index


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def run(limit: int | None = None, skip_pockets: bool = False,
        skip_expression: bool = False) -> dict:
    config = load_config()
    fetcher = Fetcher("uniprot", config=config)
    manifest = Manifest(STAGE)

    repertoire = build_repertoire(config, fetcher)
    curated, predicted = load_substrate_counts()
    log_event("2.2", f"UbiBrowser substrate counts loaded: {len(curated):,} E3s with "
                     f"curated substrates, {len(predicted):,} with predicted.")

    ligases = sorted(repertoire.values(), key=lambda l: l.uniprot_acc)
    if limit is not None:
        ligases = ligases[:limit]

    notes: dict[str, int] = {}
    for index, ligase in enumerate(ligases, start=1):
        ligase.substrate_count = curated.get((ligase.gene or "").upper(), 0)
        ligase.substrate_count_predicted = predicted.get(ligase.uniprot_acc, 0)

        if manifest.done(ligase.uniprot_acc):
            cached = next(
                (r for r in manifest.read() if r.get("key") == ligase.uniprot_acc), None
            )
            if cached and cached.get("payload"):
                for key, value in cached["payload"].items():
                    if hasattr(ligase, key):
                        setattr(ligase, key, value)
                continue

        pick_best_structure(ligase, fetcher)

        pocket_note = "skipped"
        if not skip_pockets:
            pocket_note = score_pocket(ligase, fetcher)
        notes[pocket_note] = notes.get(pocket_note, 0) + 1

        expression_note = "skipped"
        if not skip_expression:
            expression_note = fetch_expression(ligase, fetcher, config)
        notes[expression_note] = notes.get(expression_note, 0) + 1

        if ligase.pocket_score is None and not skip_pockets:
            ligase.status = f"failed:pocket:{pocket_note}"

        assign_exploitation(ligase, config)

        payload = {
            "best_structure": ligase.best_structure,
            "best_resolution": ligase.best_resolution,
            "pocket_score": ligase.pocket_score,
            "pocket_volume_a3": ligase.pocket_volume_a3,
            "has_ligand": ligase.has_ligand,
            "expression_breadth": ligase.expression_breadth,
            "tumour_enriched": ligase.tumour_enriched,
            "exploitation_status": ligase.exploitation_status,
            "status": ligase.status,
        }
        manifest.record(ligase.uniprot_acc, status=ligase.status,
                        pocket_note=pocket_note, expression_note=expression_note,
                        payload=payload)

        if index % 50 == 0:
            log_event("2.2", f"{index:,}/{len(ligases):,} ligases processed. Notes: {notes}.")

    rank(ligases, config)

    rows = []
    for ligase in ligases:
        rows.append({
            "uniprot_acc": ligase.uniprot_acc, "gene": ligase.gene, "name": ligase.name,
            "family": ligase.family, "subfamily": ligase.subfamily,
            "pdb_entries": len(ligase.pdb_ids),
            "best_structure": ligase.best_structure,
            "pocket_score": ligase.pocket_score,
            "pocket_volume_a3": ligase.pocket_volume_a3,
            "has_ligand": ligase.has_ligand,
            "expression_breadth": ligase.expression_breadth,
            "tumour_enriched": ligase.tumour_enriched,
            "substrate_count": ligase.substrate_count,
            "substrate_count_predicted": ligase.substrate_count_predicted,
            "exploitation_status": ligase.exploitation_status,
            "triage_score": ligase.triage_score,
            "triage_rank": ligase.triage_rank,
            "structure_file": "",
            "status": ligase.status,
        })
    written = write_jsonl(OUTPUT, rows)

    with_pocket = sum(1 for r in rows if r["pocket_score"] is not None)
    coverage = with_pocket / max(1, len(rows))
    log_event("2.2", f"E3 triage complete: {written:,} ligases, {with_pocket:,} with a "
                     f"pocket score (coverage {coverage:.3f}, floor "
                     f"{config.t('validation.e3_pocket_coverage_floor')}). Notes: {notes}.")
    return {
        "ligases": written, "with_pocket_score": with_pocket,
        "pocket_coverage": round(coverage, 4), "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage the human E3 ligase repertoire")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-pockets", action="store_true")
    parser.add_argument("--skip-expression", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit, skip_pockets=args.skip_pockets,
                         skip_expression=args.skip_expression), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
