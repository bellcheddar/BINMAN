"""The Slabicki 2025 primary screen, per compound, with a validated threshold.

Spec 9.2 named "the Molecular Cell 2025 druggable zinc-finger proteome study"
and it never resolved during the build, so the degron metric was measured
against Sievers 2018 instead (D-024). This is that study:
10.1016/j.molcel.2025.07.019, 9,097 zinc-finger reporters from 1,655 proteins.

**Why it matters here.** D-046 found that the pooled "degraded by any IMiD"
label was the thing holding the AUC down, and that per-compound models reach
0.826 for pomalidomide. But Sievers gives only 8 to 14 positives per compound,
which cannot support a validated decision threshold: the operating points in
D-046 pick their cut by scanning the same held-out predictions they are scored
on. This screen gives 257 and 316 positives per compound after
Benjamini-Hochberg correction, which is enough for **nested** cross-validation,
where the cut is chosen on an inner split and measured on an outer one it has
never seen.

**What is missing, stated plainly.** The published `.xls` is truncated at
65,535 rows, the legacy Excel limit, so 2 of the paper's 29 compounds survive:
`4-Ac-Phe-Glm` and `ALV1`. That is a defect in the distributed file, not in the
study. The two that remain are still an order of magnitude more positives per
compound than anything else available.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, VALIDATION, log_event  # noqa: E402
from pipeline.degron_sequence import align, anchored, GROUPS  # noqa: E402

PRIMARY = VALIDATION / "raw" / "NIHMS2104733-supplement-4.xls"
FDR = 0.05


def benjamini_hochberg(pvalues):
    """BH-adjusted q-values. Spelled out so the correction is auditable."""
    import numpy as np

    pvalues = np.asarray(pvalues, dtype=float)
    n = len(pvalues)
    order = np.argsort(pvalues)
    q = np.empty(n)
    running = 1.0
    for rank, index in enumerate(order[::-1]):
        running = min(running, pvalues[index] * n / (n - rank))
        q[index] = running
    return q


def load_primary() -> dict:
    """Sequences and per-compound depletion from the primary screen."""
    import numpy as np
    import xlrd

    if not PRIMARY.exists():
        raise SystemExit(f"{PRIMARY} does not exist")

    book = xlrd.open_workbook(str(PRIMARY), on_demand=True)

    # Construct sequences. The two library sheets carry the same constructs.
    sheet = book.sheet_by_name("ZF.Primary.Cilantro")
    header = [str(sheet.cell_value(0, c)) for c in range(sheet.ncols)]
    index = {name: i for i, name in enumerate(header)}
    sequence: dict[str, str] = {}
    gene: dict[str, str] = {}
    for row in range(1, sheet.nrows):
        # Library `Name` is "GENE_start-end;Category"; the ratio table keys on
        # "GENE_start-end" alone, so the category suffix is dropped to join.
        name = str(sheet.cell_value(row, index["Name"])).split(";")[0].strip()
        # `ZnF.Sequence` is DNA. The amino acids are in `Construct_AA`, which is
        # the 58-residue construct the C2H2 anchor is then found within.
        sequence[name] = str(sheet.cell_value(row, index["Construct_AA"]))
        gene[name] = str(sheet.cell_value(row, index["Gene_Name"]))
    book.unload_sheet("ZF.Primary.Cilantro")

    # Depletion. Gate A is the EGFP-high population: a construct depleted there
    # under drug is one the drug degraded.
    sheet = book.sheet_by_name("Screen.Primary_Ratio_pval")
    header = [str(sheet.cell_value(0, c)) for c in range(sheet.ncols)]
    index = {name: i for i, name in enumerate(header)}
    best: dict[str, dict[str, tuple[float, float]]] = collections.defaultdict(dict)
    for row in range(1, sheet.nrows):
        if sheet.cell_value(row, index["Gate"]) != "A":
            continue
        drug = str(sheet.cell_value(row, index["Drug"]))
        construct = str(sheet.cell_value(row, index["Construct.ZnF"]))
        try:
            p = float(sheet.cell_value(row, index["p_value"]))
            lfc = float(sheet.cell_value(row, index["LFC"]))
        except (ValueError, TypeError):
            continue
        # The two libraries measure the same construct twice; keep the stronger
        # evidence rather than averaging a pair that can disagree in sign.
        previous = best[drug].get(construct)
        if previous is None or p < previous[0]:
            best[drug][construct] = (p, lfc)

    labels: dict[str, dict[str, int]] = {}
    for drug, measured in best.items():
        names = list(measured)
        q = benjamini_hochberg([measured[n][0] for n in names])
        lfc = np.asarray([measured[n][1] for n in names])
        labels[drug] = {name: int(bool(q[i] < FDR and lfc[i] < 0))
                        for i, name in enumerate(names)}
    return {"sequence": sequence, "gene": gene, "labels": labels}


def featurise(names, sequence, width: int = 23):
    """Encode BOTH zinc fingers of each construct.

    These are 58-residue constructs and 5,201 of the 9,097 carry two C2H2
    motifs: the library is built from tandem finger pairs. Anchoring on the
    first match encodes finger 1 and throws finger 2 away, and the degron can
    be in either, so more than half the library was being described by the
    wrong half of itself. Both fingers get their own block of positions, and a
    construct with only one finger has the second block zeroed.

    Constructs with no C2H2 motif at all (1,877 of them, the non-C2H2 and MYM
    zinc-finger classes) are dropped: the glutarimide degron is a C2H2 feature
    and those are a different fold being asked a question that does not apply.
    """
    import numpy as np

    from pipeline.degron_sequence import C2H2

    kept = []
    for name in names:
        text = sequence.get(name, "")
        cores = [align(m.group(0), width) for m in C2H2.finditer(text)]
        cores = [c for c in cores if c]
        if not cores:
            continue
        first = cores[0]
        second = cores[1] if len(cores) > 1 else None
        kept.append((name, first, second))

    columns, matrix = [], []
    for slot, label in ((0, "f1"), (1, "f2")):
        for position in range(width):
            for group, members in GROUPS.items():
                columns.append(f"{label}:p{position}:{group}")
                column = []
                for _n, first, second in kept:
                    core = first if slot == 0 else second
                    column.append(0.0 if core is None
                                  else (1.0 if core[position] in members else 0.0))
                matrix.append(column)
    # Whether a second finger exists at all is itself informative.
    columns.append("has_second_finger")
    matrix.append([0.0 if second is None else 1.0 for _n, _f, second in kept])
    return np.asarray(matrix, dtype=float).T, [n for n, _f, _s in kept], columns


def nested_evaluate(features, labels, genes, seed: int = 20261004,
                    objective: str = "youden", spec_floor: float = 0.60):
    """Outer folds score a threshold chosen on inner folds only.

    This is what D-046 could not do. The cut is selected by Youden's J on an
    inner split of the training half, then applied unchanged to an outer fold
    the model and the threshold have both never seen, so the reported
    sensitivity and specificity are honest rather than optimistic.
    """
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold

    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    aucs, sens, spec = [], [], []
    for train_index, test_index in outer.split(features, labels, groups=genes):
        train_genes = [genes[i] for i in train_index]
        inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed + 1)
        inner_scores, inner_truth = [], []
        for a, b in inner.split(features[train_index], labels[train_index],
                                groups=train_genes):
            model = LogisticRegression(C=0.05, max_iter=5000,
                                       class_weight="balanced", solver="liblinear")
            model.fit(features[train_index][a], labels[train_index][a])
            inner_scores.extend(model.decision_function(features[train_index][b]))
            inner_truth.extend(labels[train_index][b])
        inner_scores = np.asarray(inner_scores)
        inner_truth = np.asarray(inner_truth)

        # Choose the cut on the inner predictions only. Two objectives:
        #
        #   youden    maximise sensitivity + specificity, the usual default
        #   floors    maximise sensitivity subject to specificity >= the spec
        #             floor, which is what spec 9.2 actually asks for
        #
        # Youden spends the budget symmetrically and leaves specificity well
        # above its floor while sensitivity sits below its own. The objective
        # should match the acceptance criterion, and the criterion is fixed by
        # the spec rather than chosen after seeing a result.
        pos, neg = inner_truth.sum(), (1 - inner_truth).sum()
        cut, best = 0.0, -1.0
        for candidate in np.unique(inner_scores):
            called = inner_scores >= candidate
            sensitivity = (called & (inner_truth == 1)).sum() / pos
            specificity = ((~called) & (inner_truth == 0)).sum() / neg
            if objective == "floors":
                score = sensitivity if specificity >= spec_floor else -1.0
            else:
                score = sensitivity + specificity - 1.0
            if score > best:
                cut, best = float(candidate), float(score)

        model = LogisticRegression(C=0.05, max_iter=5000,
                                   class_weight="balanced", solver="liblinear")
        model.fit(features[train_index], labels[train_index])
        outer_scores = model.decision_function(features[test_index])
        outer_truth = labels[test_index]
        if outer_truth.sum() == 0 or (1 - outer_truth).sum() == 0:
            continue
        aucs.append(roc_auc_score(outer_truth, outer_scores))
        called = outer_scores >= cut
        sens.append(float((called & (outer_truth == 1)).sum() / outer_truth.sum()))
        spec.append(float(((~called) & (outer_truth == 0)).sum()
                          / (1 - outer_truth).sum()))
    return np.asarray(aucs), np.asarray(sens), np.asarray(spec)


def run() -> dict:
    import numpy as np

    data = load_primary()
    report: dict = {
        "source": "Slabicki et al. 2025, Mol Cell 10.1016/j.molcel.2025.07.019",
        "truncation_note": (
            "The distributed .xls is truncated at 65,535 rows, the legacy Excel "
            "limit, so 2 of the paper's 29 compounds survive in the ratio table."
        ),
        "fdr": FDR,
        "compounds": {},
    }
    for drug, by_construct in sorted(data["labels"].items()):
        names = list(by_construct)
        features, kept, _columns = featurise(names, data["sequence"])
        labels = np.asarray([by_construct[n] for n in kept])
        genes = [data["gene"].get(n, n) for n in kept]
        if labels.sum() < 30:
            report["compounds"][drug] = {"n_positive": int(labels.sum()),
                                         "skipped": "too few positives"}
            continue
        aucs, sens, spec = nested_evaluate(features, labels, genes)
        report["compounds"][drug] = {
            "n_constructs": int(len(labels)),
            "n_positive": int(labels.sum()),
            "auc_mean": round(float(aucs.mean()), 4),
            "auc_std": round(float(aucs.std()), 4),
            "sensitivity_mean": round(float(sens.mean()), 4),
            "specificity_mean": round(float(spec.mean()), 4),
            "clears_spec_92_floors": bool(sens.mean() >= 0.70 and spec.mean() >= 0.60),
            "validation": ("nested: the threshold is chosen on inner folds and "
                           "measured on outer folds it never saw"),
        }
        log_event("5.2", f"{drug}: nested AUC {aucs.mean():.4f}, sensitivity "
                         f"{sens.mean():.4f}, specificity {spec.mean():.4f} on "
                         f"{int(labels.sum())} positives.")
    (INTERIM / "degron_slabicki_fit.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
