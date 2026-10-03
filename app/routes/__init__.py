"""One blueprint per module (spec 6.1)."""

from __future__ import annotations

from typing import Any

from app import db
from app.queries import RECORD_TYPES, Query, QueryError, execute, parse, schema_summary


def module_context(record_type: str, **extra: Any) -> dict:
    """Shared context for a ledger page: the schema, the counts and the selection.

    Every module renders the same split-ledger shell, so the only differences
    are the record type, the viewer and the module-specific panels.
    """
    spec = RECORD_TYPES[record_type]
    context = {
        "record_type": record_type,
        "record_label": spec.label,
        "schema": schema_summary(),
        "default_columns": list(spec.default_columns),
        "default_sort": spec.default_sort,
        "atlas_available": db.available(),
    }
    context.update(extra)
    return context


def run_query(payload: Any, columns=None) -> tuple[list[dict], dict | None, str]:
    """Parse and execute a query object. Returns (rows, query_dict, error)."""
    connection = db.get()
    if connection is None:
        return [], None, "The atlas has not been built yet."
    try:
        query = parse(payload)
    except QueryError as exc:
        return [], None, str(exc)
    try:
        rows = execute(connection, query, columns)
    except Exception as exc:  # noqa: BLE001
        return [], query.as_dict(), f"{type(exc).__name__}: {exc}"
    return rows, query.as_dict(), ""
