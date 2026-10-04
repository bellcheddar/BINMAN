"""Does the pomalidomide degron model transfer to the other glutarimides?

D-047 recorded a hypothesis: the two compounds whose degradation sequence
predicted well degrade 0.1% and 0.2% of the zinc-finger library, the two it
failed on degrade 2.8% and 4.3%, so predictability might fall as a compound
gets promiscuous. It said plainly that the test needed the other 27 compounds
and that they were "in the paper and not in the distributed file".

They are in the distributed file, in a different one. Supplement 4, the primary
screen, is truncated at the legacy 65,535-row Excel limit and keeps 2 of 29
compounds (D-046). Supplement 5, the validation screen, is a modern `.xlsx`,
is not truncated, and carries all 29 compounds against 57 constructs that the
primary screen had already shown to be degrons.

**The join, which is where this went wrong first.** The ratio table keys on
`Construct.ZnF` ("BCL6_570-627"), which matches the library's `Construct`
column and not its `Construct_Name` ("BCL6_570-627.Validation_AA"). The
variant is in `Category`: WT, Mut1, Mut2, Mut3. Only the WT rows are the
compound's effect on the native degron; the mutant rows are the alanine scan
that `degron_alascan` already uses.

**What breadth means here, stated before the result.** These 57 constructs are
validated degrons, so a compound's hit rate across them is not its hit rate
across the proteome. Pomalidomide degrades 42% of this panel and 0.1% of the
library. The panel measures selectivity *within* known degrons, which is the
right ordering but a compressed range, and that limit belongs on the finding.

**The leakage that nearly made this wrong.** 69 of the panel's 72 anchored
cores also appear in the Sievers training library, so the first run scored
every compound well for the wrong reason. Three regimes are therefore reported,
not one: the naive fit, a gene-disjoint fit that drops every Sievers row from a
panel gene, and a core-disjoint fit that also drops every row sharing an
anchored core. Core-disjointness costs 7 of 12 positives, so it is paired with
a size-matched subsample control that separates the cost of the exclusion from
the cost of the smaller training set.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    INTERIM, MANIFESTS, VALIDATION, load_config, log_event, write_jsonl,
)
from pipeline.degron_alascan import weights_vector  # noqa: E402
from pipeline.degron_predict import WIDTH, encode  # noqa: E402
from pipeline.degron_sequence import C2H2, align, featurise  # noqa: E402
from pipeline.degron_slabicki import benjamini_hochberg  # noqa: E402

PANEL = VALIDATION / "raw" / "NIHMS2104733-supplement-5.xlsx"
SIEVERS = VALIDATION / "raw" / "aat0572_sievers_data-file-s2.xlsx"
REPORT = INTERIM / "degron_panel.json"
MANIFEST = MANIFESTS / "degron_panel.jsonl"
# The WT construct carries this suffix in the library sheet; the replicate and
# mutant rows carry others and are not the native degron.
WT_SUFFIX = ".Validation_AA"


def _limits() -> dict:
    """Panel cuts from config/thresholds.toml, never from a literal here."""
    config = load_config()
    return {
        "fdr": float(config.t("validation.panel_fdr")),
        "min_class": int(config.t("validation.panel_min_class_size")),
        "permutations": int(config.t("validation.panel_permutation_draws")),
        "subsamples": int(config.t("validation.panel_subsample_draws")),
        "seed": int(config.t("validation.panel_seed")),
    }


def load_panel() -> dict[str, str]:
    """Construct name to its 58-residue wild-type amino-acid sequence."""
    import openpyxl

    if not PANEL.exists():
        raise SystemExit(f"{PANEL} does not exist")
    book = openpyxl.load_workbook(PANEL, read_only=True, data_only=True)
    stream = book["ZF.Validation.Cilantro"].iter_rows(values_only=True)
    index = {str(name): i for i, name in enumerate(next(stream))}
    out: dict[str, str] = {}
    for row in stream:
        if not row or row[index["Construct_Name"]] is None:
            continue
        if str(row[index["Construct_Name"]]).endswith(WT_SUFFIX):
            out[str(row[index["Construct"]])] = str(row[index["Construct_AA"]] or "")
    return out


def load_labels(fdr: float) -> dict[str, dict[str, int]]:
    """Compound to construct to degraded, from the validation ratio table.

    Gate A is the EGFP-high population, so a construct depleted there under
    drug is one the drug degraded. The two libraries measure each construct
    twice; the stronger evidence is kept rather than averaging a pair that can
    disagree in sign, matching `degron_slabicki`.
    """
    import numpy as np
    import openpyxl

    book = openpyxl.load_workbook(PANEL, read_only=True, data_only=True)
    stream = book["Screen.Validation_Ratio_pval"].iter_rows(values_only=True)
    index = {str(name): i for i, name in enumerate(next(stream))}
    best: dict[str, dict[str, tuple[float, float]]] = collections.defaultdict(dict)
    for row in stream:
        if not row or row[index["Gene"]] is None:
            continue
        if str(row[index["Gate"]]) != "A" or str(row[index["Category"]]) != "WT":
            continue
        try:
            p = float(row[index["p_value"]])
            lfc = float(row[index["LFC"]])
        except (TypeError, ValueError):
            continue
        drug = str(row[index["Drug"]])
        construct = str(row[index["Construct.ZnF"]])
        previous = best[drug].get(construct)
        if previous is None or p < previous[0]:
            best[drug][construct] = (p, lfc)

    labels: dict[str, dict[str, int]] = {}
    for drug, measured in best.items():
        names = list(measured)
        q = benjamini_hochberg([measured[n][0] for n in names])
        lfc = np.asarray([measured[n][1] for n in names])
        labels[drug] = {name: int(bool(q[i] < fdr and lfc[i] < 0))
                        for i, name in enumerate(names)}
    return labels


def _cores(sequence: str) -> set[str]:
    """Every anchored C2H2 core in a sequence, which is all the model sees."""
    return {core for core in (align(m.group(0), WIDTH)
                              for m in C2H2.finditer(sequence)) if core}


def load_training():
    """Sievers features, pomalidomide labels and the alanine-scan weights."""
    import numpy as np
    import openpyxl

    rows = [r for r in csv.DictReader(
        (VALIDATION / "sievers_zf_screen.tsv").open(encoding="utf-8"),
        delimiter="\t") if r.get("aa_sequence")]
    features, _labels, _genes, columns, kept = featurise(rows)

    book = openpyxl.load_workbook(SIEVERS, read_only=True, data_only=True)
    stream = book["pval_FDR"].iter_rows(values_only=True)
    index = {str(name): i for i, name in enumerate(next(stream))}
    positives = set()
    for row in stream:
        if not row or not row[index["Gene"]]:
            continue
        value = row[index["POM.FDR"]]
        if isinstance(value, (int, float)) and value < 0.05:
            positives.add((str(row[index["Gene"]]), int(row[index["AA.Start"]]),
                           int(row[index["AA.Stop"]])))
    labels = np.asarray([
        1 if (r["gene"], int(r["zf_start"]), int(r["zf_stop"])) in positives else 0
        for r in kept])
    weights = weights_vector(columns, json.loads(
        (INTERIM / "degron_alascan_importance.json").read_text()))
    return features, labels, kept, columns, weights


def _fit_and_score(features, labels, mask, columns, weights, panel):
    """Fit on the masked training rows, score every panel construct."""
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(C=0.05, max_iter=5000, class_weight="balanced",
                               solver="liblinear")
    model.fit(features[mask] * weights, labels[mask])
    scores = {}
    for name, sequence in panel.items():
        cores = _cores(sequence)
        if not cores:
            continue
        # Score every finger and keep the best, as degron_predict does: the
        # construct carries two and either can be the degron.
        scores[name] = max(
            float(model.predict_proba(
                (encode(core, columns) * weights).reshape(1, -1))[0, 1])
            for core in cores)
    return scores


def _per_compound(scores, labels, min_class):
    """Breadth and AUC for each compound, None where the AUC is not estimable."""
    import numpy as np
    from sklearn.metrics import roc_auc_score

    out = []
    for drug in sorted(labels):
        by_construct = labels[drug]
        breadth = 100.0 * float(np.mean(list(by_construct.values())))
        names = [n for n in by_construct if n in scores]
        y = np.asarray([by_construct[n] for n in names])
        s = np.asarray([scores[n] for n in names])
        estimable = min_class <= y.sum() <= len(y) - min_class
        out.append({
            "compound": drug,
            "breadth_pct": round(breadth, 2),
            "n_degraded_of_panel": int(sum(by_construct.values())),
            "n_panel": len(by_construct),
            "n_positive_scored": int(y.sum()),
            "n_scored": int(len(y)),
            "auc": round(float(roc_auc_score(y, s)), 4) if estimable else None,
        })
    return out


def _mean_auc(rows):
    import numpy as np

    values = [r["auc"] for r in rows if r["auc"] is not None]
    return float(np.mean(values)), np.asarray(values)


def run() -> dict:
    import numpy as np
    from scipy.stats import pearsonr, spearmanr

    limits = _limits()
    panel = load_panel()
    labels = load_labels(limits["fdr"])
    features, train_labels, kept, columns, weights = load_training()

    panel_genes = {name.rsplit("_", 1)[0] for name in panel}
    panel_cores: set[str] = set()
    for sequence in panel.values():
        panel_cores |= _cores(sequence)

    gene_ok = np.asarray([r["gene"] not in panel_genes for r in kept])
    core_ok = np.asarray([
        r["gene"] not in panel_genes and not (_cores(r.get("aa_sequence", "")) & panel_cores)
        for r in kept])

    report: dict = {
        "source": ("Slabicki et al. 2025 supplement 5, validation screen, "
                   "10.1016/j.molcel.2025.07.019"),
        "question": ("does the pomalidomide-trained sequence model transfer to the "
                     "other glutarimide analogs, and does breadth predict failure "
                     "(the D-047 hypothesis)"),
        "n_constructs": len(panel),
        "n_constructs_with_c2h2": sum(1 for s in panel.values() if _cores(s)),
        "n_compounds": len(labels),
        "panel_caveat": ("these 57 constructs are validated degrons, so breadth "
                         "here is selectivity within known degrons and not a "
                         "proteome hit rate: pomalidomide degrades 42% of this "
                         "panel and 0.1% of the primary library"),
        "thresholds": limits,
        "regimes": {},
    }

    for tag, mask in (("naive", np.ones(len(kept), dtype=bool)),
                      ("gene_disjoint", gene_ok),
                      ("core_disjoint", core_ok)):
        shared = int(sum(1 for r, keep in zip(kept, mask)
                         if keep and (_cores(r.get("aa_sequence", "")) & panel_cores)))
        entry = {
            "n_training_rows": int(mask.sum()),
            "n_training_positives": int(train_labels[mask].sum()),
            "training_rows_sharing_a_panel_core": shared,
        }
        if train_labels[mask].sum() < limits["min_class"]:
            entry["skipped"] = "too few training positives to fit"
            report["regimes"][tag] = entry
            continue
        scores = _fit_and_score(features, train_labels, mask, columns, weights, panel)
        rows = _per_compound(scores, labels, limits["min_class"])
        mean, values = _mean_auc(rows)
        breadths = np.asarray([r["breadth_pct"] for r in rows if r["auc"] is not None])
        rho, rho_p = spearmanr(breadths, values)
        r, r_p = pearsonr(breadths, values)

        # Permutation null: shuffle which construct carries which score, which
        # destroys the sequence signal while preserving every label and the
        # score distribution.
        rng = np.random.default_rng(limits["seed"])
        names = list(scores)
        vector = np.asarray([scores[n] for n in names])
        null = []
        for _ in range(limits["permutations"]):
            shuffled = dict(zip(names, rng.permutation(vector)))
            null.append(_mean_auc(_per_compound(
                shuffled, labels, limits["min_class"]))[0])
        null = np.asarray(null)

        entry.update({
            "n_compounds_estimable": int(len(values)),
            "auc_mean": round(mean, 4),
            "auc_median": round(float(np.median(values)), 4),
            "auc_min": round(float(values.min()), 4),
            "auc_max": round(float(values.max()), 4),
            "n_compounds_above_chance": int((values > 0.5).sum()),
            "breadth_vs_auc_spearman": round(float(rho), 4),
            "breadth_vs_auc_spearman_p": round(float(rho_p), 4),
            "breadth_vs_auc_pearson": round(float(r), 4),
            "breadth_vs_auc_pearson_p": round(float(r_p), 4),
            "permutation_null_mean": round(float(null.mean()), 4),
            "permutation_null_p95": round(float(np.percentile(null, 95)), 4),
            "permutation_p": round(
                (1 + int((null >= mean).sum())) / (1 + len(null)), 5),
            "per_compound": rows,
        })
        report["regimes"][tag] = entry

    # Size-matched control. Core-disjointness removes training positives as well
    # as shared cores, so a drop in AUC has two possible causes. Fitting repeated
    # random subsamples of the gene-disjoint positives at the core-disjoint
    # positive count, with shared cores still allowed, isolates the size cost.
    core = report["regimes"].get("core_disjoint", {})
    target = core.get("n_training_positives")
    if target and core.get("auc_mean") is not None:
        positives = np.flatnonzero(gene_ok & (train_labels == 1))
        negatives = np.flatnonzero(gene_ok & (train_labels == 0))
        rng = np.random.default_rng(limits["seed"])
        draws = []
        for _ in range(limits["subsamples"]):
            mask = np.zeros(len(kept), dtype=bool)
            mask[negatives] = True
            mask[rng.choice(positives, size=target, replace=False)] = True
            draws.append(_mean_auc(_per_compound(
                _fit_and_score(features, train_labels, mask, columns, weights, panel),
                labels, limits["min_class"]))[0])
        draws = np.asarray(draws)
        report["size_matched_control"] = {
            "what": (f"{limits['subsamples']} gene-disjoint fits subsampled to "
                     f"{target} positives, shared cores still allowed"),
            "auc_mean": round(float(draws.mean()), 4),
            "auc_p5": round(float(np.percentile(draws, 5)), 4),
            "auc_p95": round(float(np.percentile(draws, 95)), 4),
            "core_disjoint_auc_mean": core["auc_mean"],
            "core_disjoint_percentile_of_control": round(
                100.0 * float((draws <= core["auc_mean"]).mean()), 1),
        }

    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    rows = [{"compound": r["compound"], "regime": tag,
             "breadth_pct": r["breadth_pct"], "auc": r["auc"]}
            for tag, entry in report["regimes"].items()
            for r in entry.get("per_compound", [])]
    write_jsonl(MANIFEST, rows)
    gene = report["regimes"].get("gene_disjoint", {})
    if gene.get("auc_mean") is not None:
        log_event("9.2", (
            f"Glutarimide panel: the pomalidomide model transfers to "
            f"{gene['n_compounds_above_chance']} of {gene['n_compounds_estimable']} "
            f"compounds gene-disjoint, mean AUC {gene['auc_mean']}, permutation "
            f"p={gene['permutation_p']}. Breadth against AUC Spearman "
            f"{gene['breadth_vs_auc_spearman']} (p={gene['breadth_vs_auc_spearman_p']})."))
    return report


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    report = run()
    print(json.dumps({k: v for k, v in report.items() if k != "regimes"}, indent=2))
    for tag, entry in report["regimes"].items():
        print(f"\n== {tag}")
        print(json.dumps({k: v for k, v in entry.items() if k != "per_compound"},
                         indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
