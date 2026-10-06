"""The About page must not call a recorded finding an unreadable value (spec 1.0).

The page's whole claim is that every value on it comes from a build artefact,
and that anything unreadable says "not recorded" rather than a plausible guess.
It was reporting "1 value(s) could not be read from an artefact: licence for
reference 'ubibrowser2'" about a licence field that had in fact been read and
that records a deliberate finding: UbiBrowser 2.0's site states no terms, and
its NAR paper is CC BY-NC-4.0 on the version of record, which covers the article
rather than the database.

That is a false statement about the project's own provenance, so the two states
are separated and this pins the separation.
"""

from __future__ import annotations

import json

import pytest

from pipeline.build_about import ABOUT_JSON, licence_state


@pytest.mark.parametrize("value", [None, "", "   ", "not recorded"])
def test_an_absent_licence_is_missing(value):
    """A real gap must still be reported as unreadable."""
    assert licence_state(value) == "missing"


@pytest.mark.parametrize("value", [
    "not determined",
    "not determined: the project site states no terms",
])
def test_a_checked_source_with_no_terms_is_not_missing(value):
    """Checked and found to publish nothing is the opposite of unread."""
    assert licence_state(value) == "not_published"


@pytest.mark.parametrize("value", [
    "CC-BY-4.0", "publisher terms", "MIT", "free for non-commercial use",
])
def test_a_stated_licence_is_stated(value):
    assert licence_state(value) == "stated"


def test_the_built_page_does_not_call_a_finding_unreadable():
    if not ABOUT_JSON.exists():
        pytest.skip("the About page has not been built")
    about = json.loads(ABOUT_JSON.read_text(encoding="utf-8"))

    published = {entry["key"] for entry in about.get("licences_not_published", [])}
    # A key may legitimately appear in `unrecorded` for a missing DOI and URL,
    # but never for its licence once it is known to publish none.
    for item in about.get("unrecorded", []):
        if item.startswith("licence for reference"):
            key = item.split("'")[1]
            assert key not in published, (
                f"{key} publishes no licence, which is a recorded finding, and "
                "must not be reported as a value that could not be read")

    # Every such entry carries the reason it was recorded with, so the page can
    # say why rather than leaving the reader to assume it was skipped.
    for entry in about.get("licences_not_published", []):
        assert entry.get("key")
        assert entry.get("reason"), f"{entry['key']} has no recorded reason"


# --------------------------------------------------------------------------- #
# the schematic names the adapter that actually serves
# --------------------------------------------------------------------------- #

def test_the_schematic_names_the_served_adapter_in_house_convention():
    """`binman-<model-slug>-roundNN`, read and not typed.

    There are three plausible sources and two of them are wrong.
    `models/binman-lm/training.json` describes the most recent training run,
    which is the 32B experiment that is not deployed, and tuning.toml's
    `shipped_stage` is an evaluation stage name in a different convention. The
    adapter that serves is the one that was converted and pushed, which
    `deploy/hf-adapter/conversion.json` records.
    """
    import re
    from pathlib import Path

    from pipeline.build_about import ROOT, shipped_adapter_name

    name = shipped_adapter_name()
    assert re.fullmatch(r"binman-[a-z0-9.\-]+-round\d{2}", name), name

    conversion = json.loads(
        (ROOT / "deploy" / "hf-adapter" / "conversion.json").read_text(encoding="utf-8"))
    assert conversion["source_adapter"].rstrip("/").endswith(name)

    svg = Path(ROOT / "app" / "static" / "workflow.svg").read_text(encoding="utf-8")
    assert name in svg, "the schematic does not name the served adapter"


def test_the_schematic_describes_all_three_heads_for_a_screen_reader():
    """The SVG is unreadable to assistive tech, so the heads have to be in the
    text description too, not only in the drawing."""
    blob = json.loads(ABOUT_JSON.read_text(encoding="utf-8"))
    description = blob["schematic_description"]
    for head in ("Head A, query", "Head B, triage", "Head C, abstain"):
        assert head in description
    assert shipped_in(description), "the description does not name the adapter"


def shipped_in(text: str) -> bool:
    from pipeline.build_about import shipped_adapter_name

    return shipped_adapter_name() in text
