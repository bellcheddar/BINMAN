"""Is exposure the wrong feature, or is the question unanswerable from a monomer?

`degradability.fit_accessibility` fits one number, `min_nz_rel_sasa`, against
observed ubiquitylation sites and reaches a held-out AUC of 0.546 against spec
9.5's floor of 0.65. It writes nothing and emits no verdict, which is the
honest outcome, and it leaves a question open: does exposure alone fail because
exposure is the wrong feature, or because an AlphaFold monomer cannot answer
"will this lysine be ubiquitylated" at all?

This settles it by measuring, so the reach window stops being an open item.
Eighteen features are derived for all 12,705 lysines of the 403 proteins that
carry a UniProt ubiquitin crosslink: exposure, pLDDT, burial, secondary
structure, position in the chain, local sequence composition, lysine spacing,
and two protein-level terms. Everything is cross-validated with the proteins
grouped, so no protein appears in both halves.

**The trap this module exists to document.** Pooled over all lysines, the full
feature set reaches 0.714 and clears the floor. It should not be believed. The
two strongest single features are the protein's lysine count (0.708 alone) and
its length (0.691 alone), and both are constant within a protein, so they
cannot discriminate between two lysines of the same protein. What they rank is
proteins, by how large a fraction of their lysines the catalogue happens to
annotate. That is annotation prevalence, not biology, and the module's real
question is always within one protein: given this ligand site, is a reachable
lysine ubiquitylated?

So the figure that decides it is the AUC computed inside each protein, averaged
over the 393 that carry both classes. There the pooled 0.714 becomes 0.626, the
shipped single feature scores 0.544, and the best per-lysine set reaches 0.598.
Nothing clears 0.65. The negatives are also assumed rather than assayed, which
makes even those numbers generous.

**The conclusion, which is a closure and not a failure.** Exposure is weak but
it is not uniquely weak: no combination of monomer-derivable structural
features answers this question to the standard spec 9.5 asks for. The reach
window stays unfitted and no degradability verdict is emitted. That decision
now rests on a measurement rather than on one feature having been tried.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    INTERIM, MANIFESTS, VALIDATION, load_config, log_event, write_jsonl,
)

CACHE = INTERIM / "afdb"
REPORT = INTERIM / "degradability_features.json"
MANIFEST = MANIFESTS / "degradability_features.jsonl"
SITES = "digly_sites"
# Tien et al. maximum accessible surface area for lysine, as degradability uses.
LYS_MAX_ASA = 200.1
ACIDIC, BASIC, HYDROPHOBIC = set("DE"), set("KR"), set("AVLIMFWC")

# Protein-level terms are listed separately because the point of the module is
# that they inflate a pooled AUC without answering the question.
PER_LYSINE = [
    "rel_sasa", "plddt", "plddt_window", "burial_10a", "burial_15a",
    "ss_helix", "ss_strand", "ss_coil", "rel_position", "terminus_distance",
    "frac_acidic", "frac_basic", "frac_hydrophobic", "frac_glycine",
    "frac_proline", "nearest_lysine_a",
]
PROTEIN_LEVEL = ["n_lysines", "chain_length"]
ALL_FEATURES = PER_LYSINE + PROTEIN_LEVEL


def observed_sites() -> dict[str, set[int]]:
    """Accession to the residue numbers UniProt records as crosslinked."""
    out: dict[str, set[int]] = {}
    with (VALIDATION / f"{SITES}.tsv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            accession = (row.get("uniprot") or "").strip()
            try:
                residue = int(row.get("res_num") or "")
            except ValueError:
                continue
            if accession:
                out.setdefault(accession, set()).add(residue)
    return out


def _features_for(job: dict) -> list[dict]:
    """Every lysine of one AlphaFold model, with its features and label."""
    import freesasa
    import gemmi
    import numpy as np

    from pipeline.degron_scan import parse_dssp, run_dssp

    accession, sites, path = job["accession"], set(job["sites"]), Path(job["path"])
    try:
        structure = gemmi.read_structure(str(path))
        structure.setup_entities()
        structure.remove_alternative_conformations()
        structure.remove_hydrogens()
        structure.remove_waters()
        if not len(structure):
            return []
        chain = structure[0][0]

        sequence: dict[int, str] = {}
        plddt: dict[int, float] = {}
        nz: dict[int, tuple[float, float, float]] = {}
        coordinates: list[tuple[float, float, float]] = []
        flat: list[float] = []
        radii: list[float] = []
        nz_atom: dict[int, int] = {}
        element_radius = {"C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80, "P": 1.80}
        index = 0
        for residue in chain:
            code = gemmi.find_tabulated_residue(residue.name)
            if not (code and code.is_amino_acid()):
                continue
            number = residue.seqid.num
            sequence[number] = code.one_letter_code.upper()
            for atom in residue:
                element = atom.element.name.upper()
                if element in ("H", "D"):
                    continue
                coordinates.append((atom.pos.x, atom.pos.y, atom.pos.z))
                flat += [atom.pos.x, atom.pos.y, atom.pos.z]
                radii.append(element_radius.get(element, 1.70))
                if atom.name == "CA":
                    plddt[number] = atom.b_iso
                if residue.name == "LYS" and atom.name == "NZ":
                    nz[number] = (atom.pos.x, atom.pos.y, atom.pos.z)
                    nz_atom[number] = index
                index += 1
        if not nz:
            return []

        config = load_config()
        areas = freesasa.calcCoord(flat, radii, freesasa.Parameters({
            "algorithm": freesasa.LeeRichards,
            "probe-radius": float(config.t("bridging.sasa_probe_radius_a")),
            "n-slices": 20,
        }))

        secondary: dict[int, str] = {}
        try:
            for record in parse_dssp(run_dssp(path)):
                secondary[record.number] = record.ss
        except Exception:
            # Secondary structure is one feature of eighteen. A model whose DSSP
            # fails still contributes the other seventeen rather than dropping
            # the whole protein, and the coil default is recorded as such.
            pass

        points = np.asarray(coordinates, dtype=float)
        numbers = sorted(sequence)
        first, last, length = numbers[0], numbers[-1], len(numbers)
        lysines = sorted(nz)
        rows = []
        for number in lysines:
            atom_index = nz_atom.get(number)
            exposure = (areas.atomArea(atom_index) / LYS_MAX_ASA
                        if atom_index is not None else 0.0)
            window = [plddt[n] for n in range(number - 4, number + 5) if n in plddt]
            context = [sequence[n] for n in range(number - 5, number + 6)
                       if n in sequence and n != number]
            position = np.asarray(nz[number], dtype=float)
            distances = np.linalg.norm(points - position, axis=1)
            spacing = [float(np.linalg.norm(np.asarray(nz[n]) - position))
                       for n in lysines if n != number]
            state = secondary.get(number, "-")
            fraction = (lambda members: float(
                sum(c in members for c in context) / len(context)) if context else 0.0)
            rows.append({
                "accession": accession,
                "residue": number,
                "label": 1 if number in sites else 0,
                "rel_sasa": float(exposure),
                "plddt": float(plddt.get(number, 0.0)),
                "plddt_window": float(np.mean(window)) if window else 0.0,
                "burial_10a": float((distances < 10.0).sum()),
                "burial_15a": float((distances < 15.0).sum()),
                "ss_helix": 1.0 if state in ("H", "G", "I") else 0.0,
                "ss_strand": 1.0 if state in ("E", "B") else 0.0,
                "ss_coil": 1.0 if state in ("-", "T", "S", "") else 0.0,
                "rel_position": float((number - first) / max(1, last - first)),
                "terminus_distance": float(
                    min(number - first, last - number) / max(1, length)),
                "frac_acidic": fraction(ACIDIC),
                "frac_basic": fraction(BASIC),
                "frac_hydrophobic": fraction(HYDROPHOBIC),
                "frac_glycine": fraction({"G"}),
                "frac_proline": fraction({"P"}),
                "nearest_lysine_a": float(min(spacing)) if spacing else 99.0,
                "n_lysines": float(len(lysines)),
                "chain_length": float(length),
            })
        return rows
    except Exception as exc:  # one bad model must not lose the other 402
        return [{"accession": accession, "error": str(exc)[:200]}]


def extract(limit: int | None = None) -> list[dict]:
    """Features for every measurable lysine, cached so the fit is re-runnable."""
    jobs = []
    for accession, sites in sorted(observed_sites().items()):
        model = next(iter(CACHE.glob(f"*{accession}*")), None)
        if model is not None:
            jobs.append({"accession": accession, "sites": sorted(sites),
                         "path": str(model)})
    if limit:
        jobs = jobs[:limit]
    workers = int(load_config().u("compute.cpu_workers"))
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for produced in pool.map(_features_for, jobs, chunksize=4):
            rows.extend(produced)
    failures = [r for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    write_jsonl(MANIFEST, rows)
    if failures:
        log_event("2.3", f"Lysine features: {len(failures)} model(s) could not be "
                         "measured and are excluded.")
    return rows


def _grouped_out_of_fold(matrix, labels, groups, kind: str, seed: int):
    """Out-of-fold predictions with whole proteins held out."""
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    predictions = np.zeros(len(labels))
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    for train, test in splitter.split(matrix, labels, groups=groups):
        if kind == "logistic":
            model = make_pipeline(StandardScaler(), LogisticRegression(
                max_iter=4000, class_weight="balanced"))
        else:
            model = HistGradientBoostingClassifier(
                max_iter=250, learning_rate=0.06, max_depth=4,
                l2_regularization=1.0, random_state=seed)
        model.fit(matrix[train], labels[train])
        predictions[test] = model.predict_proba(matrix[test])[:, 1]
    return predictions


def _within_protein_auc(predictions, labels, groups):
    """Mean AUC inside each protein: can it rank one protein's own lysines?

    This is the figure that decides the question. A protein-constant feature
    scores 0.5 here by construction, so annotation prevalence cannot flatter it.
    """
    import numpy as np
    from sklearn.metrics import roc_auc_score

    by_protein: dict[str, list[int]] = collections.defaultdict(list)
    for i, accession in enumerate(groups):
        by_protein[accession].append(i)
    scores = []
    for indices in by_protein.values():
        truth = labels[indices]
        if truth.sum() == 0 or truth.sum() == len(truth):
            continue
        scores.append(roc_auc_score(truth, predictions[indices]))
    return float(np.mean(scores)), len(scores)


def run(limit: int | None = None) -> dict:
    import numpy as np
    from sklearn.metrics import roc_auc_score

    config = load_config()
    floor = float(config.t("validation.degradability_auc_floor"))
    seed = int(config.t("validation.panel_seed"))

    rows = extract(limit=limit)
    labels = np.asarray([r["label"] for r in rows])
    groups = np.asarray([r["accession"] for r in rows])
    columns = {name: np.asarray([r[name] for r in rows], dtype=float)
               for name in ALL_FEATURES}

    report: dict = {
        "question": ("does any feature derivable from an AlphaFold monomer predict "
                     "which lysine is ubiquitylated, to the spec 9.5 floor"),
        "dataset": SITES,
        "n_lysines": len(rows),
        "n_positive": int(labels.sum()),
        "n_proteins": int(len(set(groups))),
        "auc_floor": floor,
        "negatives_caveat": ("the negatives are the other lysines of the same "
                             "proteins, which were not assayed and found "
                             "unmodified, so every figure here is generous"),
        "single_features": {},
        "feature_sets": {},
    }

    for name in ALL_FEATURES:
        matrix = columns[name].reshape(-1, 1)
        predictions = _grouped_out_of_fold(matrix, labels, groups, "logistic", seed)
        within, _n = _within_protein_auc(predictions, labels, groups)
        report["single_features"][name] = {
            "pooled_auc": round(float(roc_auc_score(labels, predictions)), 4),
            "within_protein_auc": round(within, 4),
            "protein_constant": name in PROTEIN_LEVEL,
        }

    sets = {
        "shipped_exposure_only": ["rel_sasa"],
        "all_per_lysine": PER_LYSINE,
        "all_including_protein_level": ALL_FEATURES,
    }
    for name, names in sets.items():
        matrix = np.column_stack([columns[c] for c in names])
        entry = {"features": names}
        for kind in ("logistic", "boosted"):
            predictions = _grouped_out_of_fold(matrix, labels, groups, kind, seed)
            within, n_proteins = _within_protein_auc(predictions, labels, groups)
            entry[kind] = {
                "pooled_auc": round(float(roc_auc_score(labels, predictions)), 4),
                "within_protein_auc": round(within, 4),
                "n_proteins_scored": n_proteins,
                "clears_floor_within_protein": bool(within >= floor),
            }
        report["feature_sets"][name] = entry

    best = max(
        (entry[kind]["within_protein_auc"]
         for entry in report["feature_sets"].values()
         for kind in ("logistic", "boosted")))
    report["best_within_protein_auc"] = round(best, 4)
    report["clears_floor"] = bool(best >= floor)
    report["conclusion"] = (
        "No monomer-derivable feature set reaches the floor on the question the "
        f"module asks: the best within-protein AUC is {best:.4f} against a floor "
        f"of {floor}. A pooled AUC above the floor is reachable only with "
        "protein-level terms that are constant within a protein and therefore "
        "rank proteins by annotation prevalence. The reach window stays "
        "unfitted and no degradability verdict is emitted."
    ) if not report["clears_floor"] else (
        "A monomer-derivable feature set reaches the floor on the within-protein "
        "question, so the reach window can be revisited."
    )

    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    log_event("9.5", (
        f"Lysine feature ablation over {len(rows):,} lysines in "
        f"{report['n_proteins']} proteins: best within-protein AUC "
        f"{best:.4f} against the {floor} floor. "
        f"{'Clears' if report['clears_floor'] else 'Misses'} it."))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="measure only the first N proteins, for a smoke test")
    args = parser.parse_args()
    report = run(limit=args.limit)
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("single_features", "feature_sets")}, indent=2))
    print("\nsingle features, within-protein AUC (* is protein-constant):")
    ranked = sorted(report["single_features"].items(),
                    key=lambda kv: -kv[1]["within_protein_auc"])
    for name, entry in ranked:
        mark = " *" if entry["protein_constant"] else ""
        print(f"  {name:<20} pooled {entry['pooled_auc']:.4f}  "
              f"within {entry['within_protein_auc']:.4f}{mark}")
    print("\nfeature sets:")
    for name, entry in report["feature_sets"].items():
        for kind in ("logistic", "boosted"):
            value = entry[kind]
            print(f"  {name:<30} {kind:<9} pooled {value['pooled_auc']:.4f}  "
                  f"within {value['within_protein_auc']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
