"""About tab: generated, never authored (spec 6.6).

Every number, version, citation and count is read from `app/static/about.json`,
which `pipeline/build_about.py` writes from the build artefacts. This module
renders that file and nothing else: there is no literal metric in the template.
Where a value could not be read from an artefact the page shows "not recorded".
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, render_template

bp = Blueprint("about", __name__, url_prefix="/about")

ABOUT_JSON = Path(__file__).resolve().parents[1] / "static" / "about.json"
WORKFLOW_SVG = Path(__file__).resolve().parents[1] / "static" / "workflow.svg"


@bp.route("/")
def index():
    about = _load()
    return render_template(
        "about.html",
        active="about",
        page_title="About BINMAN",
        about=about,
        generated=bool(about),
        # The schematic is INLINED rather than served through <img>. An SVG
        # loaded as an image is a separate document and cannot see the page's
        # CSS custom properties, so every var(--token) fill resolved to black.
        # Spec 6.6.1 requires both palettes to work, which needs the SVG in the
        # same document as the tokens.
        workflow_svg=_svg(),
    )


def _svg() -> str:
    if not WORKFLOW_SVG.exists():
        return ""
    return WORKFLOW_SVG.read_text(encoding="utf-8")


def _load() -> dict:
    if not ABOUT_JSON.exists():
        return {}
    try:
        return json.loads(ABOUT_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
