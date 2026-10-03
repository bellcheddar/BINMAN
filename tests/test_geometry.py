"""Geometry against hand-computed cases (spec 10).

Every expected value here is derived analytically rather than copied from a run,
so these tests can fail. Two isolated spheres of radius r have total SASA
2 * 4 * pi * (r + probe)^2 exactly, which is the anchor for the whole SASA path.
"""

from __future__ import annotations

import math

import pytest

from pipeline.geometry import (
    AtomGroup, ContactGrid, SasaCalculator, bridging_balance, count_contacts,
    element_radius, find_bridges, merge,
)


def test_element_radii_are_bondi():
    assert element_radius("C") == pytest.approx(1.70)
    assert element_radius("N") == pytest.approx(1.55)
    assert element_radius("O") == pytest.approx(1.52)
    assert element_radius("Zn") == pytest.approx(1.39)
    # Case-insensitive, and an unknown element falls back rather than raising.
    assert element_radius("zn") == element_radius("ZN")
    assert element_radius("Xx") == pytest.approx(2.0)


def test_sasa_of_two_isolated_atoms_matches_the_analytic_sphere(config):
    """SASA of two far-apart carbons is exactly two full probe-expanded spheres."""
    calculator = SasaCalculator(config)
    group = AtomGroup("pair")
    group.add(0, 0, 0, "C", "LIG 1", "C1")
    group.add(50, 0, 0, "C", "LIG 1", "C2")

    probe = float(config.t("bridging.sasa_probe_radius_a"))
    expected = 2 * 4 * math.pi * (1.70 + probe) ** 2
    # Lee-Richards slices the sphere, so allow a small discretisation error.
    assert calculator.total(group) == pytest.approx(expected, rel=0.01)


def test_sasa_decreases_when_atoms_overlap(config):
    calculator = SasaCalculator(config)
    apart = AtomGroup("apart")
    apart.add(0, 0, 0, "C", "LIG 1", "C1")
    apart.add(50, 0, 0, "C", "LIG 1", "C2")
    close = AtomGroup("close")
    close.add(0, 0, 0, "C", "LIG 1", "C1")
    close.add(1.5, 0, 0, "C", "LIG 1", "C2")
    assert calculator.total(close) < calculator.total(apart)


def test_delta_sasa_is_zero_for_non_interacting_groups(config):
    """dSASA = SASA(L) + SASA(X) - SASA(L+X) must vanish when nothing touches."""
    calculator = SasaCalculator(config)
    ligand = AtomGroup("lig")
    ligand.add(0, 0, 0, "C", "LIG 1", "C1")
    chain = AtomGroup("chain")
    chain.add(100, 0, 0, "C", "ALA 1", "CA")
    assert calculator.delta(ligand, chain, "lig", "chain") == pytest.approx(0.0, abs=1e-6)


def test_delta_sasa_is_positive_and_symmetric_for_touching_groups(config):
    calculator = SasaCalculator(config)
    ligand = AtomGroup("lig")
    ligand.add(0, 0, 0, "C", "LIG 1", "C1")
    chain = AtomGroup("chain")
    chain.add(3.0, 0, 0, "C", "ALA 1", "CA")
    delta = calculator.delta(ligand, chain, "lig", "chain")
    assert delta > 0
    # The quantity is defined symmetrically, so swapping the arguments must not
    # change it.
    swapped = calculator.delta(chain, ligand, "chain", "lig")
    assert delta == pytest.approx(swapped, rel=1e-9)


def test_contact_grid_counts_only_within_the_cutoff():
    chain = AtomGroup("chain")
    chain.add(0, 0, 0, "C", "ALA 1", "CA")       # 2.0 A away: inside
    chain.add(3.9, 0, 0, "C", "ALA 2", "CA")     # 1.9 A away: inside
    chain.add(20, 0, 0, "C", "ALA 3", "CA")      # far: outside
    ligand = AtomGroup("lig")
    ligand.add(2.0, 0, 0, "C", "LIG 1", "C1")

    grid = ContactGrid(chain, 4.0)
    result = count_contacts(ligand, grid)
    assert result.count == 2
    assert set(result.interface_residues) == {"ALA 1", "ALA 2"}
    assert result.min_distance == pytest.approx(1.9, abs=1e-6)


def test_contact_grid_boundary_is_inclusive():
    chain = AtomGroup("chain")
    chain.add(4.0, 0, 0, "C", "ALA 1", "CA")
    ligand = AtomGroup("lig")
    ligand.add(0, 0, 0, "C", "LIG 1", "C1")
    assert count_contacts(ligand, ContactGrid(chain, 4.0)).count == 1
    assert count_contacts(ligand, ContactGrid(chain, 3.99)).count == 0


def test_bridging_balance_is_min_over_max():
    assert bridging_balance(100.0, 100.0) == 1.0
    assert bridging_balance(50.0, 100.0) == 0.5
    assert bridging_balance(100.0, 50.0) == 0.5    # symmetric
    assert bridging_balance(0.0, 100.0) == 0.0
    assert bridging_balance(-5.0, 100.0) == 0.0


def test_merge_concatenates_every_parallel_array():
    a = AtomGroup("a")
    a.add(0, 0, 0, "C", "ALA 1", "CA")
    b = AtomGroup("b")
    b.add(1, 1, 1, "N", "GLY 2", "N")
    merged = merge(a, b)
    assert len(merged) == 2
    assert merged.elements == ["C", "N"]
    assert merged.residue_keys == ["ALA 1", "GLY 2"]
    assert merged.atom_names == ["CA", "N"]
    assert merged.xyz(1) == (1.0, 1.0, 1.0)


def test_ligand_below_the_size_floor_is_rejected(config):
    """A one-atom ligand must be rejected on criterion 4, not silently pass."""
    ligand = AtomGroup("small")
    ligand.add(0, 0, 0, "ZN", "ZN 1", "ZN")
    chain_a = AtomGroup("A")
    chain_a.add(2.0, 0, 0, "C", "ALA 1", "CA")
    chain_b = AtomGroup("B")
    chain_b.add(-2.0, 0, 0, "C", "ALA 1", "CA")

    bridges, _halves, reason = find_bridges(
        ligand, "ZN", [("A", "1", chain_a, False), ("B", "2", chain_b, False)],
        config=config,
    )
    assert bridges == []
    assert reason.startswith("too_small")


def test_single_chain_contact_is_not_a_bridge(config):
    """A ligand touching one chain reports a reason, not a bridge."""
    ligand = AtomGroup("lig")
    for index in range(12):
        ligand.add(index * 1.4, 0, 0, "C", "LIG 1", f"C{index}")
    chain_a = AtomGroup("A")
    for index in range(40):
        chain_a.add(index * 1.4, 3.2, 0, "C", f"ALA {index}", "CA")

    bridges, halves, reason = find_bridges(
        ligand, "XXX", [("A", "1", chain_a, False)], config=config,
    )
    assert bridges == []
    assert reason.startswith("single_chain")
    assert len(halves) == 1


def test_symmetry_flag_propagates_to_the_bridge(config):
    """A bridge involving a symmetry copy must be flagged, not dropped."""
    ligand = AtomGroup("lig")
    for index in range(14):
        ligand.add(index * 1.4, 0, 0, "C", "LIG 1", f"C{index}")
    chain_a = AtomGroup("A")
    chain_b = AtomGroup("B-2")
    for index in range(40):
        chain_a.add(index * 1.4, 3.2, 0, "C", f"ALA {index}", "CA")
        chain_b.add(index * 1.4, -3.2, 0, "C", f"ALA {index}", "CA")

    bridges, _halves, _reason = find_bridges(
        ligand, "XXX",
        [("A", "1", chain_a, False), ("B-2", "1", chain_b, True)],
        config=config,
    )
    assert bridges, "a ligand buried between two chains should bridge"
    assert bridges[0].symmetry_mediated is True
