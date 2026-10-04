"""Two ways to raise the degron AUC, both measured, both worse.

The shipped `imid_degradation_score` is a logistic fit on C2H2-anchored
chemical-group features, weighted by the Slabicki alanine scan, trained on the
Sievers pomalidomide degrome. Its nested AUC is 0.830 and its binding
constraint is obvious: **14 positives**. Two obvious ways to get past that,
asked here so the answer is on record rather than re-derived later:

1. **Borrow labels from related compounds.** D-053 showed the degron grammar
   transfers: a pomalidomide model ranks the other 28 glutarimides above chance.
   If the grammar is shared, training on the union should give more positives at
   no cost. Trained on each union and scored against pomalidomide labels with
   whole genes held out, it costs rather than pays, and the more compounds are
   added the worse it gets.

2. **Drop the positions the alanine scan says do not matter.** With 14
   positives, fewer parameters should generalise better, and the scan measured
   which positions carry the degron.

**The second one is the interesting failure.** Sweeping k and taking the best
gives 0.840 against the shipped 0.830, which looks like a small win. It is not a
win, it is the sweep reading its own answer sheet: k was chosen by looking at the
number being reported, over nine values, on a five-fold estimate whose fold sd is
0.08. Choosing k honestly on inner folds instead gives **0.745**, which is 0.086
*worse* than shipped, and the inner folds disagree about k from fold to fold
(20, 18, 12, 12, 20), which is what no stable signal looks like.

The swing between the two estimates is 0.095, on the same data, from the same
code, differing only in whether the choice was allowed to see the test fold.
That is worth more than either number.

**Conclusion.** The shipped configuration is a local optimum for the data
available. Neither borrowing labels nor trimming features gets past 14
positives, and the honest way to raise this metric is a bigger matched screen.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    INTERIM, VALIDATION, load_config, log_event,
)
from pipeline.degron_alascan import weights_vector  # noqa: E402
from pipeline.degron_sequence import featurise, per_compound_labels  # noqa: E402

REPORT = INTERIM / "degron_ablation.json"
TARGET = "POM"
# Label sets to try, each scored against pomalidomide.
COMBINATIONS = [
    ("POM",),
    ("LEN", "POM"),
    ("THAL", "LEN", "POM"),
    ("POM", "CC122", "CC220"),
    ("THAL", "LEN", "POM", "CC122", "CC220"),
]
POSITION_COUNTS = [8, 12, 14, 16, 18, 20, None]   # None keeps all 23


def _setup():
    import numpy as np

    rows = [r for r in csv.DictReader(
        (VALIDATION / "sievers_zf_screen.tsv").open(encoding="utf-8"),
        delimiter="\t") if r.get("aa_sequence")]
    features, _labels, _g, columns, kept = featurise(rows)
    genes = np.asarray([r["gene"] for r in kept])
    keys = [(r["gene"], int(r["zf_start"]), int(r["zf_stop"])) for r in kept]
    importance = json.loads(
        (INTERIM / "degron_alascan_importance.json").read_text())
    weights = weights_vector(columns, importance)
    return features * weights, genes, keys, columns, importance


def _fit_auc(matrix, train, test, labels):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    model = LogisticRegression(C=0.05, max_iter=5000, class_weight="balanced",
                               solver="liblinear").fit(matrix[train], labels[train])
    return roc_auc_score(labels[test], model.decision_function(matrix[test]))


def run() -> dict:
    import numpy as np
    from sklearn.model_selection import StratifiedGroupKFold

    seed = int(load_config().t("validation.panel_seed"))
    matrix, genes, keys, columns, importance = _setup()
    signature = per_compound_labels()
    target = np.asarray(
        [1 if k in signature.get(TARGET, set()) else 0 for k in keys])

    report: dict = {
        "question": ("can the degron AUC be raised by borrowing labels from "
                     "related compounds, or by dropping positions the alanine "
                     "scan says do not matter"),
        "scored_against": TARGET,
        "n_target_positives": int(target.sum()),
        "positives_per_compound": {
            drug: int(sum(1 for k in keys if k in positives))
            for drug, positives in sorted(signature.items())
        },
        "pooling": [],
        "position_sweep": [],
    }

    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    folds = [(tr, te) for tr, te in outer.split(matrix, target, groups=genes)
             if target[tr].sum() >= 4 and target[te].sum() > 0]

    # 1. borrowing labels
    for drugs in COMBINATIONS:
        union = set().union(*[signature.get(d, set()) for d in drugs])
        train_labels = np.asarray([1 if k in union else 0 for k in keys])
        scores = [_fit_auc_mixed(matrix, tr, te, train_labels, target)
                  for tr, te in folds]
        report["pooling"].append({
            "train_on": list(drugs),
            "n_training_positives": int(train_labels.sum()),
            "auc_mean": round(float(np.mean(scores)), 4),
            "auc_sd": round(float(np.std(scores)), 4),
        })

    # 2. dropping positions, both ways round
    f1 = {int(k): v for k, v in importance.get("importance_finger_1", {}).items()}
    f2 = {int(k): v for k, v in importance.get("importance_finger_2", {}).items()}
    ranked = [p for p, _v in sorted(
        {p: max(f1.get(p, 0.0), f2.get(p, 0.0)) for p in range(23)}.items(),
        key=lambda kv: -kv[1])]

    def position_of(name):
        head = name.split(":")[0]
        return int(head[1:]) if head.startswith("p") and head[1:].isdigit() else None

    positions = [position_of(c) for c in columns]

    def mask_for(k):
        if k is None:
            return np.ones(len(columns), dtype=bool)
        keep = set(ranked[:k])
        return np.asarray([(p in keep) if p is not None else True for p in positions])

    for k in POSITION_COUNTS:
        subset = matrix[:, mask_for(k)]
        scores = [_fit_auc(subset, tr, te, target) for tr, te in folds]
        report["position_sweep"].append({
            "k": k, "n_features": int(mask_for(k).sum()),
            "auc_mean": round(float(np.mean(scores)), 4),
            "auc_sd": round(float(np.std(scores)), 4),
        })

    shipped = [e for e in report["position_sweep"] if e["k"] is None][0]["auc_mean"]
    best = max(report["position_sweep"], key=lambda e: e["auc_mean"])

    # The same selection done honestly: k chosen inside the training half.
    nested_scores, picked = [], []
    for train, test in folds:
        inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed + 1)
        best_k, best_inner = None, -1.0
        for k in POSITION_COUNTS:
            subset = matrix[:, mask_for(k)]
            inner_scores = []
            for a, b in inner.split(matrix[train], target[train], groups=genes[train]):
                if target[train][a].sum() < 2 or target[train][b].sum() == 0:
                    continue
                inner_scores.append(_fit_auc(subset, train[a], train[b], target))
            if inner_scores and float(np.mean(inner_scores)) > best_inner:
                best_k, best_inner = k, float(np.mean(inner_scores))
        picked.append(best_k)
        nested_scores.append(_fit_auc(matrix[:, mask_for(best_k)], train, test, target))

    report["position_selection_nested"] = {
        "k_picked_per_outer_fold": picked,
        "auc_mean": round(float(np.mean(nested_scores)), 4),
        "auc_sd": round(float(np.std(nested_scores)), 4),
        "shipped_auc": shipped,
        "difference_vs_shipped": round(float(np.mean(nested_scores)) - shipped, 4),
        "sweep_best_auc": best["auc_mean"],
        "sweep_best_k": best["k"],
        "selection_bias": round(best["auc_mean"] - float(np.mean(nested_scores)), 4),
        "what_this_measures": (
            "the sweep picks k by looking at the number it reports; the nested "
            "run picks k inside the training half. The gap between them is how "
            "much a 14-positive problem flatters a choice that sees its own "
            "test fold."
        ),
    }
    report["conclusion"] = (
        "Neither route improves on the shipped configuration. Borrowing labels "
        "costs AUC and costs more the more compounds are added; selecting "
        "positions costs "
        f"{abs(report['position_selection_nested']['difference_vs_shipped'])} "
        "once the choice is made honestly. The binding constraint is 14 "
        "positives, and the way past it is a bigger matched screen."
    )
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    log_event("9.2", (
        f"Degron ablation: pooling and position selection both lose to the "
        f"shipped model ({shipped}); nested position selection scores "
        f"{report['position_selection_nested']['auc_mean']}."))
    return report


def _fit_auc_mixed(matrix, train, test, train_labels, test_labels):
    """Train on one label set, score against another."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    model = LogisticRegression(C=0.05, max_iter=5000, class_weight="balanced",
                               solver="liblinear").fit(matrix[train],
                                                       train_labels[train])
    return roc_auc_score(test_labels[test], model.decision_function(matrix[test]))


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    report = run()
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("pooling", "position_sweep")}, indent=2))
    print("\nborrowing labels from related compounds (scored against POM):")
    for entry in report["pooling"]:
        print(f"  {'+'.join(entry['train_on']):<32} "
              f"{entry['n_training_positives']:>3} pos   "
              f"{entry['auc_mean']:.4f}")
    print("\ndropping positions, k chosen by looking at the answer:")
    for entry in report["position_sweep"]:
        label = "all" if entry["k"] is None else f"top-{entry['k']}"
        print(f"  {label:<8} {entry['n_features']:>4} features   {entry['auc_mean']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
