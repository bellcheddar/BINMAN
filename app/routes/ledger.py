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
            "Non-polymer entities burying surface against two or more polymer "
            "chains at once, with crystallisation furniture classified rather "
            "than deleted."
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
    # `filter` makes a card clickable: it applies exactly the predicate the
    # figure was counted with, so the number above and the rows below describe
    # the same set. A card without one is a plain figure, because "bridges" and
    # "entries" are the unfiltered total and filtering to them is a no-op.
    return [
        {"label": "bridges", "value": total, "tone": ""},
        {"label": "entries", "value": entries, "tone": ""},
        {"label": "glue candidates", "value": glue, "tone": "good",
         "filter": {"field": "ccd_class", "op": "eq", "value": "glue_candidate"}},
        {"label": "balanced glues", "value": balanced, "tone": "good",
         "note": "balance ≥ 0.5",
         "filter": [{"field": "ccd_class", "op": "eq", "value": "glue_candidate"},
                    {"field": "bridging_balance", "op": "gte", "value": 0.5}]},
        # No filter: furniture is counted through a join on ligand.is_furniture,
        # which is not a bridge field. A card whose filter shows a different
        # number from the card is worse than a card that does not click.
        {"label": "furniture", "value": furniture, "tone": "warn"},
        {"label": "symmetry mediated", "value": symmetry, "tone": "warn",
         "filter": {"field": "symmetry_mediated", "op": "eq", "value": 1}},
        {"label": "novel bridges", "value": novel, "tone": "bad",
         "filter": {"field": "novel_bridge", "op": "eq", "value": 1}},
    ]
