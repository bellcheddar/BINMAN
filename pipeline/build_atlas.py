"""Build the read-only SQLite atlas (spec Section 7, stage 4.3).

Reads the stage outputs and writes `data/atlas/binman.sqlite`. Idempotent: the
database is rebuilt from the manifests every time, so there is no migration path
to maintain and no chance of a stale row surviving a schema change.

A row that failed a stage is inserted with `status = "failed:<reason>"` rather
than dropped, so the UI can show what was attempted and the counts reconcile
against the manifests (spec Section 7).
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    ATLAS, INTERIM, MANIFESTS, REFERENCE, VALIDATION, Manifest, load_config,
    log_event, read_jsonl, utcnow,
)

DB_PATH = ATLAS / "binman.sqlite"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"
STAGE = "build_atlas"

# Curated glue sources, for the novel-bridge determination. Spec 9.1 defines a
# novel bridge as one passing every filter that appears in none of the three
# glue databases, is not in PROTAC-DB and is not a BioLiP2 artefact.
CURATED_GLUE_SOURCES = ("mgdb_glues", "molgluedb_glues", "mgtbind_ternary")
EXCLUSION_SOURCES = ("protacdb_protacs",)


def connect(path: Path = DB_PATH, fresh: bool = True) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fresh and path.exists():
        path.unlink()
        for suffix in ("-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA.read_text())
    return connection


def _curated_identifiers() -> tuple[set[str], set[str]]:
    """PDB identifiers in the curated glue databases, and in the exclusion sets.

    Both come back empty when those datasets have not resolved (Gate G7). An
    empty curated set means `novel_bridge` cannot be determined, which is
    recorded rather than silently treated as "everything is novel".
    """
    def harvest(names) -> set[str]:
        found: set[str] = set()
        for name in names:
            path = VALIDATION / f"{name}.tsv"
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    for key, value in row.items():
                        if "pdb" in (key or "").lower() and value:
                            for token in str(value).replace(";", ",").split(","):
                                token = token.strip().upper()
                                if len(token) == 4 and token[0].isdigit():
                                    found.add(token)
        return found

    return harvest(CURATED_GLUE_SOURCES), harvest(EXCLUSION_SOURCES)


def _biolip_artefact_codes() -> set[str]:
    path = VALIDATION / "biolip2_artefacts.tsv"
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as handle:
        return {
            (row.get("ccd_id") or "").upper()
            for row in csv.DictReader(handle, delimiter="\t")
        }


def load_entries(connection: sqlite3.Connection, catalogue: list[dict]) -> int:
    # The catalogue is rewritten atomically-ish by stage 1.1, so a build racing
    # that stage can see a partial row. Skipping rows with no identifier is
    # cheaper than locking, and the build is idempotent anyway.
    catalogue = [row for row in catalogue if row.get("pdb_id")]
    rows = [
        (
            row["pdb_id"], row.get("title", ""), row.get("method", ""),
            row.get("resolution"), row.get("deposit_date", ""),
            row.get("release_date", ""), row.get("organism", ""),
            row.get("assembly_id", "1"), row.get("tier"),
            row.get("polymer_entity_count"), row.get("nonpolymer_entity_count"),
            "ok",
        )
        for row in catalogue
    ]
    connection.executemany(
        "INSERT OR REPLACE INTO entry (pdb_id, title, method, resolution, deposit_date, "
        "release_date, organism, assembly_id, tier, polymer_entity_count, "
        "nonpolymer_entity_count, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_polymer_entities(connection: sqlite3.Connection, catalogue: list[dict]) -> int:
    rows = []
    for entry in catalogue:
        if not entry.get("pdb_id"):
            continue
        for entity in entry.get("polymer_entities") or []:
            accessions = entity.get("uniprot_ids") or [""]
            rows.append((
                entry["pdb_id"],
                ",".join(entity.get("asym_ids") or []),
                ",".join(entity.get("auth_asym_ids") or []),
                accessions[0] if accessions else "",
                entity.get("name", ""), entity.get("organism", ""), 0, "ok",
            ))
    connection.executemany(
        "INSERT INTO polymer_entity (pdb_id, asym_id, auth_asym_id, uniprot_acc, "
        "name, organism, is_e3, status) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_ligands(connection: sqlite3.Connection, catalogue: list[dict]) -> int:
    """Merge the CCD classification table with the per-entry chemistry metadata."""
    artefacts = _biolip_artefact_codes()

    classified: dict[str, dict] = {}
    table = REFERENCE / "ccd_classes.tsv"
    if table.exists():
        with table.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                classified[row["ccd_id"].upper()] = row

    chemistry: dict[str, dict] = {}
    for entry in catalogue:
        for entity in entry.get("nonpolymer_entities") or []:
            code = (entity.get("ccd_id") or "").upper()
            if code and code not in chemistry:
                chemistry[code] = entity

    codes = set(classified) | set(chemistry)
    rows = []
    for code in sorted(codes):
        meta = chemistry.get(code, {})
        label = classified.get(code, {})
        heavy = label.get("heavy_atoms") or ""
        rows.append((
            code,
            meta.get("name") or label.get("name", ""),
            meta.get("formula") or label.get("formula", ""),
            meta.get("mw") if meta.get("mw") is not None else (
                float(label["mw"]) if label.get("mw") else None
            ),
            int(heavy) if str(heavy).isdigit() else None,
            meta.get("smiles") or label.get("smiles", ""),
            label.get("ccd_class", "unknown"),
            label.get("rule", ""),
            "",
            int(label.get("is_furniture") or 0),
            int(code in artefacts),
            "ok" if label else "failed:not_classified",
        ))
    connection.executemany(
        "INSERT OR REPLACE INTO ligand (ccd_id, name, formula, mw, heavy_atoms, smiles, "
        "ccd_class, ccd_class_rule, parent_ccd, is_furniture, biolip_artefact, status) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_bridges(connection: sqlite3.Connection) -> tuple[int, int, bool]:
    """Insert bridge rows and set `novel_bridge` where it can be determined."""
    path = INTERIM / "bridges.jsonl"
    if not path.exists():
        return 0, 0, False

    curated, excluded = _curated_identifiers()
    artefacts = _biolip_artefact_codes()
    determinable = bool(curated)

    inserted = 0
    novel = 0
    batch: list[tuple] = []
    seen: set[tuple] = set()

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            # The interim file is append-only across restarts, so a re-run can
            # repeat a row. De-duplicate on the natural key.
            key = (row.get("pdb_id"), row.get("ligand_label"),
                   row.get("chain_a"), row.get("chain_b"))
            if key in seen:
                continue
            seen.add(key)

            pdb_id = row.get("pdb_id", "")
            ccd_id = (row.get("ccd_id") or "").upper()
            is_novel = 0
            if determinable:
                is_novel = int(
                    row.get("ccd_class") == "glue_candidate"
                    and pdb_id not in curated
                    and pdb_id not in excluded
                    and ccd_id not in artefacts
                    and not row.get("symmetry_mediated")
                )
            novel += is_novel

            batch.append((
                pdb_id, ccd_id, row.get("ligand_label", ""), row.get("assembly_id", "1"),
                row.get("entity_a", ""), row.get("entity_b", ""),
                row.get("chain_a", ""), row.get("chain_b", ""),
                row.get("dsasa_a"), row.get("dsasa_b"), row.get("dsasa_total"),
                row.get("bridging_balance"), row.get("buried_fraction"),
                row.get("contacts_a"), row.get("contacts_b"),
                row.get("heavy_atoms"), row.get("ccd_class", "unknown"),
                int(row.get("symmetry_mediated") or 0),
                None,                                    # evidence_class: LM Task B
                None, None,                              # alpha, alpha_source: never estimated
                json.dumps(row.get("interface_residues_a") or []),
                json.dumps(row.get("interface_residues_b") or []),
                None, None,                              # plip types, filled by the PLIP stage
                is_novel, "", "ok",
            ))
            if len(batch) >= 5000:
                connection.executemany(_BRIDGE_INSERT, batch)
                inserted += len(batch)
                batch.clear()

    if batch:
        connection.executemany(_BRIDGE_INSERT, batch)
        inserted += len(batch)
    return inserted, novel, determinable


_BRIDGE_INSERT = (
    "INSERT INTO bridge (pdb_id, ccd_id, ligand_label, assembly_id, entity_a, entity_b, "
    "chain_a, chain_b, dsasa_a, dsasa_b, dsasa_total, bridging_balance, buried_fraction, "
    "contacts_a, contacts_b, heavy_atoms, ccd_class, symmetry_mediated, evidence_class, "
    "alpha, alpha_source, interface_residues_a, interface_residues_b, plip_types_a, "
    "plip_types_b, novel_bridge, structure_file, status) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)


def recompute_novel(connection: sqlite3.Connection) -> int:
    """Recompute `novel_bridge` from the resynced classes (spec 9.1).

    A novel bridge passes every filter, carries a glue-candidate ligand, is not
    symmetry mediated, and appears in none of the curated glue databases, is not
    in PROTAC-DB and is not a BioLiP2 artefact.
    """
    curated, excluded = _curated_identifiers()
    artefacts = _biolip_artefact_codes()
    if not curated:
        connection.execute("UPDATE bridge SET novel_bridge = 0")
        return 0
    connection.execute("UPDATE bridge SET novel_bridge = 0")
    placeholders_c = ",".join("?" for _ in curated) or "''"
    placeholders_x = ",".join("?" for _ in excluded) or "''"
    placeholders_a = ",".join("?" for _ in artefacts) or "''"
    connection.execute(
        "UPDATE bridge SET novel_bridge = 1 "
        "WHERE status = 'ok' AND ccd_class = 'glue_candidate' "
        "  AND symmetry_mediated = 0 "
        f"  AND pdb_id NOT IN ({placeholders_c}) "
        f"  AND pdb_id NOT IN ({placeholders_x}) "
        f"  AND ccd_id NOT IN ({placeholders_a})",
        tuple(sorted(curated)) + tuple(sorted(excluded)) + tuple(sorted(artefacts)),
    )
    return int(connection.execute(
        "SELECT COUNT(*) FROM bridge WHERE novel_bridge = 1").fetchone()[0])


def resync_bridge_classes(connection: sqlite3.Connection) -> int:
    """Re-derive `bridge.ccd_class` from the ligand table.

    The geometry worker stamps a class onto each bridge row as it goes, so the
    interim file carries whatever the rules said at the time. The ligand table is
    the single source of truth for classification, and the rules change more
    often than the geometry does, so the bridge rows are resynced here rather
    than left to drift. Without this a classification fix silently does nothing
    to the Glue Atlas.
    """
    connection.execute(
        "UPDATE bridge SET ccd_class = ("
        "  SELECT l.ccd_class FROM ligand l WHERE l.ccd_id = bridge.ccd_id"
        ") WHERE EXISTS (SELECT 1 FROM ligand l WHERE l.ccd_id = bridge.ccd_id)"
    )
    return int(connection.execute(
        "SELECT COUNT(*) FROM bridge b JOIN ligand l ON l.ccd_id = b.ccd_id "
        "WHERE b.ccd_class = l.ccd_class").fetchone()[0])


def attach_structure_files(connection: sqlite3.Connection) -> int:
    """Point every bridge row at its trimmed viewer structure (stage 1.5).

    One file is written per (entry, ligand), so every bridge in that entry using
    that ligand references the same file.
    """
    mapping = read_jsonl(INTERIM / "structure_map.jsonl")
    if not mapping:
        return 0
    connection.executemany(
        "UPDATE bridge SET structure_file = ? WHERE pdb_id = ? AND ccd_id = ?",
        [(row["structure_file"], row["pdb_id"], row["ccd_id"]) for row in mapping],
    )
    return int(connection.execute(
        "SELECT COUNT(*) FROM bridge WHERE structure_file != ''").fetchone()[0])


def load_failed_entries(connection: sqlite3.Connection) -> int:
    """Carry stage failures into the entry table so the counts reconcile."""
    manifest = Manifest("bridges")
    rows = [
        (row["key"], row.get("status", "failed:unknown"))
        for row in manifest.read()
        if str(row.get("status", "")).startswith("failed:")
    ]
    if not rows:
        return 0
    connection.executemany(
        "UPDATE entry SET status = ? WHERE pdb_id = ?",
        [(status, pdb_id) for pdb_id, status in rows],
    )
    return len(rows)


def load_table_from_jsonl(connection: sqlite3.Connection, name: str,
                          path: Path, columns: tuple[str, ...]) -> int:
    """Generic loader for the Phase 2 tables, which write JSONL."""
    if not path.exists():
        return 0
    rows = read_jsonl(path)
    if not rows:
        return 0
    placeholders = ",".join("?" for _ in columns)
    connection.executemany(
        f"INSERT INTO {name} ({', '.join(columns)}) VALUES ({placeholders})",
        [tuple(row.get(column) for column in columns) for row in rows],
    )
    return len(rows)


def record_provenance(connection: sqlite3.Connection) -> int:
    """One provenance row per table, naming the tool and the parameters used."""
    config = load_config()
    thresholds = json.dumps(config.thresholds.get("bridging", {}), sort_keys=True)
    tool_versions = config.hardware.get("tools", {})
    rows = [
        ("bridge", "all", "RCSB Data API + file service", utcnow(),
         "freesasa + gemmi + binman.geometry",
         f"freesasa {tool_versions.get('freesasa')}, gemmi {tool_versions.get('gemmi')}",
         thresholds),
        ("ligand", "all", "RCSB chemical component dictionary", utcnow(),
         "binman.ccd_classes + rdkit", f"rdkit {tool_versions.get('rdkit')}",
         json.dumps({"note": "BioLiP artefact list held out of classification (D-007)"})),
        ("entry", "all", "RCSB Search API + Data API", utcnow(), "binman.catalogue", "", ""),
    ]
    connection.executemany(
        "INSERT INTO provenance (table_name, row_id, source, retrieved_at, tool, "
        "tool_version, params) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def build(fresh: bool = True) -> dict:
    catalogue = [
        row for row in read_jsonl(MANIFESTS / "catalogue.jsonl") if row.get("pdb_id")
    ]
    if not catalogue:
        raise SystemExit("catalogue is empty: run pipeline/catalogue.py first")

    connection = connect(fresh=fresh)
    try:
        counts = {
            "entry": load_entries(connection, catalogue),
            "polymer_entity": load_polymer_entities(connection, catalogue),
            "ligand": load_ligands(connection, catalogue),
        }
        bridges, novel, novel_determinable = load_bridges(connection)
        counts["bridge"] = bridges
        counts["novel_bridge"] = novel
        # Spec 9.1 makes the novel-bridge set the headline result, so an
        # undeterminable value must never read as a real zero. The flag is
        # carried into the atlas and shown in the UI.
        counts["novel_bridge_determinable"] = novel_determinable
        counts["entry_failed"] = load_failed_entries(connection)
        counts["bridges_with_structure"] = attach_structure_files(connection)
        counts["bridge_class_resynced"] = resync_bridge_classes(connection)
        # novel_bridge depends on ccd_class, so it is recomputed after the
        # resync rather than taken from the class the geometry worker stamped on.
        counts["novel_bridge"] = recompute_novel(connection)
        counts["degron"] = load_table_from_jsonl(
            connection, "degron", INTERIM / "degrons.jsonl",
            ("uniprot_acc", "afdb_id", "gene", "start_res", "end_res", "tip_res",
             "tip_aa", "turn_length", "mean_plddt", "tip_rel_sasa", "regularity",
             "degron_geometry_score", "motif_family", "is_known_neosubstrate",
             "structure_file", "status"),
        )
        counts["ligase"] = load_table_from_jsonl(
            connection, "ligase", INTERIM / "ligases.jsonl",
            ("uniprot_acc", "gene", "name", "family", "subfamily", "pdb_entries",
             "best_structure", "pocket_score", "pocket_volume_a3", "has_ligand",
             "expression_breadth", "tumour_enriched", "substrate_count",
             "substrate_count_predicted", "exploitation_status", "triage_score",
             "triage_rank", "structure_file", "status"),
        )
        counts["lysine"] = load_table_from_jsonl(
            connection, "lysine", INTERIM / "lysines.jsonl",
            ("uniprot_acc", "structure_id", "site_id", "res_num", "nz_rel_sasa",
             "cb_cb_distance", "nz_centroid_distance", "verdict", "observed_diGly", "status"),
        )
        counts["edge"] = load_table_from_jsonl(
            connection, "edge", INTERIM / "edges.jsonl",
            ("source_acc", "target_acc", "ccd_id", "edge_type", "evidence", "pdb_id", "status"),
        )
        counts["provenance"] = record_provenance(connection)
        connection.commit()
        connection.execute("PRAGMA optimize")
        connection.execute("VACUUM")
        connection.commit()
    finally:
        connection.close()

    size_mb = DB_PATH.stat().st_size / (1024 ** 2)
    counts["size_mb"] = round(size_mb, 1)
    Manifest(STAGE).record("build", status="ok", **counts)
    novel_note = (
        f"{counts['novel_bridge']:,} novel" if counts.get("novel_bridge_determinable")
        else "novel set not determinable: no curated glue database resolved (G7)"
    )
    log_event("4.3", f"Atlas built: {counts['entry']:,} entries, {counts['bridge']:,} bridges "
                     f"({novel_note}), {counts['ligand']:,} ligands, "
                     f"{counts['degron']:,} degrons, {counts['ligase']:,} ligases, "
                     f"{counts['lysine']:,} lysines, {size_mb:.1f} MB.")
    counts.update(_post_build())
    return counts


def _post_build() -> dict:
    """Re-derive what a fresh build drops, because a fresh build drops it.

    `zinc_finger` and `degron.is_known_neosubstrate` are produced by
    `pipeline.zinc_finger_scan`, which runs after the atlas exists because it
    reads the degron table. A rebuild recreates the schema and both vanish: the
    table silently, and the flag back to 0 for every row, which is a UI tile
    confidently reading "0 known neosubstrates" again (D-058).

    Nothing failed when that happened here. Three tests caught it, which is the
    only reason it is wired in rather than left as a step somebody has to
    remember. Running it costs about four minutes and needs the AlphaFold cache;
    when the cache is absent the reason is recorded rather than passed over.

    Only the per-finger scan needs that cache. The triage load and the novel
    glue clustering read the atlas and nothing else, so they sit outside the
    gate: they used to sit inside it, which meant a build on a machine without
    the AlphaFold cache silently shipped a Glue Atlas with no predicted
    evidence class on any row.
    """
    # Loads what pipeline/triage_predict.py produced, and does nothing when it
    # has not run. The inference is its own stage; this is the file IO.
    from pipeline.novel_glue_classes import build as cluster_novel
    from pipeline.triage_predict import load_into_atlas as load_triage

    triage = load_triage()
    # After the triage load, because it selects on `evidence_class`. Run before
    # it, and the Glue Atlas panel is empty with nothing to say why.
    novel = cluster_novel()
    out = {
        "triage_predicted_rows": triage.get("bridge_rows", 0),
        "novel_glue_series": novel.get("series", 0),
    }

    cache = INTERIM / "afdb"
    if not cache.exists() or not any(cache.iterdir()):
        log_event("4.3", "Per-finger scan skipped: no AlphaFold cache, so "
                         "zinc_finger and is_known_neosubstrate are absent.")
        return {**out, "zinc_finger": 0,
                "zinc_finger_skipped": "no AlphaFold cache"}
    # `degron_predict` first: it ALTERs the degron table to add
    # `imid_degradation_score`, which a fresh build drops along with the rest.
    # Missing it left the Degron Scan page showing "query failed: no such
    # column" with an empty table, because the column is in the query's default
    # projection. Two of these three post-build steps were wired in on the
    # first pass and this one was not, which is the argument for the list
    # living here rather than in somebody's memory.
    from pipeline.degron_predict import run as predict
    from pipeline.zinc_finger_scan import run as scan

    scored = predict()
    report = scan()
    return {
        **out,
        "imid_degradation_scored": scored.get("scored", 0),
        "zinc_finger": report.get("n_fingers", 0),
        "known_neosubstrate_rows": (
            report.get("known_neosubstrates", {}).get("degron_rows_marked", 0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the BINMAN SQLite atlas")
    parser.add_argument("--keep", action="store_true",
                        help="add to the existing database instead of rebuilding it")
    args = parser.parse_args()
    counts = build(fresh=not args.keep)
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
