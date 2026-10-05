"""Flask application factory (spec 6.1).

Read-only at serve time. One blueprint per module, a shared selection object
held in the browser, and the About tab generated from build artefacts rather
than authored.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, render_template, url_for

ROOT = Path(__file__).resolve().parents[1]

MODULES = (
    {"slug": "atlas", "endpoint": "ledger.index", "label": "Glue Atlas",
     "count_key": "bridge", "corner": "glue"},
    {"slug": "degron", "endpoint": "degron.index", "label": "Degron Scan",
     "count_key": "degron", "corner": "target"},
    {"slug": "e3", "endpoint": "e3.index", "label": "E3 Triage",
     "count_key": "ligase", "corner": "ligase"},
    {"slug": "degradability", "endpoint": "degradability.index", "label": "Degradability",
     "count_key": "lysine", "corner": "centre"},
)

# Worked questions for the natural-language box, one set per record type.
#
# They are here rather than in the template because each one has to be
# answerable by the fields that record type actually has: an example that the
# parser rejects teaches the user that the box does not work. Every field named
# below appears in app.queries.RECORD_TYPES for that type.
#
# Every one of them has been run against the live model and the atlas: it has
# to parse, it has to come back for the record type whose page it sits on, and
# it has to return rows. Three earlier candidates were dropped on that test.
# "known neosubstrates with confident structure" made the model invent a field
# and the parser rejected it; "the most exposed lysines" produced a relative
# SASA floor of 0.5, which nothing in this atlas clears.
NL_EXAMPLES = {
    "bridge": (
        "novel bridges",
        "symmetry mediated bridges",
        "bridges burying more than 400 Å²",
    ),
    "degron": (
        # Named with its record type. "known neosubstrates" alone routed to
        # ligase after G6 changed the degron schema summary, and
        # is_known_neosubstrate is a degron field, so the parser rejected it.
        # The model's record-type choice is sensitive to incidental schema
        # text, so a preset should not rely on it inferring one.
        "degrons that are known neosubstrates",
        "degrons with a mean pLDDT above 80",
        "degrons with an exposed tip",
    ),
    "ligase": (
        "orphan ligases",
        "ligases with more than 10 PDB entries",
        "ligases with a pocket score above 0.5",
    ),
    "lysine": (
        "lysines within 12 Å of the site centroid",
        "lysines with a Cβ-Cβ distance under 20 Å",
        "lysines with relative SASA above 0.1",
    ),
}


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.update(
        BINMAN_DB=os.environ.get("BINMAN_DB", str(ROOT / "data" / "atlas" / "binman.sqlite")),
        BINMAN_LM_URL=os.environ.get("BINMAN_LM_URL", ""),
        JSON_SORT_KEYS=False,
        TEMPLATES_AUTO_RELOAD=bool(os.environ.get("BINMAN_DEBUG")),
    )
    if config:
        app.config.update(config)

    # Cache-bust every static URL with the file's modification time.
    #
    # The assets ship with `cache-control: no-cache`, which asks a browser to
    # revalidate, and in practice browsers still served a mixture of old and
    # new files across a deploy: a stale molstar-bridge.js beside a fresh
    # ledger.js is a combination neither version was ever tested as, and it
    # presents as the table and the viewer being empty rather than as an error.
    #
    # A changed file gets a changed URL, so the stale copy is not a candidate
    # to serve and the failure cannot happen. Cheaper than reasoning about
    # revalidation, and it is the one fix that does not depend on the browser
    # behaving.
    @app.url_defaults
    def _static_cache_key(endpoint: str, values: dict) -> None:
        if endpoint != "static" or "filename" not in values:
            return
        try:
            stamp = os.stat(os.path.join(app.static_folder,
                                         values["filename"])).st_mtime
        except OSError:
            return          # a missing file is the router's problem, not this
        values["v"] = int(stamp)

    from app import db, lm
    from app.routes import about, degradability, degron, e3, ledger, lens

    app.teardown_appcontext(db.close)

    app.register_blueprint(ledger.bp)
    app.register_blueprint(degron.bp)
    app.register_blueprint(e3.bp)
    app.register_blueprint(degradability.bp)
    app.register_blueprint(lens.bp)
    app.register_blueprint(about.bp)

    from app.routes import api
    app.register_blueprint(api.bp)

    @app.context_processor
    def inject_globals():
        counts = db.table_counts()
        return {
            "modules": MODULES,
            # record type -> module URL, so a model proposal for another record
            # type can be handed to the page that owns it rather than silently
            # dropping every filter that page does not share.
            "module_urls": {
                module["count_key"]: url_for(module["endpoint"])
                for module in MODULES
            },
            "nl_examples": NL_EXAMPLES,
            "counts": counts,
            "atlas_available": db.available(),
            "lm_enabled": lm.enabled(),
            "nav_extra": (
                {"endpoint": "lens.index", "label": "Lens Graph"},
                {"endpoint": "about.index", "label": "About"},
            ),
        }

    @app.template_filter("thousands")
    def thousands(value):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return value

    @app.template_filter("sigfig")
    def sigfig(value, digits=3):
        """Render a number for display without implying precision it lacks."""
        if value is None or value == "":
            return "not recorded"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        if number == int(number) and abs(number) < 1e6:
            return f"{int(number):,}"
        return f"{number:.{digits}g}"

    @app.template_filter("tojson_compact")
    def tojson_compact(value):
        return json.dumps(value, separators=(",", ":"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404,
                               message="That page is not part of the atlas."), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("error.html", code=500,
                               message="Something failed while reading the atlas."), 500

    return app


app = create_app()
