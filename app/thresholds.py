"""Read `config/thresholds.toml` without importing the build pipeline.

The serving app had been doing `from pipeline.common import load_config`, which
works on the Studio where the whole repository is present and fails on the
droplet, where only `app/`, `config/`, `data/atlas/` and `wsgi.py` are
deployed. Every call site wrapped it in `except Exception` and fell back, so
nothing crashed and three things quietly went wrong instead:

* the Degradability page reported "thresholds could not be read" and showed no
  reach window,
* the Lens graph fell back to a 400-node cap rather than the configured one,
* the E3 page lost its triage weights.

A clean console and a silent fallback is worse than an error, because the page
looks finished. Reading the TOML directly removes the dependency: the pipeline
is a build-time package and the app is a serving one, and the only thing they
need to share is a file.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

# app/thresholds.py -> app/ -> project root, which holds config/ both on the
# Studio and under /opt/binman on the droplet.
CONFIG = Path(__file__).resolve().parents[1] / "config" / "thresholds.toml"


@lru_cache(maxsize=1)
def thresholds() -> dict:
    """The parsed thresholds table, or an empty dict if it cannot be read."""
    try:
        return tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def table(name: str) -> dict:
    """One top-level table, empty when absent."""
    value = thresholds().get(name, {})
    return value if isinstance(value, dict) else {}


def value(path: str, default=None):
    """A dotted lookup such as `atlas.lens_graph_max_nodes`."""
    current = thresholds()
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current
