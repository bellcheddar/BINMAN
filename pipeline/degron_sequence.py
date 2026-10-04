"""Can anything separate a degraded zinc finger from an undegraded one?

Spec 9.2 measured the geometric filter against the Sievers matched screen and
it ranked at chance: ROC AUC 0.441, below 0.5 (DECISIONS D-024). The diagnosis
was that a C2H2 zinc finger *is* a short antiparallel hairpin with an exposed
glycine-bearing turn, so the geometry describes the domain family rather than
degradability. D-024 named the reversal condition: a feature that discriminates
**within** the family.

This module tests that condition honestly. It aligns every assayed zinc finger
on its C2H2 anchors, encodes the residues at each aligned position, and asks
whether a regularised linear model can separate the 32 depleted domains from
the 5,631 that were assayed and not depleted.

**Why this is hard, stated before the result.** The classic IMiD G-loop is
necessary and not sufficient. IKZF3 reads `FQCNQC-G-ASF` and is degraded; ZFP30
reads `YECKEC-G-KAF` and is not, and the two are near-identical. Any honest
model has to separate cases that differ by a residue or two.

**Why the evaluation is grouped and repeated.** There are 32 positives. A
single train/test split would put ten or so in the test half and the AUC would
swing on which ones landed there. Splits are therefore grouped by gene, so no
protein appears in both halves, and repeated, and the spread is reported beside
the mean. A mean with no spread, on 32 positives, would be a number pretending
to a precision it does not have.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, VALIDATION, log_event  # noqa: E402

# C2H2: two cysteines, then twelve residues, then two histidines. Matching the
# anchors rather than counting from the N-terminus is what makes positions
# comparable across domains of different recorded lengths.
C2H2 = re.compile(r"C.{2,4}C.{10,14}H.{3,5}H")

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

# Residues are grouped as well as encoded individually: with 32 positives a
# per-residue one-hot has more columns than examples, and chemistry is the
# prior that keeps it from memorising.
GROUPS = {
    "hydrophobic": set("AVLIMFWC"),
    "aromatic": set("FWYH"),
    "positive": set("KRH"),
    "negative": set("DE"),
    "polar": set("STNQ"),
    "tiny": set("GAS"),
    "glycine": set("G"),
    "proline": set("P"),
}


def anchored(sequence: str) -> str | None:
    """Return the zinc finger trimmed to its C2H2 core, or None if it has none."""
    match = C2H2.search(sequence or "")
    return match.group(0) if match else None


def align(core: str, width: int = 23) -> str | None:
    """Pad or trim an anchored core to a fixed width.

    The spacing between the cysteines and between the histidines varies, so
    cores differ in length. They are anchored at the first cysteine and padded
    on the right, which keeps the hairpin region, the part that matters, in
    register.
    """
    if core is None:
        return None
    if len(core) >= width:
        return core[:width]
    return core + "-" * (width - len(core))


def featurise(rows: list[dict], width: int = 23):
    import numpy as np

    aligned, labels, genes, kept = [], [], [], []
    for row in rows:
        core = align(anchored(row.get("aa_sequence", "")), width)
        if core is None:
            continue
        aligned.append(core)
        labels.append(int(row["degraded"]))
        genes.append(row["gene"])
        kept.append(row)

    columns: list[str] = []
    matrix = []
    for position in range(width):
        for group, members in GROUPS.items():
            columns.append(f"p{position}:{group}")
            matrix.append([1.0 if core[position] in members else 0.0
                           for core in aligned])
    features = np.asarray(matrix, dtype=float).T
    return features, np.asarray(labels), genes, columns, kept


def evaluate(features, labels, genes, repeats: int = 25, seed: int = 20261004):
    """Grouped, repeated, stratified evaluation. Returns per-split AUCs."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold

    scores = []
    for repeat in range(repeats):
        splitter = StratifiedGroupKFold(n_splits=4, shuffle=True,
                                        random_state=seed + repeat)
        for train_index, test_index in splitter.split(features, labels, groups=genes):
            if labels[test_index].sum() == 0 or labels[train_index].sum() == 0:
                continue
            model = LogisticRegression(
                C=0.05, max_iter=5000,
                class_weight="balanced", solver="liblinear")
            model.fit(features[train_index], labels[train_index])
            predicted = model.decision_function(features[test_index])
            scores.append(roc_auc_score(labels[test_index], predicted))
    return np.asarray(scores)


def permutation_null(features, labels, genes, rounds: int = 200,
                     seed: int = 20261004) -> dict:
    """What AUC does this pipeline reach when the labels mean nothing?

    With 32 positives and 184 columns, a model can reach an AUC above 0.5 by
    exploiting the group structure alone: zinc fingers from paralogous families
    resemble each other, and grouping by gene does not separate ZN184 from
    ZN276. Shuffling the labels **within the same grouped splitting** measures
    exactly that, and the real score is only interesting to the extent it beats
    this.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    null = []
    for _ in range(rounds):
        shuffled = labels.copy()
        rng.shuffle(shuffled)
        scores = evaluate(features, shuffled, genes, repeats=1, seed=seed)
        if len(scores):
            null.append(float(scores.mean()))
    null_array = np.asarray(null)
    return {
        "rounds": int(len(null_array)),
        "null_mean": round(float(null_array.mean()), 4),
        "null_std": round(float(null_array.std()), 4),
        "null_p95": round(float(np.percentile(null_array, 95)), 4),
    }


def out_of_fold_operating_points(features, labels, genes,
                                 seed: int = 20261004) -> dict:
    """Sensitivity and specificity the sequence model can actually reach.

    Spec 9.2 asks for sensitivity 0.70 AND specificity 0.60 together. An AUC
    says nothing about whether any single cut satisfies both, so the curve is
    swept on out-of-fold predictions, where every domain is scored by a model
    that never saw its gene.
    """
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold

    predictions = np.full(len(labels), np.nan)
    splitter = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed)
    for train_index, test_index in splitter.split(features, labels, groups=genes):
        model = LogisticRegression(C=0.05, max_iter=5000,
                                   class_weight="balanced", solver="liblinear")
        model.fit(features[train_index], labels[train_index])
        predictions[test_index] = model.decision_function(features[test_index])

    scored = ~np.isnan(predictions)
    values, truth = predictions[scored], labels[scored]
    n_pos, n_neg = int(truth.sum()), int((1 - truth).sum())

    best, passing = None, None
    for cut in np.unique(values):
        called = values >= cut
        sensitivity = float((called & (truth == 1)).sum() / n_pos)
        specificity = float(((~called) & (truth == 0)).sum() / n_neg)
        point = {"cut": round(float(cut), 4),
                 "sensitivity": round(sensitivity, 4),
                 "specificity": round(specificity, 4),
                 "youden_j": round(sensitivity + specificity - 1, 4)}
        if best is None or point["youden_j"] > best["youden_j"]:
            best = point
        if sensitivity >= 0.70 and specificity >= 0.60 and passing is None:
            passing = point
    return {"best_youden": best, "any_cut_clears_spec_92_floors": passing,
            "n_positive": n_pos, "n_negative": n_neg}


def fold_depletion_targets() -> dict[tuple[str, int, int], float]:
    """Mean fold depletion per zinc finger, straight from Sievers data file S2.

    The binary labels throw most of the screen away: 32 positives out of 5,663,
    when the experiment measured a continuous depletion for every domain across
    three drugs and three replicates. Regressing on that signal and then ranking
    by the prediction uses the whole experiment, and the binary labels are kept
    only to score the ranking.
    """
    import statistics

    import openpyxl

    path = VALIDATION / "raw" / "aat0572_sievers_data-file-s2.xlsx"
    if not path.exists():
        return {}
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["Folddepletion"]
    stream = sheet.iter_rows(values_only=True)
    header = list(next(stream))
    index = {name: position for position, name in enumerate(header)}

    targets: dict[tuple[str, int, int], float] = {}
    for row in stream:
        if not row or not row[index["Gene"]]:
            continue
        replicates = [row[index[f"{drug}.REP{n}"]]
                      for drug in ("THAL", "LEN", "POM") for n in (1, 2, 3)
                      if f"{drug}.REP{n}" in index]
        replicates = [v for v in replicates if isinstance(v, (int, float))]
        if not replicates:
            continue
        key = (str(row[index["Gene"]]), int(row[index["AA.Start"]]),
               int(row[index["AA.Stop"]]))
        # The mean across drugs and replicates, not the max: the max is the
        # noisiest statistic in the table and would chase single bad wells.
        targets[key] = float(statistics.mean(replicates))
    return targets


def evaluate_regression(features, labels, genes, keys, targets,
                        repeats: int = 25, seed: int = 20261004):
    """Fit on continuous depletion, score the ranking against the binary labels."""
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold

    depletion = np.asarray([targets.get(k, np.nan) for k in keys], dtype=float)
    usable = ~np.isnan(depletion)
    if usable.sum() < 100:
        return np.asarray([]), int(usable.sum())

    features, labels = features[usable], labels[usable]
    genes = [g for g, keep in zip(genes, usable) if keep]
    depletion = depletion[usable]

    scores = []
    for repeat in range(repeats):
        splitter = StratifiedGroupKFold(n_splits=4, shuffle=True,
                                        random_state=seed + repeat)
        for train_index, test_index in splitter.split(features, labels, groups=genes):
            if labels[test_index].sum() == 0:
                continue
            model = Ridge(alpha=50.0)
            model.fit(features[train_index], depletion[train_index])
            predicted = model.predict(features[test_index])
            scores.append(roc_auc_score(labels[test_index], predicted))
    return np.asarray(scores), int(usable.sum())


def run(repeats: int = 25, permutations: int = 200) -> dict:
    path = VALIDATION / "sievers_zf_screen.tsv"
    if not path.exists():
        raise SystemExit(f"{path} does not exist: acquire sievers_zf_screen first")
    with path.open(encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle, delimiter="\t")
                if r.get("aa_sequence")]

    import numpy as np

    features, labels, genes, columns, kept = featurise(rows)
    scores = evaluate(features, labels, genes, repeats=repeats)

    # The same features, fitted to the continuous depletion instead of the
    # 32 binary positives.
    targets = fold_depletion_targets()
    keys = [(r["gene"], int(r["zf_start"]), int(r["zf_stop"])) for r in kept]
    regression_scores, n_with_target = evaluate_regression(
        features, labels, genes, keys, targets, repeats=repeats)

    null = permutation_null(features, labels, genes, rounds=permutations)
    observed = float(scores.mean()) if len(scores) else float("nan")
    # One-sided empirical p: how often does a meaningless label set reach this?
    report = {
        "n_domains": int(len(labels)),
        "n_degraded": int(labels.sum()),
        "n_not_degraded": int(len(labels) - labels.sum()),
        "n_dropped_no_c2h2": len(rows) - len(labels),
        "n_features": features.shape[1],
        "splits_scored": int(len(scores)),
        "auc_mean": round(float(scores.mean()), 4) if len(scores) else None,
        "auc_std": round(float(scores.std()), 4) if len(scores) else None,
        "auc_min": round(float(scores.min()), 4) if len(scores) else None,
        "auc_max": round(float(scores.max()), 4) if len(scores) else None,
        "geometry_auc_for_comparison": 0.4407,
        "regression_on_fold_depletion": {
            "n_domains_with_a_depletion_value": n_with_target,
            "splits_scored": int(len(regression_scores)),
            "auc_mean": (round(float(regression_scores.mean()), 4)
                         if len(regression_scores) else None),
            "auc_std": (round(float(regression_scores.std()), 4)
                        if len(regression_scores) else None),
            "note": ("Ridge on the mean fold depletion across three drugs and "
                     "three replicates, ranked and scored against the binary "
                     "labels. Uses the whole experiment rather than its 32 "
                     "significant calls."),
        },
        "permutation_null": null,
        "operating_points": out_of_fold_operating_points(features, labels, genes),
        "beats_null_by_sd": (
            round((observed - null["null_mean"]) / null["null_std"], 2)
            if null.get("null_std") else None),
        "above_null_p95": bool(observed > null.get("null_p95", 1.0)),
        "method": (
            "Sequence only. Zinc fingers anchored on the C2H2 motif, aligned to "
            "23 positions, each position encoded as eight overlapping chemical "
            "groups. L2 logistic regression at C=0.05 with balanced class "
            "weights, evaluated by repeated stratified group k-fold so no gene "
            "appears in both halves of a split."
        ),
    }
    log_event("5.2", f"Sequence model over {report['n_domains']:,} zinc fingers: "
                     f"held-out AUC {report['auc_mean']} "
                     f"(sd {report['auc_std']}) against the geometry's 0.4407.")
    (INTERIM / "degron_sequence_fit.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return report


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
