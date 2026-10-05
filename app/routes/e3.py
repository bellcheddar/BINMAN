"""E3 Triage: the human ligase repertoire ranked on a transparent weighted sum."""

from __future__ import annotations

from flask import Blueprint, render_template

from app import db
from app.routes import module_context

bp = Blueprint("e3", __name__, url_prefix="/e3")


@bp.route("/")
def index():
    return render_template(
        "e3.html",
        active="e3",
        page_title="E3 Triage",
        page_blurb=(
            "The human E3 repertoire ranked on ligandability, structural "
            "coverage, expression selectivity and family, every component a "
            "visible column."
        ),
        stats=_stats(),
        weights=_weights(),
        **module_context("ligase"),
    )


def _stats() -> list[dict]:
    if not db.available() or db.scalar("SELECT COUNT(*) FROM ligase") == 0:
        return []
    return [
        {"label": "ligases", "value": db.scalar(
            "SELECT COUNT(*) FROM ligase WHERE status = 'ok'")},
        {"label": "with a pocket score", "value": db.scalar(
            "SELECT COUNT(*) FROM ligase WHERE status = 'ok' AND pocket_score IS NOT NULL"),
         "tone": "good"},
        # Both of these count an exact value of one field, so the filter
        # reproduces the figure exactly. "with a pocket score" counts a NOT
        # NULL, which the query grammar has no operator for, so it stays a
        # plain figure rather than clicking through to a different number.
        {"label": "orphan", "value": db.scalar(
            "SELECT COUNT(*) FROM ligase WHERE status = 'ok' AND exploitation_status = 'orphan'"),
         "tone": "warn",
         "filter": {"field": "exploitation_status", "op": "eq", "value": "orphan"}},
        {"label": "clinically validated", "value": db.scalar(
            "SELECT COUNT(*) FROM ligase WHERE status = 'ok' "
            "AND exploitation_status = 'clinically validated'"), "tone": "good",
         "filter": {"field": "exploitation_status", "op": "eq",
                    "value": "clinically validated"}},
    ]


def _weights() -> list[dict]:
    """The ranking weights, read from thresholds.toml so the UI cannot drift."""
    try:
        from app.thresholds import table as _table

        table = _table("e3_triage")
    except Exception:  # noqa: BLE001
        return []
    return [
        {"name": key.replace("weight_", "").replace("_", " "), "value": value}
        for key, value in sorted(table.items()) if key.startswith("weight_")
    ]
