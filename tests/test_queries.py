"""The query parser against the full operator and field grid (spec 10).

This parser is also what validates every generated Task A training pair, so a
gap here becomes label noise in the corpus. The grid is therefore exhaustive
rather than illustrative.
"""

from __future__ import annotations

import itertools

import pytest

from app.queries import (
    DIRECTIONS, MAX_LIMIT, OPERATORS, RECORD_TYPES, Query, QueryError, build_sql,
    parse, schema_summary,
)


def test_every_record_type_parses_with_no_filters():
    for name in RECORD_TYPES:
        query = parse({"record_type": name})
        assert query.record_type == name
        # An absent sort falls back to the record type's default, never to none.
        assert query.sort_field == RECORD_TYPES[name].default_sort


def test_the_full_field_by_operator_grid():
    """Every (field, operator) pair either parses or is refused for a stated reason."""
    checked = 0
    for name, spec in RECORD_TYPES.items():
        for field_name, field_spec in spec.fields.items():
            sample = {
                "number": 1.5, "text": "ABCD", "bool": True,
                "enum": field_spec.enum[0] if field_spec.enum else "x",
            }[field_spec.kind]
            for operator in OPERATORS:
                payload = {"record_type": name,
                           "filters": [{"field": field_name, "op": operator,
                                        "value": sample}]}
                ordering = operator not in {"eq", "ne"}
                if field_spec.kind in {"enum", "bool"} and ordering:
                    with pytest.raises(QueryError, match="only supports eq or ne"):
                        parse(payload)
                else:
                    query = parse(payload)
                    assert query.filters[0].op == operator
                checked += 1
    assert checked > 200, "the grid should be large; got {checked}"


def test_unknown_record_type_names_what_was_allowed():
    with pytest.raises(QueryError) as error:
        parse({"record_type": "bridges"})
    message = str(error.value)
    for name in RECORD_TYPES:
        assert name in message


def test_hallucinated_field_is_refused_and_lists_the_real_ones():
    with pytest.raises(QueryError) as error:
        parse({"record_type": "bridge",
               "filters": [{"field": "dsasa_in_nanometres", "op": "gte", "value": 1}]})
    message = str(error.value)
    assert "dsasa_in_nanometres" in message
    assert "bridging_balance" in message


def test_unknown_operator_is_refused():
    with pytest.raises(QueryError, match="op must be one of"):
        parse({"record_type": "bridge",
               "filters": [{"field": "dsasa_total", "op": "between", "value": 1}]})


def test_invented_enum_value_is_refused():
    with pytest.raises(QueryError, match="takes one of"):
        parse({"record_type": "bridge",
               "filters": [{"field": "ccd_class", "op": "eq",
                            "value": "molecular_adhesive"}]})


def test_non_numeric_value_on_a_numeric_field_is_refused():
    with pytest.raises(QueryError, match="takes a number"):
        parse({"record_type": "bridge",
               "filters": [{"field": "dsasa_total", "op": "gte", "value": "lots"}]})


def test_boolean_is_rejected_on_a_numeric_field():
    """True must not quietly become 1.0 on a numeric field."""
    with pytest.raises(QueryError, match="got a boolean"):
        parse({"record_type": "bridge",
               "filters": [{"field": "dsasa_total", "op": "gte", "value": True}]})


def test_missing_value_is_refused():
    with pytest.raises(QueryError, match="a value is required"):
        parse({"record_type": "bridge",
               "filters": [{"field": "dsasa_total", "op": "gte"}]})


def test_prose_is_not_json():
    with pytest.raises(QueryError, match="not valid JSON"):
        parse("Here is the query you asked for!")


def test_a_json_array_is_not_a_query_object():
    with pytest.raises(QueryError, match="must be a JSON object"):
        parse("[1, 2, 3]")


def test_sort_direction_is_closed():
    for direction in DIRECTIONS:
        query = parse({"record_type": "ligase",
                       "sort": {"field": "triage_rank", "direction": direction}})
        assert query.sort_direction == direction
    with pytest.raises(QueryError, match="sort.direction must be one of"):
        parse({"record_type": "ligase",
               "sort": {"field": "triage_rank", "direction": "sideways"}})


def test_sort_field_must_exist():
    with pytest.raises(QueryError, match="is not a field of"):
        parse({"record_type": "ligase", "sort": {"field": "vibes"}})


def test_limit_is_clamped_and_validated():
    assert parse({"record_type": "bridge", "limit": 10_000_000}).limit == MAX_LIMIT
    assert parse({"record_type": "bridge", "limit": 7}).limit == 7
    with pytest.raises(QueryError, match="at least 1"):
        parse({"record_type": "bridge", "limit": 0})
    with pytest.raises(QueryError, match="must be an integer"):
        parse({"record_type": "bridge", "limit": "many"})


def test_round_trip_through_as_dict_is_stable():
    payload = {
        "record_type": "bridge",
        "filters": [{"field": "bridging_balance", "op": "gte", "value": 0.5},
                    {"field": "ccd_class", "op": "ne", "value": "metal"}],
        "sort": {"field": "dsasa_total", "direction": "desc"},
        "limit": 25,
    }
    once = parse(payload).as_dict()
    twice = parse(once).as_dict()
    assert once == twice


def test_describe_produces_one_readable_line_per_filter():
    query = parse({"record_type": "bridge",
                   "filters": [{"field": "bridging_balance", "op": "gte", "value": 0.5},
                               {"field": "resolution", "op": "lte", "value": 2.5}]})
    lines = query.describe()
    # Record type, two filters and the sort line.
    assert len(lines) == 4
    assert "at least 0.5" in lines[1]
    assert "at most 2.5" in lines[2]
    assert "Å" in lines[2], "a unit must appear where the field has one"


def test_no_user_value_reaches_the_sql_text():
    """Values must always be bound parameters, never interpolated."""
    query = parse({"record_type": "bridge",
                   "filters": [{"field": "ccd_id", "op": "eq",
                                "value": "'; DROP TABLE bridge; --"}]})
    sql, params = build_sql(query)
    assert "DROP TABLE" not in sql
    assert "'; DROP TABLE bridge; --" in params


def test_schema_summary_covers_every_record_type_and_field():
    summary = schema_summary()
    assert set(summary) == set(RECORD_TYPES)
    for name, spec in RECORD_TYPES.items():
        assert set(summary[name]["fields"]) == set(spec.fields)
        for field_name, described in summary[name]["fields"].items():
            assert described["kind"] in {"number", "text", "enum", "bool"}
            assert described["label"]
