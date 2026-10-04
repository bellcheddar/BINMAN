"""Degradability: surface lysine accessibility and reach relative to a site."""

from __future__ import annotations

from flask import Blueprint, render_template

from app import db
from app.routes import module_context

bp = Blueprint("degradability", __name__, url_prefix="/degradability")


@bp.route("/")
def index():
    return render_template(
        "degradability.html",
        active="degradability",
        page_title="Degradability",
        page_blurb=(
            "Surface lysine accessibility and geometry relative to a chosen binding "
            "site: the question that kills degrader programmes late and is rarely "
            "asked at nomination."
        ),
        stats=_stats(),
        window=_window(),
        **module_context("lysine"),
    )


def _stats() -> list[dict]:
    if not db.available() or db.scalar("SELECT COUNT(*) FROM lysine") == 0:
        return []
    rows = db.many(
        "SELECT verdict, COUNT(*) AS n FROM lysine WHERE status = 'ok' GROUP BY verdict"
    )
    tones = {"favourable": "good", "marginal": "warn", "unfavourable": "bad"}
    return [
        {"label": row["verdict"] or "unclassified", "value": row["n"],
         "tone": tones.get(row["verdict"], "")}
        for row in rows
    ]


def _window() -> dict:
    """The reach window and its provenance, read from thresholds.toml.

    Spec 5.4 requires the held-out AUC to be shown beside the verdict column so
    the user knows how much weight it carries. An unfitted window says so.
    """
    from app.thresholds import table as _table

    window = _table("degradability").get("reach_window", {})
    if not window:
        return {"fitted": False,
                "fit_status": "config/thresholds.toml is missing or unreadable"}
    return dict(window)
