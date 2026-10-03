"""Glue Atlas: the primary split-ledger module (spec 6.3, 6.4)."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from app import db
from app.routes import module_context

bp = Blueprint("ledger", __name__)


@bp.route("/")
def index():
    stats = _headline_stats()
    return render_template(
        "ledger.html",
        active="atlas",
        page_title="Glue Atlas",
        page_blurb=(
            "Every non-polymer entity that buries meaningful surface against two or "
            "more distinct polymer chains at once. Crystallisation furniture is "
            "classified, not deleted, so the counts reconcile."
        ),
        stats=stats,
        compare=request.args.get("compare") == "1",
        **module_context("bridge"),
    )


def _headline_stats() -> list[dict]:
    if not db.available():
        return []
    total = db.scalar("SELECT COUNT(*) FROM bridge WHERE status = 'ok'")
    glue = db.scalar(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND ccd_class = 'glue_candidate'"
    )
    furniture = db.scalar(
        "SELECT COUNT(*) FROM bridge b JOIN ligand l ON l.ccd_id = b.ccd_id "
        "WHERE b.status = 'ok' AND l.is_furniture = 1"
    )
    symmetry = db.scalar(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND symmetry_mediated = 1"
    )
    entries = db.scalar("SELECT COUNT(DISTINCT pdb_id) FROM bridge WHERE status = 'ok'")
    novel = db.scalar("SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND novel_bridge = 1")
    balanced = db.scalar(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND bridging_balance >= 0.5 "
        "AND ccd_class = 'glue_candidate'"
    )
    return [
        {"label": "bridges", "value": total, "tone": ""},
        {"label": "entries", "value": entries, "tone": ""},
        {"label": "glue candidates", "value": glue, "tone": "good"},
        {"label": "balanced glues", "value": balanced, "tone": "good",
         "note": "balance ≥ 0.5"},
        {"label": "furniture", "value": furniture, "tone": "warn"},
        {"label": "symmetry mediated", "value": symmetry, "tone": "warn"},
        {"label": "novel bridges", "value": novel, "tone": "bad",
         "note": "not determinable until a curated glue database resolves"},
    ]
