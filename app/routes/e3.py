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
            "The human E3 ligase repertoire ranked on ligandability, structural "
            "coverage, expression selectivity and family. Every component of the "
            "score is a visible column: there is no hidden scoring."
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
        {"label": "orphan", "value": db.scalar(
            "SELECT COUNT(*) FROM ligase WHERE status = 'ok' AND exploitation_status = 'orphan'"),
         "tone": "warn"},
        {"label": "clinically validated", "value": db.scalar(
            "SELECT COUNT(*) FROM ligase WHERE status = 'ok' "
            "AND exploitation_status = 'clinically validated'"), "tone": "good"},
    ]


def _weights() -> list[dict]:
    """The ranking weights, read from thresholds.toml so the UI cannot drift."""
    try:
        from pipeline.common import load_config

        table = load_config().thresholds.get("e3_triage", {})
    except Exception:  # noqa: BLE001
        return []
    return [
        {"name": key.replace("weight_", "").replace("_", " "), "value": value}
        for key, value in sorted(table.items()) if key.startswith("weight_")
    ]
