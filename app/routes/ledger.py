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
        series=_novel_series(),
        compare=request.args.get("compare") == "1",
        **module_context("bridge"),
    )


def _novel_series(limit: int = 12) -> dict:
    """The novel glue series, from pipeline/novel_glue_classes.py.

    Read from the artefact rather than recomputed per request: the clustering
    walks every bridge and resolves both chains, which is a build-time job and
    not something to do while someone waits for a page.

    Returns an empty row list when the stage has not run, so the panel
    disappears rather than the page failing.
    """
    import json
    from pathlib import Path

    empty = {"rows": [], "total": 0, "min_ligands": 0, "balance_floor": 0.0}
    path = (Path(__file__).resolve().parents[1] / "static"
            / "novel_glue_series.json")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    out = []
    for row in (report.get("top_pairs") or [])[:limit]:
        interface = row.get("interface") or []
        if len(interface) != 2:
            continue
        out.append({
            "left": interface[0], "right": interface[1],
            "ligands": row.get("n_ligands"), "entries": row.get("n_entries"),
            "median_dsasa": row.get("median_dsasa"),
            # None when the assembly was not cached, which the template shows
            # as "not measured" rather than as a zero.
            "ligand_share": (row.get("widest") or {}).get("ligand_share"),
            # How much of that interface survives in a structure holding both
            # proteins and none of this series' ligands. It is what stops
            # ligand share being over-read: see pipeline/interface_persistence.
            "retained": (row.get("persistence") or {}).get("interface_retained"),
            "focus": (row.get("accessions") or [""])[0],
            "widest": row.get("widest") or {},
        })
    return {
        "rows": out,
        # The table is a window onto a larger set, and saying how much larger is
        # the difference between a list and a finding.
        "total": report.get("series") or 0,
        "min_ligands": report.get("min_ligands_for_series") or 0,
        "balance_floor": report.get("bridging_balance_floor") or 0.0,
    }


def _headline_stats() -> list[dict]:
    if not db.available():
        return []
    total = db.counted("SELECT COUNT(*) FROM bridge WHERE status = 'ok'")
    glue = db.counted(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND ccd_class = 'glue_candidate'"
    )
    furniture = db.counted(
        "SELECT COUNT(*) FROM bridge b JOIN ligand l ON l.ccd_id = b.ccd_id "
        "WHERE b.status = 'ok' AND l.is_furniture = 1"
    )
    symmetry = db.counted(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND symmetry_mediated = 1"
    )
    entries = db.counted("SELECT COUNT(DISTINCT pdb_id) FROM bridge WHERE status = 'ok'")
    novel = db.counted("SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND novel_bridge = 1")
    balanced = db.counted(
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
