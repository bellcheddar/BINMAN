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


def test_the_interface_was_measured_for_every_cached_assembly(report):
    """`protein_protein_dsasa` and `ligand_share` are present, or the row says
    why not. A silent zero would read as "these chains do not touch", which is
    the most interesting thing this column can say and so the worst thing to
    fabricate."""
    for pair in report["top_pairs"]:
        widest = pair["widest"]
        assert widest.get("status"), f"{pair['interface']}: no measurement status"
        if widest["status"] != "ok":
            assert "cached" in widest["status"] or "absent" in widest["status"]
            assert "protein_protein_dsasa" not in widest
            continue
        assert widest["protein_protein_dsasa"] >= 0
        assert 0.0 <= widest["ligand_share"] <= 1.0


def test_ligand_share_is_the_ratio_it_claims_to_be(report):
    """share = ligand area / (ligand area + chain-chain area), both in the
    spec 5.1 two-sided convention. Asserted rather than trusted, because a
    ratio of two areas measured in different conventions looks plausible and
    is wrong."""
    for pair in report["top_pairs"]:
        widest = pair["widest"]
        if widest.get("status") != "ok":
            continue
        ligand = widest["dsasa"]
        chains = widest["protein_protein_dsasa"]
        expected = ligand / (ligand + chains)
        assert abs(widest["ligand_share"] - expected) < 0.002, pair["interface"]


def test_the_known_cereblon_degrader_series_is_in_the_set(report, atlas):
    """A positive control the method was not tuned on.

    9E2U is DDB1-CRBN with the triple zinc finger of Helios and a glutarimide
    degrader. It is a textbook molecular glue, no curated glue database the
    build resolved lists its ligand, and the clustering finds it without being
    told to look. If this row disappears, the novel set has stopped containing
    real glues.
    """
    pairs = {tuple(p["interface"]) for p in report["top_pairs"]}
    assert any("cereblon" in " ".join(p).lower() for p in pairs), (
        "the CRBN degrader series is no longer in the top pairs")
    row = atlas.execute(
        "SELECT novel_bridge, evidence_class FROM bridge "
        "WHERE pdb_id = '9E2U' AND ccd_id = 'RN9' AND status = 'ok' LIMIT 1"
    ).fetchone()
    assert row is not None, "9E2U/RN9 is not in the atlas"
    assert row["novel_bridge"] == 1
    assert row["evidence_class"] == "molecular_glue"


def test_interface_persistence_ran_after_the_clustering(report):
    """The clustering writes the artefact and the persistence stage rewrites
    it. Run them the other way round and the second write erases the first,
    silently, leaving a page that looks complete."""
    assert report.get("persistence_measured_at"), (
        "pipeline/interface_persistence.py has not run since the last clustering")
    measured = [p for p in report["top_pairs"]
                if (p.get("persistence") or {}).get("status") == "ok"]
    assert measured, "no series has a comparison structure"


def test_a_retained_ratio_is_a_ratio_of_two_measured_areas(report):
    for pair in report["top_pairs"]:
        persistence = pair.get("persistence") or {}
        if persistence.get("status") != "ok":
            assert persistence.get("status") == "no comparison structure"
            continue
        bridged = pair["widest"]["protein_protein_dsasa"]
        without = persistence["widest_without_series"]
        assert without >= 0
        if bridged:
            expected = without / bridged
            assert abs(persistence["interface_retained"] - expected) < 0.01


def test_the_comparison_structure_is_not_in_the_series(report, atlas):
    """It must hold neither of the series' ligands, or the comparison is with
    itself. Checked against the atlas, not against the artefact's own claim."""
    for pair in report["top_pairs"]:
        persistence = pair.get("persistence") or {}
        pdb_id = persistence.get("widest_without_series_pdb_id")
        if not pdb_id:
            continue
        name_a, name_b = pair["interface"]
        clash = atlas.execute(
            """
            SELECT 1 FROM bridge b WHERE b.pdb_id = ?
              AND b.status = 'ok' AND b.novel_bridge = 1
              AND b.evidence_class = 'molecular_glue'
              AND b.ccd_id IN (
                SELECT DISTINCT ccd_id FROM bridge
                WHERE status = 'ok' AND novel_bridge = 1
                  AND evidence_class = 'molecular_glue'
                  AND pdb_id IN (
                    SELECT pdb_id FROM polymer_entity
                    WHERE substr(trim(name), 1, 48) = ?
                    INTERSECT
                    SELECT pdb_id FROM polymer_entity
                    WHERE substr(trim(name), 1, 48) = ?))
            LIMIT 1
            """, (pdb_id, name_a, name_b)).fetchone()
        assert clash is None, (
            f"{pdb_id} carries a ligand of the series it is the comparison for")


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
