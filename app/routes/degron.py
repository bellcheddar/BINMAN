"""Degron Scan: structural degron candidates over the AlphaFold human proteome."""

from __future__ import annotations

from flask import Blueprint, render_template

from app import db
from app.routes import module_context

bp = Blueprint("degron", __name__, url_prefix="/degron")


@bp.route("/")
def index():
    return render_template(
        "degron.html",
        active="degron",
        page_title="Degron Scan",
        page_blurb=(
            "The β-hairpin-with-exposed-glycine geometry that underlies CRBN "
            "neosubstrate recognition, found by geometry rather than by sequence "
            "motif. This is a geometric filter and its score is a rank, not a "
            "calibrated probability."
        ),
        stats=_stats(),
        **module_context("degron"),
    )


def _stats() -> list[dict]:
    if not db.available() or db.scalar("SELECT COUNT(*) FROM degron") == 0:
        return []
    return [
        {"label": "candidates", "value": db.scalar(
            "SELECT COUNT(*) FROM degron WHERE status = 'ok'")},
        {"label": "proteins", "value": db.scalar(
            "SELECT COUNT(DISTINCT uniprot_acc) FROM degron WHERE status = 'ok'")},
        {"label": "high confidence", "value": db.scalar(
            "SELECT COUNT(*) FROM degron WHERE status = 'ok' AND mean_plddt >= 70"),
         "tone": "good", "note": "tip pLDDT ≥ 70"},
        {"label": "known neosubstrates", "value": db.scalar(
            "SELECT COUNT(*) FROM degron WHERE status = 'ok' AND is_known_neosubstrate = 1"),
         "tone": "good"},
    ]
