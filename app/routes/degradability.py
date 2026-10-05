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
            "Surface lysine accessibility and geometry relative to a chosen "
            "binding site: the question that kills degrader programmes late."
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
    # The scale of the set first, then its verdict breakdown. Without the first
    # two the page led with "unclassified" and said nothing about what had been
    # measured; the reach window is unfitted, so every verdict is null and that
    # single card was the whole summary.
    stats = [
        {"label": "lysines", "value": db.scalar(
            "SELECT COUNT(*) FROM lysine WHERE status = 'ok'")},
        {"label": "proteins", "value": db.scalar(
            "SELECT COUNT(DISTINCT uniprot_acc) FROM lysine WHERE status = 'ok'")},
        {"label": "structures", "value": db.scalar(
            "SELECT COUNT(DISTINCT structure_id) FROM lysine WHERE status = 'ok'")},
    ]
    # A verdict card filters to its own verdict, which is the same predicate
    # the figure was counted with. A null verdict has no operator in the query
    # grammar, so "unclassified" stays a plain figure.
    stats.extend(
        {"label": row["verdict"] or "unclassified", "value": row["n"],
         "tone": tones.get(row["verdict"], ""),
         "filter": ({"field": "verdict", "op": "eq", "value": row["verdict"]}
                    if row["verdict"] else None)}
        for row in rows
    )
    return stats


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
