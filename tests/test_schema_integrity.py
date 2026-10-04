"""Schema integrity and science sanity against the built atlas (spec 10).

These are the tests that stop a regression introduced while building the serving
bundle from hiding: they run against the database the app actually reads.
"""

from __future__ import annotations

import json
import sqlite3

import pytest


def test_every_expected_table_exists(atlas):
    present = {
        row[0] for row in atlas.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    for table in ("entry", "ligand", "polymer_entity", "bridge", "degron",
                  "ligase", "lysine", "edge", "provenance"):
        assert table in present


def test_no_orphan_foreign_keys(atlas):
    """A bridge must point at an entry and a ligand that exist."""
    orphan_entries = atlas.execute(
        "SELECT COUNT(*) FROM bridge b LEFT JOIN entry e ON e.pdb_id = b.pdb_id "
        "WHERE e.pdb_id IS NULL").fetchone()[0]
    assert orphan_entries == 0

    orphan_ligands = atlas.execute(
        "SELECT COUNT(*) FROM bridge b LEFT JOIN ligand l ON l.ccd_id = b.ccd_id "
        "WHERE l.ccd_id IS NULL").fetchone()[0]
    assert orphan_ligands == 0


def test_every_status_value_is_parseable(atlas):
    """`status` is either 'ok' or 'failed:<reason>' with a non-empty reason."""
    for table in ("entry", "ligand", "bridge", "degron", "ligase", "lysine", "edge"):
        rows = atlas.execute(
            f"SELECT DISTINCT status FROM {table}").fetchall()
        for (status,) in rows:
            if status is None:
                continue
            assert status == "ok" or status.startswith("failed:"), (
                f"{table}.status = {status!r} is neither ok nor failed:<reason>")
            if status.startswith("failed:"):
                assert len(status) > len("failed:"), (
                    f"{table} has a failure with no reason")


def test_no_alpha_value_without_a_source(atlas):
    """Cooperativity is not computable from a structure (spec 5.1)."""
    bad = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE alpha IS NOT NULL "
        "AND (alpha_source IS NULL OR alpha_source = '')").fetchone()[0]
    assert bad == 0, "an alpha value exists with no alpha_source"


def test_bridging_balance_is_within_range(atlas):
    out_of_range = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE bridging_balance IS NOT NULL "
        "AND (bridging_balance < 0 OR bridging_balance > 1)").fetchone()[0]
    assert out_of_range == 0


def test_buried_fraction_is_within_range(atlas):
    out_of_range = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE buried_fraction IS NOT NULL "
        "AND (buried_fraction < 0 OR buried_fraction > 1.0001)").fetchone()[0]
    assert out_of_range == 0


def test_balance_equals_min_over_max_of_the_two_areas(atlas):
    """The stored balance must be derivable from the stored areas."""
    rows = atlas.execute(
        "SELECT dsasa_a, dsasa_b, bridging_balance FROM bridge "
        "WHERE status = 'ok' AND dsasa_a > 0 AND dsasa_b > 0 LIMIT 500").fetchall()
    if not rows:
        pytest.skip("no bridges yet")
    for dsasa_a, dsasa_b, balance in rows:
        expected = min(dsasa_a, dsasa_b) / max(dsasa_a, dsasa_b)
        assert balance == pytest.approx(expected, abs=1e-3)


def test_both_half_interfaces_clear_the_dsasa_floor(atlas, config):
    """Criterion 1: every bridge buries at least the floor against BOTH chains."""
    floor = float(config.t("bridging.min_dsasa_per_chain_a2"))
    below = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND (dsasa_a < ? OR dsasa_b < ?)",
        (floor, floor)).fetchone()[0]
    assert below == 0, f"a bridge buries less than {floor} A^2 against a chain"


def test_both_half_interfaces_clear_the_contact_floor(atlas, config):
    floor = int(config.t("bridging.min_heavy_atom_contacts"))
    below = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok' "
        "AND (contacts_a < ? OR contacts_b < ?)", (floor, floor)).fetchone()[0]
    assert below == 0


def test_a_bridge_never_pairs_a_chain_with_itself(atlas):
    self_paired = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE chain_a = chain_b").fetchone()[0]
    assert self_paired == 0


def test_interface_residue_lists_are_valid_json(atlas):
    rows = atlas.execute(
        "SELECT interface_residues_a, interface_residues_b FROM bridge LIMIT 400"
    ).fetchall()
    for left, right in rows:
        for blob in (left, right):
            if blob:
                parsed = json.loads(blob)
                assert isinstance(parsed, list)


def test_no_verdict_exists_while_the_reach_window_is_unfitted(atlas, config):
    """Spec 5.4 forbids shipping the unfitted starting values as verdicts."""
    if config.t("degradability.reach_window.fitted"):
        pytest.skip("the window has been fitted")
    with_verdict = atlas.execute(
        "SELECT COUNT(*) FROM lysine WHERE verdict IS NOT NULL").fetchone()[0]
    assert with_verdict == 0, (
        "verdicts exist although the reach window is unfitted; the spec 1.0 "
        "starting values must not reach the atlas"
    )


def test_ligand_class_is_always_one_of_the_declared_classes(atlas):
    from pipeline.ccd_classes import CLASSES

    classes = {row[0] for row in atlas.execute(
        "SELECT DISTINCT ccd_class FROM ligand WHERE ccd_class IS NOT NULL")}
    assert classes <= set(CLASSES), f"unexpected classes: {classes - set(CLASSES)}"


def test_provenance_exists_for_the_derived_tables(atlas):
    tables = {row[0] for row in atlas.execute(
        "SELECT DISTINCT table_name FROM provenance")}
    assert {"bridge", "ligand", "entry"} <= tables


def test_ui_bridge_count_equals_the_database_count(atlas):
    """Spec 10: the number of bridges in the UI equals the number in the database."""
    from app import create_app

    direct = atlas.execute(
        "SELECT COUNT(*) FROM bridge WHERE status = 'ok'").fetchone()[0]
    app = create_app()
    with app.test_client() as client:
        payload = client.get("/api/health").get_json()
    assert payload["counts"]["bridge"] == direct


def test_no_third_party_dataset_rows_are_bundled_in_the_atlas(atlas):
    """Spec 10: a licence-restricted dataset must not be inside the shipped atlas."""
    tables = {row[0] for row in atlas.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    forbidden = {"biolip", "biolip2_annotations", "protacdb", "ubibrowser",
                 "mgdb", "molgluedb", "degronopedia", "phosphositeplus"}
    assert not (tables & forbidden), f"third-party rows bundled: {tables & forbidden}"


def test_zinc_finger_table_is_consistent_with_the_degron_table(atlas):
    """The per-finger table must not contradict the per-candidate one.

    `zinc_finger` exists because `degron.imid_degradation_score` is per hairpin
    candidate and could not reach a protein's degron finger when the geometry
    scan placed no candidate there (D-052, D-055). The two must still agree on
    the facts they share.
    """
    present = {
        row[0] for row in atlas.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "zinc_finger" not in present:
        pytest.skip("zinc_finger has not been built")

    total = atlas.execute("SELECT COUNT(*) FROM zinc_finger").fetchone()[0]
    assert total > 0

    # Every score is a probability.
    assert atlas.execute(
        "SELECT COUNT(*) FROM zinc_finger WHERE imid_degradation_score IS NOT NULL "
        "AND (imid_degradation_score < 0 OR imid_degradation_score > 1)"
    ).fetchone()[0] == 0

    # Every finger has a sane window and a fixed-width anchored core.
    assert atlas.execute(
        "SELECT COUNT(*) FROM zinc_finger WHERE zf_end <= zf_start").fetchone()[0] == 0
    assert atlas.execute(
        "SELECT COUNT(DISTINCT LENGTH(core)) FROM zinc_finger").fetchone()[0] == 1

    # `screen_degraded` is a three-state label: 1, 0, or NULL for never
    # assayed. A 0 standing in for "unknown" would read as a matched negative.
    assert atlas.execute(
        "SELECT COUNT(*) FROM zinc_finger WHERE screen_degraded NOT IN (0, 1)"
    ).fetchone()[0] == 0

    # has_degron_candidate must agree with the degron table it was derived from.
    disagreements = atlas.execute(
        "SELECT COUNT(*) FROM zinc_finger z WHERE z.has_degron_candidate = 1 "
        "AND NOT EXISTS (SELECT 1 FROM degron d WHERE d.uniprot_acc = z.uniprot_acc "
        "AND d.status = 'ok' AND d.start_res <= z.zf_end AND d.end_res >= z.zf_start)"
    ).fetchone()[0]
    assert disagreements == 0


def test_the_two_degron_fingers_the_scan_missed_are_now_scored(atlas):
    """D-052's two coverage misses must stay closed.

    ZNF653 and ZNF692 are pomalidomide substrates whose per-candidate rows
    scored 0.106 and 0.046 because the hairpin scan never landed on their
    degron finger. If this regresses, the per-finger table has stopped doing
    the one job it was added for.
    """
    present = {
        row[0] for row in atlas.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "zinc_finger" not in present:
        pytest.skip("zinc_finger has not been built")

    for gene, start, end in (("ZNF653", 556, 578), ("ZNF692", 417, 439)):
        best = atlas.execute(
            "SELECT MAX(imid_degradation_score) FROM zinc_finger "
            "WHERE gene = ? AND zf_start <= ? AND zf_end >= ?",
            (gene, end, start)).fetchone()[0]
        assert best is not None, f"{gene} degron finger is not in the table"
        assert best > 0.9, f"{gene} degron finger scores only {best}"


def test_known_neosubstrates_are_actually_marked(atlas):
    """A boolean column that is false for every row is a claim, not a default.

    `degron.is_known_neosubstrate` shipped as 0 for all 21,717 rows and had
    never been populated, so the UI tile read "0 known neosubstrates" about a
    proteome containing IKZF1, IKZF3, ZFP91 and SALL4 (D-058). It is written
    from the two screens the repository carries. If it goes back to all-zero,
    that is the same defect returning.
    """
    marked = atlas.execute(
        "SELECT COUNT(*) FROM degron WHERE is_known_neosubstrate = 1").fetchone()[0]
    assert marked > 0, "no degron row is marked as a known neosubstrate"

    # The canonical substrates must be among them, by gene.
    genes = {
        row[0] for row in atlas.execute(
            "SELECT DISTINCT gene FROM degron WHERE is_known_neosubstrate = 1")
    }
    for gene in ("IKZF1", "IKZF3", "ZFP91"):
        assert gene in genes, f"{gene} is not marked as a known neosubstrate"

    # And the flag is a strict boolean, never NULL.
    assert atlas.execute(
        "SELECT COUNT(*) FROM degron WHERE is_known_neosubstrate NOT IN (0, 1)"
    ).fetchone()[0] == 0
