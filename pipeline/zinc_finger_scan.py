"""Every C2H2 zinc finger in the proteome, scored for glutarimide degradation.

D-052 found that `degron.imid_degradation_score` was right in all five cases it
was doubted over, and that its two apparent misses were a coverage limit rather
than an error: the column is per hairpin candidate, so a protein whose geometry
scan never placed a candidate on its degron finger has no row to carry the
answer. ZNF692 and ZNF653 are both pomalidomide substrates and both scored low,
because the rows that existed described the wrong finger. D-052 named the fix
and said it belonged in a column of its own rather than quietly widening that
one, because the semantics differ: per protein, not per candidate.

This is that table. It finds every C2H2 motif in every cached AlphaFold model,
with no geometry filter in front of it, and scores each one. The per-protein
answer is then `MAX(imid_degradation_score) GROUP BY uniprot_acc`, and the
finger carrying it is named rather than inferred.

**It closes the gap it was built for.** On its own degron finger ZNF692 scores
0.957 where the per-candidate column gave 0.046, and ZNF653 scores 0.982 where
it gave 0.106 and 0.011.

**What it does not do, which matters more.** Five of the canonical substrates it
recovers are genes the Sievers screen reports as degraded, so they are in the
scorer's training set and their high scores are partly memory. Only two of the
usual list are genuinely held out, and it gets one: IKZF1 scores 0.907, SALL4
scores 0.264 on its documented degron and 0.485 on its best finger, which is a
real miss. The generalisation evidence for this scorer is the 29-compound
transfer test in `degron_panel` (D-053), not this table's hit list.

**`screen_degraded` is a label, not a prediction.** Where the Sievers screen
assayed a window overlapping a finger and reported it degraded, that is recorded
as such, so the table carries its own matched negatives and positives and can be
audited without re-deriving them. A finger the screen never covered is NULL
there rather than zero.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    ATLAS, INTERIM, MANIFESTS, VALIDATION, Fetcher, load_config, log_event,
    write_jsonl,
)

DB = ATLAS / "binman.sqlite"
CACHE = INTERIM / "afdb"
REPORT = INTERIM / "zinc_finger_scan.json"
MANIFEST = MANIFESTS / "zinc_finger_scan.jsonl"
WIDTH = 23

SCHEMA = """
CREATE TABLE IF NOT EXISTS zinc_finger (
  id INTEGER PRIMARY KEY,
  uniprot_acc TEXT, gene TEXT,
  zf_start INTEGER, zf_end INTEGER, core TEXT,
  mean_plddt REAL,
  imid_degradation_score REAL,
  has_degron_candidate INTEGER,
  screen_degraded INTEGER,
  status TEXT DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS zinc_finger_acc ON zinc_finger (uniprot_acc);
CREATE INDEX IF NOT EXISTS zinc_finger_score ON zinc_finger (imid_degradation_score);
"""

# The documented glutarimide neosubstrates, with the window each is reported
# degraded over where a screen reports one. Used only to audit the table, never
# to fit it.
CANONICAL = {
    "IKZF1": ("Q13422", (141, 198)), "IKZF3": ("Q9UKT9", (146, 168)),
    "SALL4": ("Q9UJQ4", (392, 449)), "ZFP91": ("Q96JP5", (400, 422)),
    "ZNF276": ("Q8N554", (524, 546)), "ZNF692": ("Q9BU19", (417, 439)),
    "ZNF653": ("Q96CK0", (556, 578)),
}


def _scan_one(job: dict) -> list[dict]:
    """Every C2H2 motif of one model, with its mean pLDDT. No scoring here."""
    import gemmi

    from pipeline.degron_sequence import C2H2, align

    accession, path = job["accession"], Path(job["path"])
    try:
        structure = gemmi.read_structure(str(path))
        structure.setup_entities()
        if not len(structure):
            return []
        residues: dict[int, str] = {}
        plddt: dict[int, float] = {}
        for chain in structure[0]:
            for residue in chain:
                code = gemmi.find_tabulated_residue(residue.name)
                if not (code and code.is_amino_acid()):
                    continue
                residues[residue.seqid.num] = code.one_letter_code.upper()
                for atom in residue:
                    if atom.name == "CA":
                        plddt[residue.seqid.num] = atom.b_iso
        if not residues:
            return []
        numbers = sorted(residues)
        first = numbers[0]
        # One contiguous string so the regex can cross a numbering gap; any
        # missing residue becomes X, which no C2H2 pattern matches through.
        sequence = "".join(residues.get(n, "X")
                           for n in range(first, numbers[-1] + 1))
        out = []
        for match in C2H2.finditer(sequence):
            core = align(match.group(0), WIDTH)
            if not core:
                continue
            start = match.start() + first
            end = match.end() + first - 1
            window = [plddt[n] for n in range(start, end + 1) if n in plddt]
            out.append({
                "uniprot_acc": accession,
                "zf_start": start,
                "zf_end": end,
                "core": core,
                "mean_plddt": round(sum(window) / len(window), 2) if window else None,
            })
        return out
    except Exception as exc:  # one unreadable model must not lose the rest
        return [{"uniprot_acc": accession, "error": str(exc)[:200]}]


def screen_labels() -> dict[str, list[tuple[int, int, int]]]:
    """Accession to the windows the Sievers screen assayed, with its POM call.

    Keyed on `Uniprot.Code` and not on `Gene`, because that column mixes gene
    symbols with Swiss-Prot entry names: ADNP2 and CTCF appear as themselves,
    while ZNF276 appears as ZN276 and BCL11A as BC11A. Joining on it silently
    dropped every ZNF gene in the screen, which is most of the library, and left
    3 of 1,178 assayed fingers labelled. A finger is labelled only where an
    assayed window overlaps it, and NULL where the screen never covered it.
    """
    import openpyxl

    book = openpyxl.load_workbook(
        VALIDATION / "raw" / "aat0572_sievers_data-file-s2.xlsx",
        read_only=True, data_only=True)
    stream = book["pval_FDR"].iter_rows(values_only=True)
    index = {str(name): i for i, name in enumerate(next(stream))}
    fdr = float(load_config().t("validation.sievers_fdr"))
    out: dict[str, list[tuple[int, int, int]]] = collections.defaultdict(list)
    for row in stream:
        if not row or not row[index["Gene"]]:
            continue
        try:
            start = int(row[index["AA.Start"]])
            stop = int(row[index["AA.Stop"]])
        except (TypeError, ValueError):
            continue
        value = row[index["POM.FDR"]]
        degraded = 1 if isinstance(value, (int, float)) and value < fdr else 0
        accession = str(row[index["Uniprot.Code"]] or "").strip()
        if accession:
            out[accession].append((start, stop, degraded))
    return out


def run(limit: int | None = None) -> dict:
    from pipeline.degron_predict import encode, train_model
    from pipeline.degron_scan import human_proteome

    config = load_config()
    model, weights, columns, n_positive = train_model()

    gene_of = {row["accession"]: row["gene"]
               for row in human_proteome(Fetcher("afdb", config=config))}

    jobs = []
    for accession in sorted(gene_of):
        path = next(iter(CACHE.glob(f"*{accession}*")), None)
        if path is not None:
            jobs.append({"accession": accession, "path": str(path)})
    if limit:
        jobs = jobs[:limit]
    log_event("2.1b", f"Zinc-finger scan over {len(jobs):,} cached models.")

    workers = int(config.u("compute.cpu_workers"))
    fingers: list[dict] = []
    failures: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for produced in pool.map(_scan_one, jobs, chunksize=16):
            for row in produced:
                (failures if "error" in row else fingers).append(row)

    # Score. Done here rather than in the workers so the fitted model is built
    # once instead of per process.
    for row in fingers:
        row["imid_degradation_score"] = round(float(model.predict_proba(
            (encode(row["core"], columns) * weights).reshape(1, -1))[0, 1]), 4)
        row["gene"] = gene_of.get(row["uniprot_acc"], "")

    # Which fingers the geometry scan already reached, which is the coverage
    # gap D-052 named, measured rather than asserted.
    connection = sqlite3.connect(DB)
    candidates: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    for accession, start, end in connection.execute(
            "SELECT uniprot_acc, start_res, end_res FROM degron WHERE status = 'ok'"):
        candidates[accession].append((start, end))
    labels = screen_labels()
    for row in fingers:
        row["has_degron_candidate"] = int(any(
            not (end < row["zf_start"] or start > row["zf_end"])
            for start, end in candidates.get(row["uniprot_acc"], [])))
        overlapping = [d for start, stop, d in labels.get(row["uniprot_acc"], [])
                       if not (stop < row["zf_start"] or start > row["zf_end"])]
        row["screen_degraded"] = max(overlapping) if overlapping else None

    connection.executescript(SCHEMA)
    connection.execute("DELETE FROM zinc_finger")   # idempotent re-run
    connection.executemany(
        "INSERT INTO zinc_finger (uniprot_acc, gene, zf_start, zf_end, core, "
        "mean_plddt, imid_degradation_score, has_degron_candidate, "
        "screen_degraded) VALUES (?,?,?,?,?,?,?,?,?)",
        [(r["uniprot_acc"], r["gene"], r["zf_start"], r["zf_end"], r["core"],
          r["mean_plddt"], r["imid_degradation_score"],
          r["has_degron_candidate"], r["screen_degraded"]) for r in fingers])
    connection.commit()

    best_per_protein = {}
    for row in fingers:
        current = best_per_protein.get(row["uniprot_acc"])
        if current is None or row["imid_degradation_score"] > current["imid_degradation_score"]:
            best_per_protein[row["uniprot_acc"]] = row

    uncovered = sum(1 for r in fingers if not r["has_degron_candidate"])
    assayed = [r for r in fingers if r["screen_degraded"] is not None]
    report: dict = {
        "n_models_scanned": len(jobs),
        "n_models_unreadable": len(failures),
        "n_fingers": len(fingers),
        "n_proteins_with_a_finger": len(best_per_protein),
        "n_fingers_with_no_hairpin_candidate": uncovered,
        "coverage_gap_pct": round(100.0 * uncovered / len(fingers), 1) if fingers else 0.0,
        "n_fingers_assayed_by_the_screen": len(assayed),
        "n_fingers_screen_degraded": sum(1 for r in assayed if r["screen_degraded"]),
        "training_positives": n_positive,
        "semantics": ("one row per C2H2 motif per protein, with no geometry "
                      "filter in front of it; the per-protein answer is MAX() "
                      "over a protein's fingers"),
        "generalisation_note": ("most canonical substrates below are genes in "
                                "the scorer's training set, so their scores are "
                                "partly memory; see degron_panel (D-053) for "
                                "gene-disjoint evidence"),
        "canonical_audit": {},
    }
    by_protein: dict[str, list[dict]] = collections.defaultdict(list)
    for row in fingers:
        by_protein[row["uniprot_acc"]].append(row)
    for gene, (accession, (start, stop)) in sorted(CANONICAL.items()):
        rows = by_protein.get(accession, [])
        if not rows:
            report["canonical_audit"][gene] = {"found": False}
            continue
        at_degron = [r for r in rows
                     if not (r["zf_end"] < start or r["zf_start"] > stop)]
        best = max(rows, key=lambda r: r["imid_degradation_score"])
        report["canonical_audit"][gene] = {
            "n_fingers": len(rows),
            "best_score": best["imid_degradation_score"],
            "best_finger": f"{best['zf_start']}-{best['zf_end']}",
            "documented_degron": f"{start}-{stop}",
            "score_at_documented_degron": (
                max(r["imid_degradation_score"] for r in at_degron)
                if at_degron else None),
            "in_scorer_training_set": bool(
                any(r["screen_degraded"] for r in at_degron)),
        }

    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    write_jsonl(MANIFEST, fingers)
    connection.close()
    log_event("2.1b", (
        f"Zinc-finger table: {len(fingers):,} C2H2 motifs over "
        f"{len(best_per_protein):,} proteins, of which {uncovered:,} "
        f"({report['coverage_gap_pct']}%) carry no hairpin candidate and were "
        "unreachable by the per-candidate column."))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="scan only the first N models, for a smoke test")
    args = parser.parse_args()
    report = run(limit=args.limit)
    print(json.dumps({k: v for k, v in report.items() if k != "canonical_audit"},
                     indent=2))
    print("\ncanonical substrate audit (* is in the scorer's training set):")
    for gene, entry in report["canonical_audit"].items():
        if not entry.get("n_fingers"):
            print(f"  {gene:<8} not found"); continue
        mark = " *" if entry["in_scorer_training_set"] else ""
        at = entry["score_at_documented_degron"]
        print(f"  {gene:<8} {entry['n_fingers']} fingers, best "
              f"{entry['best_score']:.3f} at {entry['best_finger']}, "
              f"documented degron {entry['documented_degron']} scores "
              f"{'none' if at is None else f'{at:.3f}'}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
