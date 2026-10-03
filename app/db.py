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


def table_counts() -> dict[str, int]:
    """Row counts per table, for the rail and the About tab.

    Returns zeroes rather than raising when the atlas is absent, so every page
    renders an honest empty state instead of a 500.
    """
    connection = get()
    if connection is None:
        return {name: 0 for name in
                ("entry", "bridge", "ligand", "degron", "ligase", "lysine", "edge")}
    counts: dict[str, int] = {}
    for name in ("entry", "bridge", "ligand", "degron", "ligase", "lysine", "edge"):
        try:
            counts[name] = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {name} WHERE status = 'ok'"
                ).fetchone()[0]
            )
        except sqlite3.Error:
            counts[name] = 0
    return counts
