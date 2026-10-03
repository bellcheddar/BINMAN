"""Stage 2.4: the lens graph edge table (spec 2.4, 6.3).

Builds `edge` from the bridge, degron and ligase tables plus the curated
UbiBrowser network. Four edge types, each carrying its evidence so a lens can
colour by provenance:

    bridged_by       two chains bridged by the same ligand in one assembly
    ubiquitylates    a curated E3-to-substrate pair from UbiBrowser literature
    predicted_ub     a predicted E3-to-substrate pair, kept separate from curated
    has_degron       a protein carrying a degron candidate, linked to its own node

A predicted edge is never merged into a curated one: the lens needs to be able
to show only what is literature-backed.
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
    INTERIM, VALIDATION, Manifest, log_event, write_jsonl,
)

STAGE = "edges"
OUTPUT = INTERIM / "edges.jsonl"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "atlas" / "binman.sqlite"

# A predicted network of millions of pairs would swamp a 400-node graph, so the
# predicted edges are capped per E3 and ranked by the source's own p-value.
MAX_PREDICTED_PER_E3 = 25


def gene_to_accession(connection: sqlite3.Connection) -> dict[str, str]:
    """Map gene symbols to accessions using the ligase table, which has both."""
    mapping: dict[str, str] = {}
    try:
        for row in connection.execute(
            "SELECT gene, uniprot_acc FROM ligase WHERE gene IS NOT NULL AND gene != ''"
        ):
            mapping.setdefault(row[0].upper(), row[1])
    except sqlite3.Error:
        pass
    return mapping


def bridge_edges(connection: sqlite3.Connection) -> list[dict]:
    """One edge per bridged chain pair, resolved to accessions where possible."""
    accession_by_chain: dict[tuple[str, str], str] = {}
    try:
        for row in connection.execute(
            "SELECT pdb_id, auth_asym_id, uniprot_acc FROM polymer_entity "
            "WHERE uniprot_acc IS NOT NULL AND uniprot_acc != ''"
        ):
            for chain in (row[1] or "").split(","):
                chain = chain.strip()
                if chain:
                    accession_by_chain[(row[0], chain)] = row[2]
    except sqlite3.Error:
        return []

    edges: list[dict] = []
    seen: set[tuple] = set()
    for row in connection.execute(
        "SELECT pdb_id, ccd_id, chain_a, chain_b, bridging_balance, dsasa_total, "
        "ccd_class FROM bridge WHERE status = 'ok' AND symmetry_mediated = 0"
    ):
        pdb_id, ccd_id, chain_a, chain_b = row[0], row[1], row[2], row[3]
        # Bridge chain labels are "<auth>/<subchain>"; the auth part maps to a
        # polymer entity.
        auth_a = (chain_a or "").split("/")[0]
        auth_b = (chain_b or "").split("/")[0]
        source = accession_by_chain.get((pdb_id, auth_a))
        target = accession_by_chain.get((pdb_id, auth_b))
        if not source or not target or source == target:
            continue
        key = tuple(sorted((source, target))) + (ccd_id,)
        if key in seen:
            continue
        seen.add(key)
        edges.append({
            "source_acc": source, "target_acc": target, "ccd_id": ccd_id,
            "edge_type": "bridged_by",
            "evidence": json.dumps({
                "balance": row[4], "dsasa_total": row[5], "ccd_class": row[6],
            }),
            "pdb_id": pdb_id, "status": "ok",
        })
    return edges


def ubibrowser_edges(connection: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """Curated and predicted E3-substrate edges, kept as separate types."""
    genes = gene_to_accession(connection)

    curated: list[dict] = []
    path = VALIDATION / "ubibrowser_literature_e3.tsv"
    if path.exists():
        seen: set[tuple] = set()
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                e3 = genes.get((row.get("e3_gene") or "").strip().upper())
                substrate = (row.get("substrate_gene") or "").strip().upper()
                if not e3 or not substrate:
                    continue
                target = genes.get(substrate, substrate)
                key = (e3, target)
                if key in seen:
                    continue
                seen.add(key)
                curated.append({
                    "source_acc": e3, "target_acc": target, "ccd_id": None,
                    "edge_type": "ubiquitylates",
                    "evidence": json.dumps({"source": row.get("source", ""),
                                            "curation": "UbiBrowser literature"}),
                    "pdb_id": None, "status": "ok",
                })

    predicted: list[dict] = []
    path = VALIDATION / "ubibrowser_predicted_e3.tsv"
    if path.exists():
        per_e3: dict[str, list[tuple[float, str]]] = {}
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                e3 = (row.get("e3_acc") or "").strip()
                substrate = (row.get("substrate_acc") or "").strip()
                if not e3 or not substrate:
                    continue
                try:
                    pvalue = float(row.get("pvalue") or 1.0)
                except ValueError:
                    continue
                per_e3.setdefault(e3, []).append((pvalue, substrate))
        for e3, items in per_e3.items():
            for pvalue, substrate in sorted(items)[:MAX_PREDICTED_PER_E3]:
                predicted.append({
                    "source_acc": e3, "target_acc": substrate, "ccd_id": None,
                    "edge_type": "predicted_ub",
                    "evidence": json.dumps({"pvalue": pvalue,
                                            "curation": "UbiBrowser prediction"}),
                    "pdb_id": None, "status": "ok",
                })
    return curated, predicted


def degron_edges(connection: sqlite3.Connection) -> list[dict]:
    """A self-edge marking a protein that carries a degron candidate.

    Self-edges let a lens recolour degron-carrying nodes without needing a
    separate node attribute table.
    """
    edges: list[dict] = []
    try:
        for row in connection.execute(
            "SELECT uniprot_acc, COUNT(*) AS n, MAX(degron_geometry_score) AS best "
            "FROM degron WHERE status = 'ok' GROUP BY uniprot_acc"
        ):
            edges.append({
                "source_acc": row[0], "target_acc": row[0], "ccd_id": None,
                "edge_type": "has_degron",
                "evidence": json.dumps({"candidates": row[1], "best_score": row[2]}),
                "pdb_id": None, "status": "ok",
            })
    except sqlite3.Error:
        pass
    return edges


def build() -> dict:
    if not DB_PATH.exists():
        log_event("2.4", "Edge build skipped: the atlas has not been built yet.")
        return {"edges": 0}

    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        bridges = bridge_edges(connection)
        curated, predicted = ubibrowser_edges(connection)
        degrons = degron_edges(connection)
    finally:
        connection.close()

    rows = bridges + curated + predicted + degrons
    written = write_jsonl(OUTPUT, rows)
    counts = {
        "bridged_by": len(bridges), "ubiquitylates": len(curated),
        "predicted_ub": len(predicted), "has_degron": len(degrons),
        "edges": written,
    }
    Manifest(STAGE).record("build", status="ok", **counts)
    log_event("2.4", f"Edge table built: {written:,} edges "
                     f"({len(bridges):,} bridged_by, {len(curated):,} curated "
                     f"ubiquitylates, {len(predicted):,} predicted, "
                     f"{len(degrons):,} has_degron).")
    return counts


def main() -> int:
    argparse.ArgumentParser(description="Build the lens graph edge table").parse_args()
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
