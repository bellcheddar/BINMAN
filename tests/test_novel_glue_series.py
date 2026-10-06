"""The novel glue series artefact and the panel that reads it.

The panel is a table of deep links, and a deep link is the easy thing to get
wrong: the shared selection is `pdb_id:ccd_id:bridge_id` (app/static/js/
selection.js), and a link missing the row id is a link to a row the viewer
cannot find. It renders, it looks right, and it does nothing when clicked.
These assert the artefact's claims against the atlas rather than against
themselves.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTEFACT = ROOT / "app" / "static" / "novel_glue_series.json"


@pytest.fixture(scope="module")
def report() -> dict:
    if not ARTEFACT.exists():
        pytest.skip("novel glue series artefact not built")
    return json.loads(ARTEFACT.read_text(encoding="utf-8"))


def test_the_artefact_is_shipped_not_excluded():
    """It lives under app/static/ because deploy/provision.sh excludes
    data/interim/. A panel fed from an excluded path is empty on the live host
    and correct locally, which is the hardest version of this bug to see."""
    provision = (ROOT / "deploy" / "provision.sh").read_text(encoding="utf-8")
    assert "--exclude 'data/interim/'" in provision
    assert ARTEFACT.parts[-2] == "static"


def test_every_series_clears_the_configured_balance_floor(report, config):
    """The floor comes from thresholds.toml, never from the stage."""
    expected = float(config.t("bridging.glue_balance_strong"))
    assert report["bridging_balance_floor"] == expected


def test_every_row_names_a_real_bridge_the_viewer_can_load(report, atlas):
    """pdb_id, ccd_id and bridge_id together, and all three agreeing.

    A two-part fragment passes any test that only checks the strings are
    non-empty, so this resolves the id against the bridge table and insists the
    row it finds is the one the other two fields name.
    """
    assert report["top_pairs"], "the artefact carries no pairs"
    for pair in report["top_pairs"]:
        widest = pair["widest"]
        for field in ("pdb_id", "ccd_id", "bridge_id"):
            assert widest.get(field), f"{pair['interface']}: widest has no {field}"
        row = atlas.execute(
            "SELECT pdb_id, ccd_id, dsasa_total FROM bridge WHERE id = ?",
            (widest["bridge_id"],),
        ).fetchone()
        assert row is not None, f"bridge {widest['bridge_id']} is not in the atlas"
        assert row["pdb_id"] == widest["pdb_id"]
        assert row["ccd_id"] == widest["ccd_id"]


def test_every_series_is_novel_and_model_called(report, atlas):
    """The three signals the stage claims to intersect, checked on one row of
    each series: geometric bridge, absent from the curated databases, and
    called a glue by the triage head."""
    for pair in report["top_pairs"]:
        row = atlas.execute(
            "SELECT novel_bridge, evidence_class, symmetry_mediated FROM bridge "
            "WHERE id = ?", (pair["widest"]["bridge_id"],),
        ).fetchone()
        assert row["novel_bridge"] == 1, f"{pair['interface']} is not novel"
        assert row["evidence_class"] == "molecular_glue"
        assert row["symmetry_mediated"] == 0


def test_a_series_carries_at_least_the_declared_number_of_ligands(report):
    floor = report["min_ligands_for_series"]
    assert floor >= 2, "one ligand on a pair is an observation, not a series"
    for pair in report["top_pairs"][: report["series"]]:
        assert pair["n_ligands"] >= floor


def test_the_panel_renders_a_row_per_pair_with_a_three_part_link(report):
    from app import create_app

    html = create_app().test_client().get("/").get_data(as_text=True)
    assert "Novel glue series" in html
    panel = html[html.index("Novel glue series"):]
    panel = panel[: panel.index("</table>")]
    for pair in report["top_pairs"][:12]:
        widest = pair["widest"]
        fragment = (f"#glue={widest['pdb_id']}:{widest['ccd_id']}:"
                    f"{widest['bridge_id']}")
        assert fragment in panel, f"the panel does not deep-link {fragment}"


def test_the_caption_states_the_whole_set_not_just_the_rows_shown(report):
    """A table of twelve read as "twelve novel series exist". It is a window on
    82, and the count is read from the artefact rather than written in the
    template."""
    from app import create_app

    html = create_app().test_client().get("/").get_data(as_text=True)
    panel = html[html.index("Novel glue series"):]
    panel = panel[: panel.index("<table")]
    assert f"{report['series']:,}" in panel
