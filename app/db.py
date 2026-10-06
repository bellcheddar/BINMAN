"""Read-only SQLite access for the serving layer (spec 6.1).

No folding, no FreeSASA, no fpocket at request time: the droplet serves a
precomputed atlas and nothing else. The connection is opened read-only and in
URI mode so a misconfigured deployment cannot write to the atlas, and it is
cached per request on Flask's `g`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "atlas" / "binman.sqlite"


def db_path() -> Path:
    return Path(current_app.config.get("BINMAN_DB", DEFAULT_DB))


def available() -> bool:
    return db_path().exists()


def get() -> sqlite3.Connection | None:
    """The request-scoped read-only connection, or None when there is no atlas."""
    if "binman_db" not in g:
        path = db_path()
        if not path.exists():
            g.binman_db = None
        else:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro", uri=True, check_same_thread=False
            )
            connection.row_factory = sqlite3.Row
            g.binman_db = connection
    return g.binman_db


def close(_exception=None) -> None:
    connection = g.pop("binman_db", None)
    if connection is not None:
        connection.close()


# --------------------------------------------------------------------------- #
# the counted-once cache
# --------------------------------------------------------------------------- #

# Every page was running seven COUNT(*) scans over a 286,000-row bridge table,
# two of them joined, before it rendered anything: 1.27 s of a 1.40 s response,
# repeated for every visitor and every reload. The atlas is a read-only file
# that changes only when a build replaces it, so these are constants between
# builds and there is no reason to recount them per request.
#
# Keyed on the database's path, size and mtime, so a rebuilt atlas invalidates
# the cache by existing rather than by anyone remembering to clear it. Keyed in
# a module-level dict rather than on `g`, because `g` is per request and that is
# exactly the scope the problem had.
_COUNT_CACHE: dict = {}


def _atlas_fingerprint() -> tuple | None:
    path = db_path()
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), stat.st_size, stat.st_mtime_ns)


def counted(sql: str, params: tuple = (), default=0):
    """A scalar that is cached until the atlas file changes.

    For figures derived from the whole table: counts, sums, extremes. The key is
    the query itself, so two different questions cannot collide on one hand
    written label, and a query that varies with the request varies its own key
    and so is simply never reused. Do not use it for anything unbounded: a
    per-row lookup would grow the cache without limit.
    """
    fingerprint = _atlas_fingerprint()
    if fingerprint is None:
        return default
    key = (sql, params)
    cached = _COUNT_CACHE.get(key)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]
    value = scalar(sql, params, default)
    _COUNT_CACHE[key] = (fingerprint, value)
    return value


def clear_cache() -> None:
    """Drop the cached counts. For tests, and for a process that outlives a build."""
    _COUNT_CACHE.clear()


def one(sql: str, params: tuple = ()) -> dict | None:
    connection = get()
    if connection is None:
        return None
    row = connection.execute(sql, params).fetchone()
    return dict(row) if row else None


def many(sql: str, params: tuple = ()) -> list[dict]:
    connection = get()
    if connection is None:
        return []
    return [dict(row) for row in connection.execute(sql, params).fetchall()]


def scalar(sql: str, params: tuple = (), default=0):
    connection = get()
    if connection is None:
        return default
    row = connection.execute(sql, params).fetchone()
    if row is None or row[0] is None:
        return default
    return row[0]


TABLES = ("entry", "bridge", "ligand", "degron", "ligase", "lysine", "edge")


def table_counts() -> dict[str, int]:
    """Row counts per table, for the rail and the About tab.

    Cached with the rest: this runs in `inject_globals`, so it was seven table
    scans on every page of every module, not just the ones that show counts.

    Returns zeroes rather than raising when the atlas is absent, so every page
    renders an honest empty state instead of a 500.
    """
    if get() is None:
        return {name: 0 for name in TABLES}
    counts: dict[str, int] = {}
    for name in TABLES:
        try:
            counts[name] = int(counted(
                f"SELECT COUNT(*) FROM {name} WHERE status = 'ok'"))
        except sqlite3.Error:
            counts[name] = 0
    return counts
