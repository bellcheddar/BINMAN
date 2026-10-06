"""Does geometry add anything to the sequence model, or take away?

Spec 9.2 reports two scores for the same question. The shipped geometry score
reaches ROC AUC 0.4407, below chance, and the sequence model reaches 0.6363
over gene-grouped repeated splits. D-072 and D-075 explain the first number:
one of its three components is a constant, and the other two are inverted.

An inverted feature is not an empty one. A model free to give it a negative
weight can use it, which a fixed positive-weighted sum cannot. So the question
this module asks is not whether geometry is good, which is settled, but whether
a model that knows geometry is backwards does better than one that never sees
it.

Everything here runs the protocol pipeline/degron_sequence.py already uses, on
the same rows, with the same seeds: StratifiedGroupKFold over four folds
grouped by gene so no protein spans a split, repeated, with the spread reported
beside the mean because 32 positives cannot support a single number. The
permutation null is measured the same way, because a difference between two
means is only interesting against the spread of both.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    ATLAS, INTERIM, VALIDATION, Manifest, load_config, log_event, utcnow,
)
from pipeline.degron_sequence import evaluate, featurise, permutation_null  # noqa: E402

STAGE = "degron_combined"
REPORT = INTERIM / "degron_combined.json"
DEFAULT_DB = ATLAS / "binman.sqlite"

# The geometry the atlas carries per candidate. regularity is included although
# D-075 measures it as a constant: leaving it out because it looked useless in
# one analysis would be deciding the answer before running the test, and a
# regularised model can drop it itself.
GEOMETRY = ["degron_geometry_score", "mean_plddt", "tip_rel_sasa", "regularity"]


def geometry_features(kept: list[dict], db_path: Path):
    """One geometry row per assayed finger, aligned to the sequence rows.

    A finger the geometry filter never called has no values to read. It gets
    zeros and a `called` flag of 0, so the model can tell "not called" from
    "called with a low score" instead of having the two collapsed into one
    number, which is what the 0.0 sentinel in the spec 9.2 AUC does.
    """
    import numpy as np

    config = load_config()
    floor = int(config.thresholds["validation"]["degron_overlap_residues"])
    connection = sqlite3.connect(db_path)
    try:
        candidates: dict[str, list] = {}
        for row in connection.execute(
                f"SELECT uniprot_acc, start_res, end_res, {', '.join(GEOMETRY)} "
                f"FROM degron WHERE status = 'ok'"):
            candidates.setdefault(row[0], []).append(
                (int(row[1]), int(row[2]), row[3:]))
    finally:
        connection.close()

    matrix = []
    called_count = 0
    for row in kept:
        accession = (row.get("uniprot") or "").strip()
        try:
            start, stop = int(row["zf_start"]), int(row["zf_stop"])
        except (KeyError, TypeError, ValueError):
            matrix.append([0.0] * len(GEOMETRY) + [0.0])
            continue
        hits = [values for low, high, values in candidates.get(accession, ())
                if min(stop, high) - max(start, low) + 1 >= floor]
        if not hits:
            matrix.append([0.0] * len(GEOMETRY) + [0.0])
            continue
        called_count += 1
        best = [max((float(h[i]) for h in hits if h[i] is not None), default=0.0)
                for i in range(len(GEOMETRY))]
        matrix.append(best + [1.0])
    return np.asarray(matrix, dtype=float), called_count, GEOMETRY + ["called"]


def run(repeats: int = 25, permutations: int = 200,
        db_path: Path = DEFAULT_DB) -> dict:
    import numpy as np

    path = VALIDATION / "sievers_zf_screen.tsv"
    if not path.exists():
        raise SystemExit(f"{path} does not exist: acquire sievers_zf_screen first")
    with path.open(encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle, delimiter="\t")
                if r.get("aa_sequence")]

    sequence, labels, genes, columns, kept = featurise(rows)
    geometry, called, geometry_columns = geometry_features(kept, db_path)
    # Standardised so the logistic penalty falls on both blocks alike. Without
    # it pLDDT at 70-to-99 would be penalised differently from a 0/1 sequence
    # indicator purely because of its units.
    spread = geometry.std(axis=0)
    spread[spread == 0] = 1.0
    geometry_z = (geometry - geometry.mean(axis=0)) / spread
    combined = np.hstack([sequence, geometry_z])

    log_event("5.2", f"Combined degron model: {len(kept):,} fingers, "
                     f"{int(labels.sum())} degraded, {called:,} called by the "
                     f"geometry filter, {sequence.shape[1]} sequence features "
                     f"and {geometry_z.shape[1]} geometry features.")

    out: dict = {"generated_at": utcnow(), "n_domains": len(kept),
                 "n_degraded": int(labels.sum()),
                 "n_called_by_geometry": called,
                 "n_sequence_features": int(sequence.shape[1]),
                 "n_geometry_features": int(geometry_z.shape[1]),
                 "protocol": ("StratifiedGroupKFold, 4 folds grouped by gene, "
                              f"{repeats} repeats, identical seeds to "
                              "pipeline/degron_sequence.py")}

    for name, matrix in (("sequence_only", sequence),
                         ("geometry_only", geometry_z),
                         ("combined", combined)):
        scores = evaluate(matrix, labels, genes, repeats=repeats)
        out[name] = {
            "auc_mean": round(float(scores.mean()), 4),
            "auc_std": round(float(scores.std()), 4),
            "auc_min": round(float(scores.min()), 4),
            "auc_max": round(float(scores.max()), 4),
            "splits_scored": int(scores.size),
        }
        log_event("5.2", f"{name}: AUC {scores.mean():.4f} "
                         f"+/- {scores.std():.4f} over {scores.size} splits.")

    null = permutation_null(combined, labels, genes, rounds=permutations)
    out["combined_permutation_null"] = null
    gain = out["combined"]["auc_mean"] - out["sequence_only"]["auc_mean"]
    # Measured against the spread of the splits, not asserted. A gain smaller
    # than the split-to-split noise is not a gain.
    out["gain_over_sequence"] = round(float(gain), 4)
    out["gain_in_units_of_sequence_sd"] = round(
        float(gain / max(out["sequence_only"]["auc_std"], 1e-9)), 2)
    REPORT.write_text(json.dumps(out, indent=2) + "\n")
    Manifest(STAGE).record(
        "fit", status="ok",
        sequence_auc=out["sequence_only"]["auc_mean"],
        geometry_auc=(out.get("geometry_only") or {}).get("auc_mean"),
        combined_auc=out["combined"]["auc_mean"],
        gain_over_sequence=out["gain_over_sequence"])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=25)
    parser.add_argument("--permutations", type=int, default=200)
    args = parser.parse_args()
    print(json.dumps(run(repeats=args.repeats,
                         permutations=args.permutations), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
