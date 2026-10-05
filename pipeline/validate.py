"""Section 9 validation against published datasets.

Writes `data/validation/results.json` and the corresponding `FINDINGS.md`
sections. Runs at the end of Phases 1, 2 and 3 and again in Phase 4 against the
**shipped atlas**, so a regression between the pipeline and the serving bundle
cannot hide.

The central rule: a metric whose dataset is unavailable is reported as
`computed: false` with the reason. It is never estimated, and no hand-written
control is ever substituted for a missing published one (spec 4.1b, 9.6).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import math
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    ATLAS, INTERIM, VALIDATION, Manifest, load_config, log_event, utcnow,
)

RESULTS = VALIDATION / "results.json"
STAGE = "validate"
DEFAULT_DB = ATLAS / "binman.sqlite"


def _json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def not_computed(reason: str, floor=None) -> dict:
    return {"computed": False, "reason": reason, "floor": floor, "value": None}


def computed(value, floor=None, **extra) -> dict:
    out = {"computed": True, "value": value, "floor": floor, "reason": ""}
    if floor is not None:
        try:
            out["passes"] = bool(value >= floor)
        except TypeError:
            out["passes"] = None
    out.update(extra)
    return out


def dataset_resolved(name: str) -> bool:
    path = VALIDATION / f"{name}.tsv"
    return path.exists() and path.stat().st_size > 0


def _read_tsv(name: str) -> list[dict]:
    path = VALIDATION / f"{name}.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


# --------------------------------------------------------------------------- #
# 9.1 Glue Atlas
# --------------------------------------------------------------------------- #

def section_91(connection: sqlite3.Connection, config) -> dict:
    floors = config.thresholds["validation"]
    out: dict = {"title": "Glue Atlas"}

    curated = [n for n in ("mgdb_glues", "molgluedb_glues", "mgtbind_ternary")
               if dataset_resolved(n)]

    # Artefact precision is reported FIRST, per spec 9.1: a tool that finds every
    # known glue and also calls PEG a glue is useless; the reverse is merely
    # incomplete.
    if not dataset_resolved("biolip2_artefacts"):
        out["artefact_precision"] = not_computed(
            "BioLiP2 artefact ligand list unavailable",
            floors["glue_artefact_precision_floor"])
    else:
        artefacts = {r["ccd_id"].upper() for r in _read_tsv("biolip2_artefacts")}
        rows = connection.execute(
            "SELECT ccd_id, ccd_class FROM ligand WHERE ccd_id IN "
            f"({','.join('?' for _ in artefacts)})", tuple(sorted(artefacts))
        ).fetchall() if artefacts else []
        seen = {r[0].upper(): r[1] for r in rows}
        total = len(seen)
        if total == 0:
            out["artefact_precision"] = not_computed(
                "no BioLiP artefact CCD appears in the atlas yet",
                floors["glue_artefact_precision_floor"])
        else:
            not_glue = sum(1 for cls in seen.values() if cls != "glue_candidate")
            out["artefact_precision"] = computed(
                round(not_glue / total, 4), floors["glue_artefact_precision_floor"],
                n=total, not_called_glue=not_glue,
                note=("Measured over the artefact CCDs present in the atlas. The "
                      "held-out-split figure in FINDINGS.md (0.927) is the one to "
                      "quote: it was measured on a half of the list that the "
                      "classification rules were not developed against."),
            )

    if not curated:
        out["recall"] = not_computed(
            "No curated glue database resolved (MGDB, MolGlueDB and MGTbind all "
            "publish through JavaScript front ends with no documented bulk export; "
            "Gate G7). Spec 4.1b forbids substituting a hand-written positive set, "
            "so recall is not computed.",
            floors["glue_recall_floor"])
        out["three_way_agreement"] = not_computed("no curated glue database resolved")
        out["misses"] = not_computed(
            "The misses list is the complement of recall and needs the same curated "
            "positives.")
    else:
        curated_entries: set[str] = set()
        for name in curated:
            for row in _read_tsv(name):
                for key, value in row.items():
                    if "pdb" in (key or "").lower() and value:
                        for token in str(value).replace(";", ",").split(","):
                            token = token.strip().upper()
                            if len(token) == 4 and token[0].isdigit():
                                curated_entries.add(token)
        found = {r[0] for r in connection.execute(
            "SELECT DISTINCT pdb_id FROM bridge WHERE status = 'ok' "
            "AND ccd_class = 'glue_candidate'")}
        recovered = curated_entries & found
        out["recall"] = computed(
            round(len(recovered) / max(1, len(curated_entries)), 4),
            floors["glue_recall_floor"],
            n=len(curated_entries), recovered=len(recovered))
        out["misses"] = computed(
            sorted(curated_entries - found)[:200],
            note="Each is a sensitivity bug. Enumerated with its reason in FINDINGS.md.")

    if not dataset_resolved("protcid_interfaces"):
        out["packing_specificity"] = not_computed(
            "ProtCID interface classification unavailable (Gate G7)",
            floors["glue_packing_specificity_floor"])
    else:
        out["packing_specificity"] = not_computed("ProtCID parser not wired up")

    # The novel-bridge set is the headline product, and it is only determinable
    # against the curated databases.
    total_bridges = connection.execute(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok'").fetchone()[0]
    glue_bridges = connection.execute(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND ccd_class = 'glue_candidate'"
    ).fetchone()[0]
    novel = connection.execute(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND novel_bridge = 1"
    ).fetchone()[0]
    out["counts"] = {
        "bridges": total_bridges, "glue_candidate_bridges": glue_bridges,
        "entries_with_a_bridge": connection.execute(
            "SELECT COUNT(DISTINCT pdb_id) FROM bridge WHERE status = 'ok'").fetchone()[0],
        "symmetry_mediated": connection.execute(
            "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND symmetry_mediated = 1"
        ).fetchone()[0],
    }
    if curated:
        out["novel_bridges"] = computed(novel, note="The headline result.")
    else:
        out["novel_bridges"] = not_computed(
            "A novel bridge is one in NONE of the three curated glue databases, so "
            "the set is undeterminable while none has resolved. The column reads 0 "
            "in the atlas and must not be read as a real zero.")

    out["ccd_class_counts"] = {
        row[0]: row[1] for row in connection.execute(
            "SELECT ccd_class, COUNT(*) FROM ligand GROUP BY ccd_class "
            "ORDER BY COUNT(*) DESC")
    }
    return out


def roc_auc(scores: list[tuple[float, int]]) -> float:
    """AUC as the rank-based Mann-Whitney statistic, ties shared.

    Spelled out rather than imported so the number in FINDINGS.md is auditable
    against the contingency table beside it.
    """
    positives = [s for s, label in scores if label == 1]
    negatives = [s for s, label in scores if label == 0]
    if not positives or not negatives:
        return float("nan")
    ordered = sorted(scores, key=lambda pair: pair[0])
    ranks: dict[int, float] = {}
    index = 0
    while index < len(ordered):
        stop = index
        while stop + 1 < len(ordered) and ordered[stop + 1][0] == ordered[index][0]:
            stop += 1
        shared = (index + stop) / 2.0 + 1.0
        for position in range(index, stop + 1):
            ranks[position] = shared
        index = stop + 1
    rank_sum = sum(ranks[position] for position, (_, label) in enumerate(ordered)
                   if label == 1)
    n_pos, n_neg = len(positives), len(negatives)
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def degron_threshold_sweep(scores: list[tuple[float, int]],
                           sensitivity_floor: float,
                           specificity_floor: float) -> dict:
    """Sweep `degron_geometry_score` and report whether ANY cut satisfies both
    spec 9.2 floors at once.

    This exists so the G6 case rests on evidence rather than on one failed
    operating point. If no cut on the existing score clears both floors, the
    threshold is not what is wrong with the module and a second adjustment
    would be tuning against the test set for nothing.
    """
    n_pos = sum(1 for _, label in scores if label == 1)
    n_neg = len(scores) - n_pos
    if not n_pos or not n_neg:
        return {}

    points = []
    best = None
    for cut in sorted({score for score, _ in scores} | {0.0}):
        # "called" means the best overlapping candidate scores at or above the
        # cut; a zinc finger with no overlapping candidate scores zero.
        tp = sum(1 for score, label in scores if label == 1 and score >= cut and score > 0)
        fp = sum(1 for score, label in scores if label == 0 and score >= cut and score > 0)
        sensitivity = tp / n_pos
        specificity = (n_neg - fp) / n_neg
        points.append({"cut": round(cut, 4),
                       "sensitivity": round(sensitivity, 4),
                       "specificity": round(specificity, 4)})
        if sensitivity >= sensitivity_floor and specificity >= specificity_floor:
            if best is None or sensitivity + specificity > best["sensitivity"] + best["specificity"]:
                best = points[-1]
    # Youden's J, as the best the score can do regardless of the floors.
    youden = max(points, key=lambda row: row["sensitivity"] + row["specificity"] - 1.0)
    return {
        "any_cut_passes_both_floors": best is not None,
        "passing_cut": best,
        "best_youden_j": {**youden,
                          "j": round(youden["sensitivity"] + youden["specificity"] - 1.0, 4)},
        "curve": points[:: max(1, len(points) // 24)],
    }


def sievers_matched_sets(connection: sqlite3.Connection, config) -> dict | None:
    """Score each assayed zinc finger by the degron scan and build the
    contingency table spec 9.2 asks for.

    A zinc finger counts as *called* when a degron candidate on its AlphaFold
    model shares at least `validation.degron_overlap_residues` residues with the
    assayed window. Its score is the best `degron_geometry_score` among the
    overlapping candidates, and zero when the protein was scanned and nothing
    overlapped, which is what makes a matched negative measurable at all.

    A zinc finger whose protein never reached the scan (no AlphaFold model, or
    outside the reviewed human proteome the scan covers) is excluded and
    counted, because a miss there is missing data rather than a false negative.
    """
    assayed = _read_tsv("sievers_zf_screen")
    if not assayed:
        return None

    overlap_floor = int(config.thresholds["validation"]["degron_overlap_residues"])

    scanned: set[str] = set()
    for record in Manifest("degrons").read():
        if record.get("status") == "ok" and record.get("key"):
            scanned.add(record["key"])

    candidates: dict[str, list[tuple[int, int, float]]] = {}
    for accession, start, end, score in connection.execute(
            "SELECT uniprot_acc, start_res, end_res, degron_geometry_score "
            "FROM degron WHERE status = 'ok'"):
        candidates.setdefault(accession, []).append(
            (int(start), int(end), float(score or 0.0)))

    scores: list[tuple[float, int]] = []
    table = {"tp": 0, "fn": 0, "fp": 0, "tn": 0}
    excluded = {"not_scanned": 0, "no_accession": 0}
    recovered: list[dict] = []
    missed: list[dict] = []

    for row in assayed:
        accession = (row.get("uniprot") or "").strip()
        if not accession:
            excluded["no_accession"] += 1
            continue
        if accession not in scanned:
            excluded["not_scanned"] += 1
            continue
        try:
            start = int(row["zf_start"])
            stop = int(row["zf_stop"])
        except (KeyError, TypeError, ValueError):
            excluded["no_accession"] += 1
            continue

        best = 0.0
        called = False
        for low, high, score in candidates.get(accession, ()):
            shared = min(stop, high) - max(start, low) + 1
            if shared >= overlap_floor:
                called = True
                best = max(best, score)

        degraded = row.get("degraded") == "1"
        scores.append((best, 1 if degraded else 0))
        if degraded and called:
            table["tp"] += 1
            recovered.append({"gene": row.get("gene", ""), "uniprot": accession,
                              "window": f"{start}-{stop}", "score": round(best, 4),
                              "drugs": row.get("drugs_significant", "")})
        elif degraded:
            table["fn"] += 1
            missed.append({"gene": row.get("gene", ""), "uniprot": accession,
                           "window": f"{start}-{stop}",
                           "candidates_on_protein": len(candidates.get(accession, ())),
                           "drugs": row.get("drugs_significant", "")})
        elif called:
            table["fp"] += 1
        else:
            table["tn"] += 1

    degraded_total = table["tp"] + table["fn"]
    matched_total = table["tn"] + table["fp"]
    if not degraded_total or not matched_total:
        return None

    return {
        "table": table,
        "sensitivity": table["tp"] / degraded_total,
        "specificity": table["tn"] / matched_total,
        "degraded_total": degraded_total,
        "matched_total": matched_total,
        "excluded": excluded,
        "auc": roc_auc(scores),
        "recovered": recovered,
        "missed": missed,
        "scores": scores,
    }


# --------------------------------------------------------------------------- #
# 9.2 Degron Scan
# --------------------------------------------------------------------------- #

def section_92(connection: sqlite3.Connection, config) -> dict:
    floors = config.thresholds["validation"]
    out: dict = {"title": "Degron Scan"}
    reason = (
        "No matched degraded and non-degraded zinc-finger sets resolved (Gate "
        "G7). Specificity is the metric that matters here and there is no "
        "matched negative set to measure it against, so the module is presented "
        "as a hypothesis generator rather than a classifier, which is what spec "
        "9.2 instructs for exactly this case."
    )
    matched = sievers_matched_sets(connection, config)
    if matched is None:
        out["sensitivity"] = not_computed(reason, floors["degron_sensitivity_floor"])
        out["specificity"] = not_computed(reason, floors["degron_specificity_floor"])
        out["contingency_table"] = not_computed(reason)
        out["roc_auc"] = not_computed(reason)
    else:
        source = (
            "Sievers et al. 2018 (10.1126/science.aat0572), supplementary data "
            "files S2 and S6 pooled: "
            f"{matched['degraded_total']} zinc fingers depleted under IMiD "
            f"treatment at FDR < {config.thresholds['validation']['sievers_fdr']} "
            f"against {matched['matched_total']} assayed in the same screens and "
            "not depleted. Spec 9.2 names the Molecular Cell 2025 and Nature "
            "Communications 2025 screens; neither resolved, and this is the same "
            "experimental design (one flow-cytometry screen supplying both arms) "
            "from a source that did."
        )
        out["sensitivity"] = computed(
            round(matched["sensitivity"], 4),
            floors["degron_sensitivity_floor"],
            source=source,
            n=matched["degraded_total"],
        )
        out["specificity"] = computed(
            round(matched["specificity"], 4),
            floors["degron_specificity_floor"],
            source=source,
            n=matched["matched_total"],
        )
        out["contingency_table"] = {
            "computed": True, "reason": "", "value": matched["table"],
            "note": (
                "Rows are the screen, columns the geometric filter. A zinc finger "
                "is 'called' when a degron candidate on its AlphaFold model shares "
                "at least "
                f"{config.thresholds['validation']['degron_overlap_residues']} "
                "residue(s) with the assayed window. "
                f"{matched['excluded']['not_scanned']:,} assayed zinc fingers were "
                "excluded because their protein never reached the scan (no "
                "AlphaFold model, or outside the reviewed human proteome) and "
                f"{matched['excluded']['no_accession']:,} for want of a usable "
                "accession or window; a miss there is missing data, not a false "
                "negative, so neither is scored."
            ),
        }
        out["roc_auc"] = {
            "computed": True, "reason": "", "floor": None,
            "value": None if matched["auc"] != matched["auc"] else round(matched["auc"], 4),
            "note": (
                "Over degron_geometry_score, taking the best overlapping candidate "
                "per zinc finger and zero where the protein was scanned and nothing "
                "overlapped. The score is therefore heavily tied at zero, which "
                "caps the AUC achievable by ranking alone: read it with the "
                "contingency table, not instead of it."
            ),
        }
        sweep = degron_threshold_sweep(
            matched["scores"],
            float(floors["degron_sensitivity_floor"]),
            float(floors["degron_specificity_floor"]),
        )
        out["threshold_sweep"] = {
            "computed": True, "reason": "", "floor": None, "value": sweep,
            "note": (
                "Spec 9.6 allows one documented threshold adjustment before G6, "
                "and D-010 already spent it on five documented degrons, with no "
                "matched negative set in existence at the time. This sweep asks "
                "whether a second adjustment could even help: if no cut on "
                "degron_geometry_score clears both floors together, the cut is not "
                "what is wrong and moving it would be tuning against the test set."
            ),
        }
        fit = _json_file(INTERIM / "degron_sequence_fit.json")
        if fit:
            points = fit.get("operating_points") or {}
            null = fit.get("permutation_null") or {}
            out["sequence_model_auc"] = {
                "computed": True, "reason": "", "floor": None,
                "value": fit.get("auc_mean"),
                "note": (
                    "Spec 9.2's reversal condition, tested: a feature that "
                    "discriminates WITHIN the C2H2 family. Zinc fingers anchored "
                    "on their C2H2 motif, residues encoded as chemical groups "
                    "per aligned position, L2 logistic regression evaluated by "
                    "repeated stratified group k-fold so no gene spans a split. "
                    f"Held-out AUC {fit.get('auc_mean')} (sd {fit.get('auc_std')}) "
                    f"against the geometry's {fit.get('geometry_auc_for_comparison')} "
                    f"and a permutation null of {null.get('null_mean')} "
                    f"(sd {null.get('null_std')}, p95 {null.get('null_p95')}). "
                    "Real, and marginal: it clears the null's 95th percentile by "
                    f"{fit.get('beats_null_by_sd')} standard deviations on 32 "
                    "positives."
                ),
            }
            out["sequence_model_operating_points"] = {
                "computed": True, "reason": "", "floor": None,
                "value": points,
                "note": (
                    "Swept on out-of-fold predictions, where every domain is "
                    "scored by a model that never saw its gene. **No cut "
                    "satisfies both spec 9.2 floors**: the best Youden's J is "
                    f"{(points.get('best_youden') or {}).get('youden_j')} at "
                    f"sensitivity {(points.get('best_youden') or {}).get('sensitivity')} "
                    f"and specificity {(points.get('best_youden') or {}).get('specificity')}. "
                    "Better discrimination than the geometry by a wide margin, "
                    "and still not a classifier."
                ),
            }
        out["recovered_zinc_fingers"] = {
            "computed": True, "reason": "", "floor": None,
            "value": sorted(matched["recovered"],
                            key=lambda row: -row["score"]),
        }
        out["missed_zinc_fingers"] = {
            "computed": True, "reason": "", "floor": None,
            "value": matched["missed"],
            "note": ("candidates_on_protein is how many degron candidates the scan "
                     "found anywhere on that protein: a non-zero count with no "
                     "overlap means the filter fired, but elsewhere."),
        }

    window = config.thresholds["degron"]
    out["calibration"] = {
        "computed": True,
        "value": {
            "min_strand_length": window["min_strand_length"],
            "max_turn_length": window["max_turn_length"],
            "min_tip_rel_sasa": window["min_tip_rel_sasa"],
            "min_mean_plddt": window["min_mean_plddt"],
            "tip_region_half_width": window["tip_region_half_width"],
            "calibration_date": window.get("calibration_date"),
            "calibration_basis": window.get("calibration_basis"),
            "calibration_validated": window.get("calibration_validated"),
        },
        "reason": "",
        "note": ("Calibrated to the measured geometry of five documented CRBN and "
                 "DCAF degrons, as the single adjustment spec 9.6 permits "
                 "(DECISIONS D-010). Not independently validated: see the reason "
                 "above."),
    }
    out["documented_degron_recovery"] = {
        "computed": True, "reason": "",
        "value": {"recovered": 3, "of": 5,
                  "found": ["IKZF1 Gly151", "SALL4 Gly416", "CSNK1A1 Gly40"],
                  "missed": {"IKZF3 Gly155": "relative SASA 0.15, buried in the monomer model",
                             "RBM39 Gly268": "in a helix, not a hairpin, in the monomer model"}},
        "note": ("A method sanity check, NOT the spec 9.2 metric: the set is small, "
                 "it was used for calibration, and it contains no negatives."),
    }
    try:
        out["counts"] = {
            "candidates": connection.execute(
                "SELECT COUNT(*) FROM degron WHERE status = 'ok'").fetchone()[0],
            "proteins": connection.execute(
                "SELECT COUNT(DISTINCT uniprot_acc) FROM degron WHERE status = 'ok'"
            ).fetchone()[0],
        }
    except sqlite3.Error:
        out["counts"] = {"candidates": 0, "proteins": 0}
    return out


# --------------------------------------------------------------------------- #
# 9.3 E3 Triage
# --------------------------------------------------------------------------- #

def mann_whitney_u(group_a: list[float], group_b: list[float]) -> tuple[float, float]:
    """One-sided Mann-Whitney U with a normal approximation and tie correction.

    Implemented here rather than pulled from scipy at import time so the metric
    is auditable: this is the number spec 9.3 turns on.
    """
    n1, n2 = len(group_a), len(group_b)
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan")
    combined = sorted([(v, 0) for v in group_a] + [(v, 1) for v in group_b])
    ranks: list[float] = [0.0] * len(combined)
    index = 0
    tie_correction = 0.0
    while index < len(combined):
        end = index
        while end + 1 < len(combined) and combined[end + 1][0] == combined[index][0]:
            end += 1
        average = (index + end + 2) / 2.0
        size = end - index + 1
        for position in range(index, end + 1):
            ranks[position] = average
        tie_correction += size ** 3 - size
        index = end + 1

    rank_sum_a = sum(r for r, (_v, g) in zip(ranks, combined) if g == 0)
    u_a = rank_sum_a - n1 * (n1 + 1) / 2.0
    mean_u = n1 * n2 / 2.0
    total = n1 + n2
    variance = (n1 * n2 / 12.0) * ((total + 1) - tie_correction / (total * (total - 1)))
    if variance <= 0:
        return u_a, float("nan")
    z = (u_a - mean_u) / math.sqrt(variance)
    # One-sided p for "group A ranks higher" using the survival function of the
    # standard normal.
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return u_a, p


def spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3:
        return float("nan")

    def rank(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        index = 0
        while index < len(order):
            end = index
            while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
                end += 1
            average = (index + end + 2) / 2.0
            for position in range(index, end + 1):
                ranks[order[position]] = average
            index = end + 1
        return ranks

    rx, ry = rank(xs), rank(ys)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def section_93(connection: sqlite3.Connection, config) -> dict:
    floors = config.thresholds["validation"]
    out: dict = {"title": "E3 Triage"}

    try:
        rows = [dict(r) for r in connection.execute(
            "SELECT uniprot_acc, gene, triage_rank, triage_score, pocket_score, "
            "substrate_count, exploitation_status, status FROM ligase")]
    except sqlite3.Error:
        rows = []

    if not rows:
        reason = "The ligase table is empty: stage 2.2 has not produced rows yet."
        out["rank_enrichment_p"] = not_computed(reason, floors["e3_enrichment_p_max"])
        out["substrate_spearman"] = not_computed(reason, floors["e3_substrate_spearman_floor"])
        out["pocket_coverage"] = not_computed(reason, floors["e3_pocket_coverage_floor"])
        return out

    # Coverage: ligases with a pocket score rather than a failure status.
    with_pocket = sum(1 for r in rows if r["pocket_score"] is not None)
    out["pocket_coverage"] = computed(
        round(with_pocket / len(rows), 4), floors["e3_pocket_coverage_floor"],
        n=len(rows), with_pocket=with_pocket)

    # Enrichment: validated ligases should rank near the top WITHOUT the ranking
    # having used that status. `exploitation_status` and `has_ligand` are not
    # weighted components (see pipeline/e3_triage.rank), so the test is not
    # circular; the held-out configuration is recorded here for the audit trail.
    validated_statuses = {"clinically validated", "chemically validated"}
    scores_validated = [
        r["triage_score"] for r in rows
        if r["exploitation_status"] in validated_statuses and r["triage_score"] is not None
    ]
    scores_rest = [
        r["triage_score"] for r in rows
        if r["exploitation_status"] not in validated_statuses and r["triage_score"] is not None
    ]
    if len(scores_validated) < 3 or len(scores_rest) < 3:
        out["rank_enrichment_p"] = not_computed(
            f"too few ligases to test: {len(scores_validated)} validated against "
            f"{len(scores_rest)} others",
            floors["e3_enrichment_p_max"])
    else:
        u, p = mann_whitney_u(scores_validated, scores_rest)
        out["rank_enrichment_p"] = {
            "computed": True, "value": p, "floor": floors["e3_enrichment_p_max"],
            "passes": bool(p < floors["e3_enrichment_p_max"]),
            "reason": "",
            "n_validated": len(scores_validated), "n_rest": len(scores_rest),
            "u_statistic": u,
            "held_out_fields": list(config.t("e3_triage.validation_held_out_fields")),
            "note": ("One-sided Mann-Whitney on the triage score. "
                     "`exploitation_status` and `has_ligand` are not weighted "
                     "components of the score, so the test is not circular."),
        }

    # Substrate-count agreement with UbiBrowser.
    if not dataset_resolved("ubibrowser_literature_e3"):
        out["substrate_spearman"] = not_computed(
            "UbiBrowser literature set unavailable",
            floors["e3_substrate_spearman_floor"])
    else:
        paired = [
            (float(r["substrate_count"]), float(r["substrate_count"]))
            for r in rows if r["substrate_count"] is not None
        ]
        # The atlas column is populated FROM UbiBrowser, so comparing it against
        # UbiBrowser would be a tautology. The honest statement is that this
        # metric cannot be computed as specified.
        out["substrate_spearman"] = not_computed(
            "The atlas `substrate_count` column is populated from the UbiBrowser "
            "literature set itself, so a Spearman correlation against UbiBrowser "
            "would be a tautology (rho = 1 by construction) rather than a test. "
            "A genuine version needs a second, independent substrate source.",
            floors["e3_substrate_spearman_floor"])

    out["counts"] = {
        "ligases": len(rows),
        "by_status": {},
        "by_family": {},
    }
    for row in rows:
        status = row["exploitation_status"] or "unknown"
        out["counts"]["by_status"][status] = out["counts"]["by_status"].get(status, 0) + 1

    # The ranked orphan shortlist: the product of this module.
    orphans = sorted(
        (r for r in rows if r["exploitation_status"] == "orphan"
         and r["triage_score"] is not None),
        key=lambda r: -(r["triage_score"] or 0),
    )[:25]
    out["orphan_shortlist"] = [
        {"gene": r["gene"], "uniprot_acc": r["uniprot_acc"],
         "triage_rank": r["triage_rank"], "triage_score": r["triage_score"],
         "pocket_score": r["pocket_score"], "substrate_count": r["substrate_count"]}
        for r in orphans
    ]
    return out


# --------------------------------------------------------------------------- #
# 9.4 Degradability
# --------------------------------------------------------------------------- #

def section_94(connection: sqlite3.Connection, config) -> dict:
    floors = config.thresholds["validation"]
    window = config.thresholds["degradability"]["reach_window"]
    out: dict = {"title": "Degradability"}

    report = _json_file(INTERIM / "degradability_fit.json")
    if not report:
        out["held_out_auc"] = not_computed(
            "No observed ubiquitylation site table is available, so the window is "
            "unfitted, no verdict is emitted and the AUC is not computed.",
            floors["degradability_auc_floor"])
        out["protein_level_split_honoured"] = not_computed(
            "No fit has run, so there is no split to assert.")
    else:
        out["held_out_auc"] = computed(
            report.get("held_out_auc"), floors["degradability_auc_floor"],
            source=(
                "UniProt CROSSLNK ubiquitin isopeptide annotations for the "
                f"reviewed human proteome ({report.get('n_positive')} observed "
                f"sites on {report.get('n_proteins')} proteins, "
                f"{report.get('n_negative')} unannotated lysines as negatives), "
                "measured on a protein-level split with "
                f"{report.get('n_held_out_positive')} observed sites held out."
            ),
            note=(
                "**SUPERSEDED, and reported because it is the last figure any "
                "artefact holds.** D-067 remeasured exposure against lysines "
                "assayed and found unmodified and got 0.5020, at chance. This "
                "0.5458 was measured against lysines nobody had annotated, "
                "which skew buried because buried lysines are also harder to "
                "detect by mass spectrometry, so the negative set was enriched "
                "for exactly what this feature measures and the number is "
                "biased upward. Read it as an upper bound on a dead criterion, "
                "not as the module's accuracy.\n\n"
                "**Accessibility only.** It is the AUC of lysine NZ relative "
                "accessibility as a predictor of whether a lysine carries an "
                "observed ubiquitylation site. The three Cb-Cb reach boundaries "
                "are unfitted and no reach verdict is emitted: an AlphaFold "
                "monomer carrying an observed site has no ligand site for the "
                "distance to be measured from."
            ),
        )
        # The superseding measurement, read from the artefact that now holds it.
        #
        # D-067's figures were prose in DECISIONS.md and thresholds.toml until
        # degradability_features.py gained an --assayed mode and was run with
        # it. This reads that report rather than restating its numbers.
        assayed = _json_file(INTERIM / "degradability_features.json")
        if assayed and assayed.get("negatives") == "assayed":
            exposure = (assayed.get("feature_sets", {})
                        .get("shipped_exposure_only", {})
                        .get("logistic", {}).get("within_protein_auc"))
            out["exposure_vs_assayed_negatives"] = computed(
                exposure, floors["degradability_auc_floor"],
                source=(
                    f"{assayed.get('n_lysines', 0):,} lysines seen in identified "
                    f"peptides across {assayed.get('n_proteins', 0):,} proteins, "
                    f"{assayed.get('n_positive', 0):,} of them ubiquitylated and "
                    "the rest assayed and found unmodified "
                    f"({assayed.get('dataset')})."
                ),
                note=(
                    "**This supersedes held_out_auc above.** It is the same "
                    "question asked of a negative set that was measured rather "
                    "than assumed, and exposure answers it at chance. Within "
                    "protein, which is the only figure annotation prevalence "
                    "cannot flatter."
                ),
            )
            best = assayed.get("best_within_protein_auc")
            out["best_monomer_feature_set"] = computed(
                best, floors["degradability_auc_floor"],
                note=(
                    "A boosted model over the per-lysine features clears the "
                    "floor where the single shipped criterion does not. It is "
                    "reported and not shipped: spec 5.4 defines four window "
                    "thresholds, and a model is not a window, so emitting its "
                    "score would answer a different question from the one the "
                    "module asks. See D-068."
                ),
            )
        else:
            out["exposure_vs_assayed_negatives"] = not_computed(
                "pipeline/degradability_features.py has not been run with "
                "--assayed, so no artefact holds the measurement against "
                "lysines assayed and found unmodified.",
                floors["degradability_auc_floor"])
        out["protein_level_split_honoured"] = computed(
            True, None,
            note=("A protein contributes wholly to train or wholly to test: "
                  f"{report.get('n_proteins_held_out')} of "
                  f"{report.get('n_proteins')} proteins were held out."))
    out["window_fitted"] = {"computed": True, "value": bool(window.get("fitted")),
                            "reason": "", "fit_status": window.get("fit_status"),
                            "note": ("The fit ran but its held-out AUC misses the "
                                     "floor, so nothing was written back: spec 5.4 "
                                     "forbids a starting value surviving into a "
                                     "shipped config unless the fit lands on it.")
                            if report and not report.get("clears_floor") else None}
    out["honest_limits"] = [
        "Observed ubiquitylation sites come from native E3 biology, not from "
        "induced ternary complexes, so the window would be a proxy even once fitted.",
        "Absence of a reported site is weak evidence that a lysine is unusable: "
        "detection is incomplete and condition-dependent, which biases the "
        "negative set.",
        "An AUC of 0.65 to 0.75 here would be a genuine and useful result. "
        "Anything above 0.9 should be treated as suspected leakage and "
        "investigated before it is believed.",
    ]
    try:
        out["counts"] = {
            "lysines": connection.execute(
                "SELECT COUNT(*) FROM lysine WHERE status = 'ok'").fetchone()[0],
            "with_verdict": connection.execute(
                "SELECT COUNT(*) FROM lysine WHERE verdict IS NOT NULL").fetchone()[0],
        }
    except sqlite3.Error:
        out["counts"] = {"lysines": 0, "with_verdict": 0}
    return out


# --------------------------------------------------------------------------- #
# 9.5 BINMAN-LM
# --------------------------------------------------------------------------- #

def section_95(config) -> dict:
    floors = config.thresholds["validation"]
    out: dict = {"title": "BINMAN-LM"}
    report = INTERIM / "lm_eval.json"
    if not report.exists():
        reason = "Phase 3 has not run: there is no model to evaluate."
        for key, floor in (
            ("parse_rate", floors["lm_parse_rate_floor"]),
            ("set_equality_synthetic", floors["lm_set_equality_synthetic_floor"]),
            ("set_equality_external", floors["lm_set_equality_external_floor"]),
            ("triage_macro_f1", floors["lm_triage_macro_f1_floor"]),
            ("fabrication_rate", floors["lm_fabrication_rate_max"]),
        ):
            out[key] = not_computed(reason, floor)
        return out
    try:
        blob = json.loads(report.read_text())
    except json.JSONDecodeError:
        out["error"] = "lm_eval.json could not be parsed"
        return out

    def _annotate_adapter(record: dict) -> dict:
        """Say so when the recorded adapter path no longer exists.

        The path was written at evaluation time and is not stable:
        models/binman-lm/adapters held round 07 when round 07 was evaluated, a
        later 32B run overwrote it, and D-077 deleted it. The stage name is the
        identifier that survives, so it is reported as the answer and the path
        as the historical note rather than as a location anyone should look in.
        """
        path = record.get("adapter") or ""
        if path and not (Path(__file__).resolve().parents[1] / path).exists():
            record = dict(record)
            record["adapter_note"] = (
                f"`{path}` was the path at evaluation time and no longer "
                "exists (D-077). The stage name identifies the run; "
                "models/binman-lm/runs/binman-qwen-2.5-3b-4bit-round07 is what "
                "serves, and models/binman-lm/served/adapter_config.json "
                "describes it.")
        return record

    # The file is keyed by stage. Prefer the stage named in the model card, then
    # the newest round, so the floors describe the adapter that actually ships
    # rather than whichever evaluation happened to run last.
    stages = [k for k in blob if isinstance(blob.get(k), dict)]
    shipped = config.u("model").get("shipped_stage", "")
    # Sort by round NUMBER, not lexically: "round_with_task_b" sorts after
    # "round09-..." because underscore outranks digits in ASCII, which silently
    # selected an old ad-hoc evaluation as the shipped one.
    numbered = []
    for key in stages:
        match = re.match(r"round(\d+)", key)
        if match:
            numbered.append((int(match.group(1)), key))
    numbered.sort()
    stage = shipped if shipped in stages else (numbered[-1][1] if numbered else None)
    if stage is None:
        out["error"] = "lm_eval.json holds no stage to report"
        return out

    report_blob = blob[stage]
    out["stage_reported"] = stage
    out["available_stages"] = sorted(stages)
    out.update(_annotate_adapter(report_blob))

    # Spec 9.5 floors. These were never checked: section_95 dumped the raw file
    # and the LM was the only module whose floors no gate ever saw.
    synthetic = report_blob.get("task_a_synthetic") or {}
    external = report_blob.get("task_a_external") or {}
    triage = report_blob.get("task_b") or {}
    abstain = report_blob.get("task_c") or {}

    out["parse_rate"] = computed(
        synthetic.get("parse_rate"), floors["lm_parse_rate_floor"],
        n=synthetic.get("n"), source=f"{stage}, synthetic held-out query set")
    out["set_equality_synthetic"] = computed(
        synthetic.get("set_equality"), floors["lm_set_equality_synthetic_floor"],
        n=synthetic.get("n"), source=f"{stage}, synthetic held-out query set")

    if external.get("computed") is False:
        out["set_equality_external"] = not_computed(
            external.get("reason", "no externally phrased query set"),
            floors["lm_set_equality_external_floor"])
    else:
        out["set_equality_external"] = computed(
            external.get("set_equality"),
            floors["lm_set_equality_external_floor"], n=external.get("n"))

    if triage.get("macro_f1") is None:
        out["triage_macro_f1"] = not_computed(
            "Task B was not evaluated for this stage.",
            floors["lm_triage_macro_f1_floor"])
    else:
        out["triage_macro_f1"] = computed(
            triage.get("macro_f1"), floors["lm_triage_macro_f1_floor"],
            n=triage.get("n"),
            note=("Class-balanced sample, 60 per class at a fixed seed. The test "
                  "file is unbalanced and a head slice flatters the rare classes "
                  "(DECISIONS D-034)."))

    # Fabrication is a ceiling, not a floor: lower is better and the spec sets
    # the maximum at zero, so computed()'s >= comparison would read backwards.
    fabrication = abstain.get("fabrication_rate")
    ceiling = floors["lm_fabrication_rate_max"]
    out["fabrication_rate"] = {
        "computed": fabrication is not None,
        "value": fabrication, "floor": ceiling, "reason": "",
        "passes": None if fabrication is None else bool(fabrication <= ceiling),
        "n": abstain.get("n"),
        "note": ("A maximum rather than a minimum: any fabricated number is a "
                 "defect, so the bar is zero and the comparison is <=."),
    }
    out["abstention_rate"] = {
        "computed": abstain.get("abstention_rate") is not None,
        "value": abstain.get("abstention_rate"), "floor": None, "reason": "",
        "n": abstain.get("n"),
    }
    return out


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def run(db_path: Path | None = None, sections: list[str] | None = None) -> dict:
    config = load_config()
    path = db_path or DEFAULT_DB
    if not path.exists():
        raise SystemExit(f"{path} does not exist: build the atlas first")

    # A partial run must not destroy the sections it did not run. Start from
    # whatever is already on disk and overwrite only what this run recomputes:
    # `--section 9.2` silently replaced the whole file before this, and the
    # About tab was rebuilt from the truncated result.
    carried: dict = {}
    if RESULTS.exists():
        try:
            carried = json.loads(RESULTS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            carried = {}

    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        results = {
            **{key: value for key, value in carried.items()
               if key.startswith("9.")},
            "generated_at": utcnow(),
            "atlas": str(path),
            "atlas_bytes": path.stat().st_size,
            "note": (
                "A metric whose dataset is unavailable is reported as "
                "computed: false with the reason. Nothing here is estimated, and "
                "no hand-written control was substituted for a missing published "
                "one (spec 4.1b)."
            ),
        }
        wanted = set(sections or ["9.1", "9.2", "9.3", "9.4", "9.5"])
        if "9.1" in wanted:
            results["9.1"] = section_91(connection, config)
        if "9.2" in wanted:
            results["9.2"] = section_92(connection, config)
        if "9.3" in wanted:
            results["9.3"] = section_93(connection, config)
        if "9.4" in wanted:
            results["9.4"] = section_94(connection, config)
        if "9.5" in wanted:
            results["9.5"] = section_95(config)
    finally:
        connection.close()

    # Floors that were measured and missed, for the gate protocol.
    missed = []
    for key, section in results.items():
        if not isinstance(section, dict) or not key.startswith("9."):
            continue
        for metric, value in section.items():
            if isinstance(value, dict) and value.get("computed") and \
                    value.get("passes") is False:
                missed.append({"section": key, "metric": metric,
                               "value": value.get("value"),
                               "floor": value.get("floor")})
    results["floors_missed"] = missed
    results["metrics_not_computed"] = [
        {"section": key, "metric": metric, "reason": value.get("reason", "")}
        for key, section in results.items()
        if isinstance(section, dict) and key.startswith("9.")
        for metric, value in section.items()
        if isinstance(value, dict) and value.get("computed") is False
    ]

    ordered = {key: results[key] for key in results if not key.startswith("9.")}
    for key in sorted(k for k in results if k.startswith("9.")):
        ordered[key] = results[key]

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(ordered, indent=2, default=str) + "\n")
    Manifest(STAGE).record(
        "run", status="ok", floors_missed=len(missed),
        not_computed=len(results["metrics_not_computed"]), atlas=str(path),
    )
    log_event("9", f"Validation run against {path.name}: "
                   f"{len(results['metrics_not_computed'])} metric(s) not computed "
                   f"(dataset unavailable), {len(missed)} measured floor(s) missed.")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Section 9 validation")
    parser.add_argument("--db", type=Path, default=None,
                        help="atlas to validate; defaults to data/atlas/binman.sqlite")
    parser.add_argument("--section", action="append", default=None)
    args = parser.parse_args()
    results = run(db_path=args.db, sections=args.section)

    print(f"\n--- not computed ({len(results['metrics_not_computed'])}) ---")
    for item in results["metrics_not_computed"]:
        print(f"  {item['section']} {item['metric']}: {item['reason'][:92]}")
    print(f"\n--- measured floors missed ({len(results['floors_missed'])}) ---")
    for item in results["floors_missed"]:
        print(f"  {item['section']} {item['metric']}: {item['value']} "
              f"against floor {item['floor']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
