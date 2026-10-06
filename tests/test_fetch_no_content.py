"""An empty 2xx body: zero rows, or a truncated transfer?

The RCSB Search API answers a zero-hit query with 204 and no body at all, so
"nothing matched" and "the transfer failed" arrive looking identical. Guessing
either way is wrong: read as zero, a truncated response silently under-counts;
read as an error, a question whose honest answer is "none" kills the stage
asking it, which is what happened to the apo co-occurrence counts.

So the caller declares what an empty body means to it, and the default stays
fatal. Nothing here touches the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def fetcher(tmp_path, monkeypatch):
    from pipeline import common

    monkeypatch.setattr(common, "CACHE", tmp_path)
    instance = common.Fetcher("test")
    monkeypatch.setattr(
        instance, "_attempt",
        lambda *args, **kwargs: (b"", {"status_code": 204, "attempts": 1}),
    )
    return instance


def test_an_empty_body_is_fatal_unless_the_caller_says_otherwise(fetcher):
    with pytest.raises(RuntimeError, match="non-JSON"):
        fetcher.fetch_json("https://example.invalid/none", key="empty_default")


def test_a_caller_can_declare_what_an_empty_body_means(fetcher):
    assert fetcher.fetch_json("https://example.invalid/none",
                              key="empty_dict", no_content={}) == {}
    assert fetcher.fetch_json("https://example.invalid/none",
                              key="empty_none", no_content=None) is None


def test_none_is_a_usable_value_and_not_mistaken_for_the_default(fetcher):
    """`no_content=None` has to be distinguishable from not passing it, which
    is why the default is a sentinel rather than None: None is the natural
    thing a caller wants an empty body to mean."""
    with pytest.raises(RuntimeError):
        fetcher.fetch_json("https://example.invalid/none", key="sentinel_check")
    assert fetcher.fetch_json("https://example.invalid/none",
                              key="sentinel_check_2", no_content=None) is None


def test_search_count_reports_zero_rather_than_raising(monkeypatch):
    """The call site that the bug was found through."""
    from pipeline import rcsb

    class Stub:
        def fetch_json(self, *args, **kwargs):
            assert "no_content" in kwargs, "search_count must declare 204 as zero"
            return kwargs["no_content"]

    assert rcsb.search_count({"type": "group", "nodes": []}, fetcher=Stub()) == 0
