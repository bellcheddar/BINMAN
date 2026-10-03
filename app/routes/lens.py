"""Lens Graph: a force-directed E3-to-substrate network (spec 6.3)."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from app import db
from app.routes import module_context

bp = Blueprint("lens", __name__, url_prefix="/lens")


@bp.route("/")
def index():
    return render_template(
        "lens.html",
        active="lens",
        page_title="Lens Graph",
        page_blurb=(
            "One network, four lenses. The modules recolour the same graph and "
            "change the side panel rather than showing a different graph. Pruned "
            "to the pinned ligase's neighbourhood by default."
        ),
        focus=request.args.get("focus", ""),
        depth=request.args.get("depth", "2"),
        node_count=db.scalar("SELECT COUNT(*) FROM edge WHERE status = 'ok'"),
        **module_context("ligase"),
    )
