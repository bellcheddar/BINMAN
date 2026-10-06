"""Whole-table counts are computed once per build, not once per request.

Every page ran seven COUNT(*) scans over a 286,000-row bridge table before it
rendered anything, two of them joined, and `table_counts` ran in
`inject_globals` so it happened on every page of every module and not only the
ones that show counts. That was 1.27 s of a 1.40 s response, which is what the
launcher's health check was reporting as 1,387 ms.

The atlas is a read-only file that changes only when a build replaces it, so
the risk a cache introduces is serving yesterday's numbers after a rebuild.
These assert that it does not.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def app_with_atlas(tmp_path):
    from app import create_app, db

    path = tmp_path / "tiny.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE bridge (id INTEGER, status TEXT)")
    connection.executemany("INSERT INTO bridge VALUES (?, 'ok')", [(i,) for i in range(3)])
    connection.commit()
    connection.close()

    application = create_app()
    application.config["BINMAN_DB"] = str(path)
    db.clear_cache()
    return application, db, path


def test_a_count_is_computed_once_and_then_reused(app_with_atlas):
    application, db, _ = app_with_atlas
    sql = "SELECT COUNT(*) FROM bridge WHERE status = 'ok'"
    with application.test_request_context():
        assert db.counted(sql) == 3
    with application.test_request_context():
        assert db.counted(sql) == 3
    assert len(db._COUNT_CACHE) == 1


def test_rewriting_the_atlas_invalidates_it(app_with_atlas):
    """The failure this guards: a build replaces the database and the running
    process keeps serving the previous counts until somebody restarts it."""
    application, db, path = app_with_atlas
    sql = "SELECT COUNT(*) FROM bridge WHERE status = 'ok'"
    with application.test_request_context():
        assert db.counted(sql) == 3

    connection = sqlite3.connect(path)
    connection.executemany("INSERT INTO bridge VALUES (?, 'ok')", [(9,), (10,)])
    connection.commit()
    connection.close()
    # mtime_ns moves on write, which is the whole fingerprint; make sure the
    # filesystem actually recorded a change rather than relying on timing.
    import os
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    with application.test_request_context():
        assert db.counted(sql) == 5, "the cache outlived the atlas it described"


def test_two_different_questions_do_not_share_an_answer(app_with_atlas):
    application, db, _ = app_with_atlas
    with application.test_request_context():
        total = db.counted("SELECT COUNT(*) FROM bridge WHERE status = 'ok'")
        subset = db.counted("SELECT COUNT(*) FROM bridge WHERE id = 0")
    assert total == 3 and subset == 1


def test_a_missing_atlas_returns_the_default_rather_than_raising(tmp_path):
    from app import create_app, db

    application = create_app()
    application.config["BINMAN_DB"] = str(tmp_path / "absent.sqlite")
    db.clear_cache()
    with application.test_request_context():
        assert db.counted("SELECT COUNT(*) FROM bridge", default=-1) == -1
        assert db.table_counts()["bridge"] == 0
