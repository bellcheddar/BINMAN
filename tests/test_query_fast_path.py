"""The base-table-first path must return exactly what the join-first path did.

The bridge record type is a join, so `SELECT ... FROM (join) ORDER BY
dsasa_total LIMIT 200` joined all 286,000 rows to entry and ligand and sorted
the lot in a temp B-tree to return 200: 90 ms locally, 1.2 s on the droplet, on
the endpoint every page view fires. When nothing in the query touches a joined
column the same answer comes from filtering, sorting and limiting the base
table first.

"The same answer" is the claim, so it is the thing tested: both paths, same
query, compared row for row.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASES = [
    {"record_type": "bridge", "filters": [], "limit": 50},
    {"record_type": "bridge", "limit": 50,
     "filters": [{"field": "novel_bridge", "op": "eq", "value": 1}]},
    {"record_type": "bridge", "limit": 50,
     "filters": [{"field": "bridging_balance", "op": "gte", "value": 0.5}],
     "sort": {"field": "bridging_balance", "direction": "desc"}},
    {"record_type": "bridge", "limit": 25,
     "filters": [{"field": "ccd_class", "op": "eq", "value": "glue_candidate"},
                 {"field": "symmetry_mediated", "op": "eq", "value": 0}],
     "sort": {"field": "dsasa_total", "direction": "asc"}},
]


def _join_first_sql(query) -> tuple[str, list]:
    """What build_sql produced before the fast path, rebuilt here so the test
    does not depend on the old code still existing."""
    from app.queries import OPERATORS

    spec = query.spec
    select = ", ".join(list(spec.identity_columns))
    for name in spec.default_columns:
        if name not in select.split(", "):
            select += f", {name}"
    where = ["status = 'ok'"]
    params: list = []
    for item in query.filters:
        where.append(f"{item.field} {OPERATORS[item.op]} ?")
        params.append(item.value)
    params.append(query.limit)
    return (f"SELECT {select} FROM {spec.table} WHERE {' AND '.join(where)} "
            f"ORDER BY {query.sort_field} {query.sort_direction.upper()} LIMIT ?"), params


@pytest.mark.parametrize("payload", CASES)
def test_both_paths_return_the_same_rows(payload, atlas):
    from app.queries import build_sql, parse

    query = parse(payload)
    fast_sql, fast_params = build_sql(query, None)
    assert "SELECT * FROM bridge WHERE" in fast_sql, "the fast path did not fire"

    slow_sql, slow_params = _join_first_sql(query)
    fast = [tuple(r) for r in atlas.execute(fast_sql, fast_params)]
    slow = [tuple(r) for r in atlas.execute(slow_sql, slow_params)]
    assert fast == slow


def test_a_joined_column_falls_back(atlas):
    """`resolution` lives on entry, so the base table cannot answer it alone."""
    from app.queries import build_sql, parse

    for payload in (
        {"record_type": "bridge", "filters": [],
         "sort": {"field": "resolution", "direction": "asc"}, "limit": 10},
        {"record_type": "bridge", "limit": 10,
         "filters": [{"field": "resolution", "op": "lte", "value": 2.0}]},
    ):
        sql, params = build_sql(parse(payload), None)
        assert "SELECT * FROM bridge WHERE" not in sql
        assert len(atlas.execute(sql, params).fetchall()) <= 10


def test_the_compound_indexes_are_in_the_shipped_atlas(atlas):
    """Without them the base-table sort is still a temp B-tree, which is most of
    what the fast path was meant to remove."""
    names = {row[0] for row in atlas.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'bridge'")}
    assert "idx_bridge_status_dsasa" in names
    assert "idx_bridge_status_balance" in names

    plan = [row[-1] for row in atlas.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM bridge WHERE status = 'ok' "
        "ORDER BY dsasa_total DESC LIMIT 200")]
    assert not any("TEMP B-TREE" in step for step in plan), plan


def test_the_row_count_does_not_join_when_it_does_not_have_to(atlas):
    """A LEFT JOIN cannot change how many bridge rows there are, and counting
    over the join made the API spend 2.0 s arriving at the number of rows in
    `bridge`."""
    import time

    from app.queries import count, parse

    query = parse({"record_type": "bridge", "filters": [], "limit": 200})
    joined = atlas.execute(
        f"SELECT COUNT(*) FROM {query.spec.table} WHERE status = 'ok'").fetchone()[0]

    started = time.perf_counter()
    counted = count(atlas, query)
    elapsed = time.perf_counter() - started

    assert counted == joined, "the cheap count disagrees with the join"
    assert elapsed < 0.2, f"the count still joins: {elapsed:.3f}s"


def test_a_filter_on_a_joined_column_still_counts_over_the_join(atlas):
    from app.queries import count, parse

    query = parse({"record_type": "bridge", "limit": 10,
                   "filters": [{"field": "resolution", "op": "lte", "value": 2.0}]})
    expected = atlas.execute(
        f"SELECT COUNT(*) FROM {query.spec.table} WHERE status = 'ok' "
        f"AND resolution <= ?", (2.0,)).fetchone()[0]
    assert count(atlas, query) == expected


def test_the_atlas_carries_query_planner_statistics(atlas):
    """Without ANALYZE the planner cannot tell which of two usable indexes is
    selective, and chooses by position in the schema."""
    tables = {row[0] for row in atlas.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "sqlite_stat1" in tables, "the build did not run ANALYZE"
