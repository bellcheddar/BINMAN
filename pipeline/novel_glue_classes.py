"""Stage 2.6: novel glue series, clustered by the interface they induce.

A molecular glue class is defined by what it glues, so the clustering is on the
protein pair rather than the chemistry. A pair carrying several distinct ligands
is a medicinal chemistry series somebody is running; a pair with one ligand is a
single observation.

The input is the intersection of three independent signals: the geometric
bridging filter found it, `novel_bridge` says no curated glue database lists it,
and the triage head called it a molecular glue. Homo-oligomeric pairs are
dropped, because a ligand bridging two copies of one protein is a different
question, and symmetry-mediated contacts are already excluded upstream.

**What this does not do is separate induced proximity from a pre-existing
interface.** Both bury surface against two chains and both pass the filter. The
14-3-3 and small-GTPase series are induced proximity; the tubulin and proteasome
series are ligands binding an interface that exists without them. Buried area
sorts them better than anything else available here, and the page says so.

The output is read by the Glue Atlas page, so it is written under `app/static/`
rather than `data/interim/`: the deploy ships the application tree and excludes
the interim tree, and a panel fed from an excluded file would be empty on the
live host while looking correct locally.
"""

from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    ROOT, Manifest, load_config, log_event, utcnow,
)

STAGE = "novel_glue_classes"
OUTPUT = ROOT / "app" / "static" / "novel_glue_series.json"
DB_PATH = ROOT / "data" / "atlas" / "binman.sqlite"

# A series needs more than one repeat to be a series. Two ligands on one pair is
# a pair of observations; three is somebody iterating.
MIN_LIGANDS_FOR_SERIES = 3
# The page shows a dozen; the artefact carries enough to re-rank without a
# rebuild, and a protein name longer than this is a construct description.
PAIRS_KEPT = 40
NAME_LIMIT = 48


def chain_index(connection: sqlite3.Connection) -> dict[str, dict[str, tuple[str, str]]]:
    """pdb_id -> auth chain id -> (protein name, UniProt accession).

    `auth_asym_id` holds a comma-joined list when one entity is deposited as
    several chains, so each one is indexed separately.
    """
    index: dict[str, dict[str, tuple[str, str]]] = collections.defaultdict(dict)
    rows = connection.execute(
        "SELECT pdb_id, auth_asym_id, name, uniprot_acc FROM polymer_entity"
    )
    for row in rows:
        for auth in str(row["auth_asym_id"] or "").split(","):
            auth = auth.strip()
            if auth:
                index[row["pdb_id"]][auth] = ((row["name"] or "").strip(),
                                              (row["uniprot_acc"] or "").strip())
    return index


def cluster(connection: sqlite3.Connection, balance_floor: float) -> tuple[dict, int]:
    """Group the qualifying bridges by the protein pair they bridge."""
    index = chain_index(connection)

    def resolve(pdb_id: str, chain: str) -> tuple[str, str]:
        key = str(chain or "").split("/")[0].strip()
        return index.get(pdb_id, {}).get(key, ("", ""))

    bridges = connection.execute(
        """
        SELECT id, pdb_id, ccd_id, chain_a, chain_b, dsasa_total
        FROM bridge
        WHERE status = 'ok' AND novel_bridge = 1
          AND evidence_class = 'molecular_glue'
          AND symmetry_mediated = 0
          AND bridging_balance >= ?
        """,
        (balance_floor,),
    ).fetchall()

    pairs: dict[tuple[str, str], dict] = {}
    for row in bridges:
        (name_a, acc_a) = resolve(row["pdb_id"], row["chain_a"])
        (name_b, acc_b) = resolve(row["pdb_id"], row["chain_b"])
        if not name_a or not name_b or name_a == name_b:
            continue
        key = tuple(sorted((name_a[:NAME_LIMIT], name_b[:NAME_LIMIT])))
        group = pairs.setdefault(key, {"ligands": set(), "entries": set(),
                                       "dsasa": [], "accessions": set(),
                                       "widest": None})
        group["ligands"].add(row["ccd_id"])
        group["entries"].add(row["pdb_id"])
        group["dsasa"].append(row["dsasa_total"] or 0)
        # An accession so the series can be opened in the Lens graph, and the
        # widest bridge so the page can name one structure to look at. The row
        # id goes with it: the shared selection is pdb:ccd:id, and a link
        # without the id names a bridge the viewer cannot find.
        for accession in (acc_a, acc_b):
            if accession:
                group["accessions"].add(accession)
        area = row["dsasa_total"] or 0
        if group["widest"] is None or area > group["widest"]["dsasa"]:
            group["widest"] = {
                "dsasa": area, "pdb_id": row["pdb_id"], "ccd_id": row["ccd_id"],
                "bridge_id": row["id"],
                # The chain labels as the bridge recorded them, which is what
                # the assembly's polymer units are keyed on, so the
                # protein-protein interface can be measured on the same pair of
                # chains the ligand was measured against.
                "chain_a": row["chain_a"], "chain_b": row["chain_b"],
            }
    return pairs, len(bridges)


def protein_protein_dsasa(widest: dict) -> dict:
    """The buried area between the two bridged chains, ligand excluded.

    The caveat this closes: a bridging ligand can be glueing two proteins
    together or sitting in a pocket of an interface that was already there.
    Both bury surface against two chains and the geometric filter cannot tell
    them apart. What separates them is how much of the sticking the ligand is
    doing, and that is the ratio of the two interface areas.

    Measured in the same convention as `dsasa_total` (both sides of the
    contact, spec 5.1), on the same two chains, with the same probe radius from
    thresholds.toml, so the two numbers divide.

    Alpha/beta-tubulin buries thousands of square Angstroms chain to chain and
    the colchicine-site ligand adds a few hundred: the interface is obligate
    and the ligand is a passenger. A chemically induced dimer is the other way
    round. Nothing here decides which is which: it reports the ratio and the
    page shows it.
    """
    from pipeline.geometry import SasaCalculator
    from pipeline.rcsb import ASSEMBLY_DIR
    from pipeline.structures import load_assembly

    pdb_id = str(widest.get("pdb_id") or "").upper()
    path = ASSEMBLY_DIR / f"{pdb_id}-assembly1.cif.gz"
    if not path.exists():
        path = ASSEMBLY_DIR / f"{pdb_id}-deposited.cif.gz"
    if not pdb_id or not path.exists():
        # Recorded, not fetched: this runs inside the atlas post-build and a
        # stage that quietly reaches for the network there is a stage that
        # fails on a machine without one.
        return {"status": "assembly not cached"}

    assembly = load_assembly(path, pdb_id=pdb_id)
    units = {unit.label: unit for unit in assembly.polymers}
    first, second = widest.get("chain_a"), widest.get("chain_b")
    if first not in units or second not in units:
        return {"status": "chains absent from the cached assembly"}

    calculator = SasaCalculator()
    area = calculator.delta(units[first].atoms, units[second].atoms,
                            f"{pdb_id}:{first}", f"{pdb_id}:{second}")
    ligand_area = float(widest.get("dsasa") or 0)
    total = area + ligand_area
    return {
        "status": "ok",
        "protein_protein_dsasa": round(area, 1),
        # How much of the interface the ligand accounts for. 1.0 means the two
        # chains do not touch at all and the ligand is the only thing holding
        # them together.
        "ligand_share": round(ligand_area / total, 3) if total > 0 else None,
    }


def _widest(group: dict) -> dict:
    widest = dict(group.get("widest") or {})
    out = {
        "dsasa": round(float(widest.get("dsasa") or 0), 1),
        "pdb_id": widest.get("pdb_id") or "",
        "ccd_id": widest.get("ccd_id") or "",
        "bridge_id": widest.get("bridge_id") or "",
    }
    if out["pdb_id"]:
        out.update(protein_protein_dsasa(widest))
    return out


def build() -> dict:
    if not DB_PATH.exists():
        log_event("2.6", "Novel glue series skipped: the atlas has not been built yet.")
        return {"series": 0}

    config = load_config()
    # The panel is a headline, and glue_balance_strong is the threshold the spec
    # names for a headline figure: glue_balance_floor is "reported but not
    # headline". See DECISIONS.md D-088.
    balance_floor = float(config.t("bridging.glue_balance_strong"))

    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        pairs, considered = cluster(connection, balance_floor)
    finally:
        connection.close()

    ranked = sorted(pairs.items(),
                    key=lambda kv: (-len(kv[1]["ligands"]), -len(kv[1]["entries"])))
    series = [k for k, v in pairs.items()
              if len(v["ligands"]) >= MIN_LIGANDS_FOR_SERIES]

    report = {
        "generated_at": utcnow(),
        "bridging_balance_floor": balance_floor,
        "min_ligands_for_series": MIN_LIGANDS_FOR_SERIES,
        "bridges_considered": considered,
        "distinct_hetero_pairs": len(pairs),
        "series": len(series),
        "top_pairs": [
            {
                "interface": list(key),
                "n_ligands": len(group["ligands"]),
                "n_entries": len(group["entries"]),
                "median_dsasa": round(statistics.median(group["dsasa"]), 1),
                "accessions": sorted(group["accessions"])[:2],
                "widest": _widest(group),
            }
            for key, group in ranked[:PAIRS_KEPT]
        ],
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    counts = {"bridges_considered": considered, "hetero_pairs": len(pairs),
              "series": len(series), "pairs_kept": len(report["top_pairs"]),
              "bridging_balance_floor": balance_floor}
    Manifest(STAGE).record("build", status="ok", **counts)
    log_event("2.6", f"Novel glue series: {len(series):,} protein pairs carry "
                     f"{MIN_LIGANDS_FOR_SERIES} or more distinct novel glues, "
                     f"from {considered:,} bridges over {len(pairs):,} pairs.")
    return counts


def main() -> int:
    argparse.ArgumentParser(description="Cluster the novel glues by interface").parse_args()
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
