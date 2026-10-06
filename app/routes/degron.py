"""Degron Scan: structural degron candidates over the AlphaFold human proteome."""

from __future__ import annotations

from flask import Blueprint, render_template

from app import db
from app.routes import module_context
from app.thresholds import table

bp = Blueprint("degron", __name__, url_prefix="/degron")


@bp.route("/")
def index():
    return render_template(
        "degron.html",
        active="degron",
        page_title="Degron Scan",
        page_blurb=(
            "Ranked by the glutarimide degradation model (nested AUC 0.830), "
            "which scores the 4,650 candidates carrying a C2H2 motif; the rest "
            "keep their hairpin geometry rank below them."
        ),
        stats=_stats(),
        **module_context("degron"),
    )


def _stats() -> list[dict]:
    if not db.available() or db.counted("SELECT COUNT(*) FROM degron") == 0:
        return []
    # The cut was written into the SQL as a literal 70, which is a threshold in
    # Python by any reading of it. It comes from the file, and the same value
    # drives the card's note and its filter so all three cannot drift apart.
    plddt = float(table("degron").get("min_mean_plddt", 70.0))
    return [
        {"label": "candidates", "value": db.counted(
            "SELECT COUNT(*) FROM degron WHERE status = 'ok'")},
        {"label": "proteins", "value": db.counted(
            "SELECT COUNT(DISTINCT uniprot_acc) FROM degron WHERE status = 'ok'")},
        {"label": "high confidence", "value": db.counted(
            "SELECT COUNT(*) FROM degron WHERE status = 'ok' AND mean_plddt >= ?",
            (plddt,)),
         "tone": "good", "note": f"tip pLDDT ≥ {plddt:g}",
         "filter": {"field": "mean_plddt", "op": "gte", "value": plddt}},
        # Populated from the two screens the repository carries rather than
        # from a hand-typed list (D-058). It read 0 for every row until then,
        # which is a claim that none of these are known, and a wrong one.
        {"label": "known neosubstrates", "value": db.counted(
            "SELECT COUNT(*) FROM degron WHERE status = 'ok' AND is_known_neosubstrate = 1"),
         "tone": "good", "note": "reported degraded in Sievers or Slabicki",
         "filter": {"field": "is_known_neosubstrate", "op": "eq", "value": 1}},
    ]
