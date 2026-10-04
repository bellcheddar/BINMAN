"""Section 9 validation mechanics.

Nothing here touches the network or recomputes a metric: these guard the
bookkeeping around the metrics, which is where the damage happens quietly.
"""

from __future__ import annotations

import json

import pytest

from pipeline import validate


def test_partial_run_keeps_the_sections_it_did_not_run(tmp_path, monkeypatch):
    """`--section 9.2` must not delete 9.1, 9.3, 9.4 and 9.5.

    It did: `run()` built a fresh dict and wrote it over the file, so a partial
    run silently truncated `results.json`, and `build_about` then rebuilt the
    About tab from whatever survived.
    """
    results = tmp_path / "results.json"
    results.write_text(json.dumps({
        "generated_at": "2026-01-01T00:00:00+00:00",
        "9.1": {"title": "Glue Atlas", "recall": {"computed": True, "value": 0.77}},
        "9.3": {"title": "E3 Triage", "enrichment_p": {"computed": True, "value": 0.0024}},
    }) + "\n")
    monkeypatch.setattr(validate, "RESULTS", results)

    atlas = validate.DEFAULT_DB
    if not atlas.exists():
        pytest.skip("atlas not built")

    validate.run(sections=["9.2"])

    after = json.loads(results.read_text())
    assert "9.2" in after, "the section that was asked for must be written"
    assert "9.1" in after, "a section that was not run must survive"
    assert "9.3" in after, "a section that was not run must survive"
    assert after["9.1"]["recall"]["value"] == 0.77, "carried sections must be untouched"


def test_full_run_replaces_every_section(tmp_path, monkeypatch):
    """A full run must overwrite stale sections rather than merge into them."""
    results = tmp_path / "results.json"
    results.write_text(json.dumps({
        "9.1": {"title": "stale", "recall": {"computed": True, "value": 0.01}},
    }) + "\n")
    monkeypatch.setattr(validate, "RESULTS", results)

    if not validate.DEFAULT_DB.exists():
        pytest.skip("atlas not built")

    validate.run()

    after = json.loads(results.read_text())
    assert after["9.1"]["title"] != "stale"
    assert after["9.1"]["recall"]["value"] != 0.01


def test_roc_auc_matches_a_hand_computed_case():
    """The AUC is spelled out in-tree, so it is worth pinning to known values."""
    # Perfect separation, ties absent.
    assert validate.roc_auc([(0.9, 1), (0.8, 1), (0.2, 0), (0.1, 0)] ) == 1.0
    # Reversed: every positive below every negative.
    assert validate.roc_auc([(0.1, 1), (0.2, 1), (0.8, 0), (0.9, 0)]) == 0.0
    # All tied: no information, which must read as chance rather than as 1.0.
    assert validate.roc_auc([(0.5, 1), (0.5, 1), (0.5, 0), (0.5, 0)]) == 0.5
    # One arm empty is undefined, not zero.
    assert validate.roc_auc([(0.5, 1), (0.9, 1)]) != validate.roc_auc(
        [(0.5, 1), (0.9, 0)])


def test_threshold_sweep_reports_when_no_cut_passes():
    """The G6 case for 9.2 rests on this returning False, so pin both branches."""
    # A score with no signal: positives and negatives interleaved.
    noise = [(0.1, 1), (0.2, 0), (0.3, 1), (0.4, 0), (0.5, 1), (0.6, 0)]
    out = validate.degron_threshold_sweep(noise, 0.70, 0.60)
    assert out["any_cut_passes_both_floors"] is False
    assert out["passing_cut"] is None

    # A score that separates cleanly must find a passing cut.
    clean = [(0.9, 1), (0.8, 1), (0.85, 1), (0.1, 0), (0.2, 0), (0.15, 0)]
    out = validate.degron_threshold_sweep(clean, 0.70, 0.60)
    assert out["any_cut_passes_both_floors"] is True
    assert out["passing_cut"]["sensitivity"] >= 0.70
    assert out["passing_cut"]["specificity"] >= 0.60
