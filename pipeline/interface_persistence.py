"""Stage 2.7: does the interface survive without THIS chemistry?

The question the novel series panel could not answer. A bridging ligand is
either glueing two proteins together or sitting in a pocket of an interface
that was already there, and buried area alone does not separate them: a real
cereblon degrader and a colchicine-site passenger both read 0.47 ligand share
(D-089).

Counting apo depositions does not answer it either. Every framing tried fell to
a cofactor: haemoglobin alpha and beta have no ligand-free structure at all,
because haem is a ligand, so the most obligate pair in the set looked induced
(D-090).

So this measures rather than counts. For each series it finds structures that
hold both proteins and **none of that series' ligands**, and measures the area
the two chains bury on each other there, in the same convention and with the
same probe radius as everywhere else:

    interface_retained = widest chain-chain area without the series ligands
                         ----------------------------------------------
                            chain-chain area in the bridged structure

**This is not an apo comparison, and calling it one would be wrong.** The
comparison structure is allowed to hold any other ligand, including a different
glue on the same interface, and for the tri-complex series it does: KRas with
cyclophilin A reads 1.06 and 1.14, because the only structures holding both
proteins are tri-complexes built on other chemistries. Cereblon with the Helios
zinc fingers reads 1.10 for the same reason. The ratio answers "does this
interface need THIS series", not "does it need a ligand at all", and the second
question is not answerable from the PDB for a pair whose proteins are only ever
crystallised together with something between them.

Read that way the three regimes are informative:

    near 0    the two chains are not seen touching in any structure lacking
              this chemistry
    near 1    the interface forms without this series, by whatever means
    far above the bridged structure caught an unusually small interface, which
    1         says the ligand share measured on it was a conformational
              accident rather than a property of the pair

The last one is why this exists. DNA gyrase A and B read 0.97 ligand share on
29.8 square Angstroms of chain-to-chain contact, which read as a ligand holding
two subunits together that barely touch. They bury 3,284 square Angstroms on
each other in 7Z9G. The pair was fine; the structure was unusual.

It cannot prove a negative. "Never observed touching without this chemistry" is
not "cannot touch without it", and a pair with no comparison structure gets no
ratio rather than a zero.
"""

from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import ROOT, Manifest, log_event, utcnow  # noqa: E402

STAGE = "interface_persistence"
SERIES = ROOT / "app" / "static" / "novel_glue_series.json"
DB_PATH = ROOT / "data" / "atlas" / "binman.sqlite"
NAME_LIMIT = 48
# Per series: how many comparison structures to measure, and how many chain
# pairings within one structure. Both are caps on work, not on evidence: the
# result keeps the largest area found, so a cap can only understate a
# pre-existing interface, never invent one.
MAX_CANDIDATES = 5
# Twelve and not three: a c-ring carries ten copies of one subunit, and three
# pairings can miss every adjacent one and report zero contact for an assembly
# that is nothing but contact.
MAX_CHAIN_PAIRS = 12


def chain_index(connection: sqlite3.Connection) -> dict[str, dict[str, str]]:
    """pdb_id -> auth chain -> truncated protein name."""
    index: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for row in connection.execute(
            "SELECT pdb_id, auth_asym_id, name FROM polymer_entity"):
        name = (row["name"] or "").strip()[:NAME_LIMIT]
        if not name:
            continue
        for auth in str(row["auth_asym_id"] or "").split(","):
            if auth.strip():
                index[row["pdb_id"]][auth.strip()] = name
    return index


def candidates(connection: sqlite3.Connection, name_a: str, name_b: str,
               ccds: set[str]) -> list[str]:
    """Entries holding both proteins and none of this series' ligands."""
    both = [row[0] for row in connection.execute(
        "SELECT pdb_id FROM polymer_entity WHERE substr(trim(name), 1, ?) = ? "
        "INTERSECT "
        "SELECT pdb_id FROM polymer_entity WHERE substr(trim(name), 1, ?) = ?",
        (NAME_LIMIT, name_a, NAME_LIMIT, name_b))]
    if not ccds:
        return both
    marks = ",".join("?" * len(ccds))
    excluded = {row[0] for row in connection.execute(
        f"SELECT DISTINCT pdb_id FROM bridge WHERE ccd_id IN ({marks})", tuple(ccds))}
    return [pdb for pdb in both if pdb not in excluded]


def series_ccds(connection: sqlite3.Connection, name_a: str, name_b: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT ccd_id FROM bridge
        WHERE status = 'ok' AND novel_bridge = 1
          AND evidence_class = 'molecular_glue'
          AND pdb_id IN (
            SELECT pdb_id FROM polymer_entity WHERE substr(trim(name), 1, ?) = ?
            INTERSECT
            SELECT pdb_id FROM polymer_entity WHERE substr(trim(name), 1, ?) = ?)
        """,
        (NAME_LIMIT, name_a, NAME_LIMIT, name_b))
    return {row[0] for row in rows}


def widest_contact(pdb_id: str, name_a: str, name_b: str,
                   names: dict[str, str], calculator) -> float | None:
    """The largest area the two named chains bury on each other in one entry."""
    from pipeline.rcsb import ASSEMBLY_DIR
    from pipeline.structures import load_assembly

    path = ASSEMBLY_DIR / f"{pdb_id}-assembly1.cif.gz"
    if not path.exists():
        path = ASSEMBLY_DIR / f"{pdb_id}-deposited.cif.gz"
    if not path.exists():
        return None

    assembly = load_assembly(path, pdb_id=pdb_id)
    first = [u for u in assembly.polymers if names.get(u.auth_chain) == name_a]
    second = [u for u in assembly.polymers if names.get(u.auth_chain) == name_b]
    if not first or not second:
        return None

    best = 0.0
    tried = 0
    for unit_a in first:
        for unit_b in second:
            if tried >= MAX_CHAIN_PAIRS:
                return best
            tried += 1
            area = calculator.delta(unit_a.atoms, unit_b.atoms,
                                    f"{pdb_id}:{unit_a.label}",
                                    f"{pdb_id}:{unit_b.label}")
            best = max(best, area)
    return best


def build(limit: int | None = None) -> dict:
    if not DB_PATH.exists() or not SERIES.exists():
        log_event("2.7", "Interface persistence skipped: the series artefact is not built.")
        return {"series": 0}

    from pipeline.geometry import SasaCalculator

    report = json.loads(SERIES.read_text(encoding="utf-8"))
    pairs = report.get("top_pairs") or []
    if limit:
        pairs = pairs[:limit]

    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    manifest = Manifest(STAGE)
    measured = 0
    try:
        names_by_entry = chain_index(connection)
        for pair in pairs:
            name_a, name_b = pair["interface"]
            key = f"{name_a}|{name_b}"
            widest = pair.get("widest") or {}
            bridged = widest.get("protein_protein_dsasa")

            ccds = series_ccds(connection, name_a, name_b)
            pool = candidates(connection, name_a, name_b, ccds)
            # Deterministic, and the order is not meaningful, so sort rather
            # than take whatever SQLite happened to return.
            pool = sorted(pool)[:MAX_CANDIDATES]

            # A fresh calculator per series: its cache is keyed by chain label
            # and would otherwise grow across the whole run for no reuse.
            calculator = SasaCalculator()
            areas: list[dict] = []
            for pdb_id in pool:
                area = widest_contact(pdb_id, name_a, name_b,
                                      names_by_entry.get(pdb_id, {}), calculator)
                if area is not None:
                    areas.append({"pdb_id": pdb_id, "chain_chain_dsasa": round(area, 1)})

            if not areas:
                pair["persistence"] = {"status": "no comparison structure",
                               "series_ligands_excluded": len(ccds),
                               "candidates": len(pool)}
                manifest.record(key, status="no_comparison", candidates=len(pool))
                continue

            best = max(areas, key=lambda row: row["chain_chain_dsasa"])
            pair["persistence"] = {
                "status": "ok",
                "series_ligands_excluded": len(ccds),
                "measured": len(areas),
                "widest_without_series": best["chain_chain_dsasa"],
                "widest_without_series_pdb_id": best["pdb_id"],
                # None rather than a division by zero: a bridged structure whose
                # chains do not touch has no denominator, and that case is
                # interesting enough to say so rather than round away.
                "interface_retained": (round(best["chain_chain_dsasa"] / bridged, 3)
                              if bridged else None),
            }
            measured += 1
            manifest.record(key, status="ok", measured=len(areas),
                            widest_without_series=best["chain_chain_dsasa"],
                            bridged=bridged,
                            interface_retained=pair["persistence"]["interface_retained"])
    finally:
        connection.close()

    report["persistence_measured_at"] = utcnow()
    report["max_candidates_per_series"] = MAX_CANDIDATES
    SERIES.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    counts = {"series": len(pairs), "measured": measured,
              "without_a_comparison": len(pairs) - measured}
    log_event("2.7", f"Interface persistence: {measured} of {len(pairs)} series compared "
                     f"against a structure holding both proteins and none of "
                     f"the series' ligands.")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chain-chain area without the series ligands")
    parser.add_argument("--limit", type=int, default=None,
                        help="only the first N series, for a quick check")
    args = parser.parse_args()
    print(json.dumps(build(limit=args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
