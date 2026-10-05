"""Flask application factory (spec 6.1).

Read-only at serve time. One blueprint per module, a shared selection object
held in the browser, and the About tab generated from build artefacts rather
than authored.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, render_template

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
