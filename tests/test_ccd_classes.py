"""Chemical classification (spec 4.3, 9.1)."""

from __future__ import annotations

import pytest

from pipeline.ccd_classes import (
    CLASSES, FURNITURE_CLASSES, classify, heavy_atoms_from_formula,
)
from pipeline.chem_rules import structural_class


@pytest.mark.parametrize("formula,expected", [
    ("C51 H79 N O13", 65),      # rapamycin: 51 + 1 + 13
    ("C3 H8 O3", 6),            # glycerol
    ("Zn", 1),
    ("O4 S", 5),
    ("C34 H32 Fe N4 O4", 43),
    ("", None),
])
def test_heavy_atom_counting(formula, expected):
    assert heavy_atoms_from_formula(formula) == expected


def test_hydrogen_and_deuterium_never_count_as_heavy():
    assert heavy_atoms_from_formula("H2 O") == 1
    assert heavy_atoms_from_formula("D2 O") == 1


@pytest.mark.parametrize("ccd,name,formula,expected", [
    ("ZN", "ZINC ION", "Zn 2", "metal"),
    ("GOL", "GLYCEROL", "C3 H8 O3", "cryoprotectant"),
    ("EPE", "HEPES", "C8 H18 N2 O4 S", "buffer"),
    ("SO4", "SULFATE ION", "O4 S", "buffer"),
    ("HEM", "PROTOPORPHYRIN IX CONTAINING FE", "C34 H32 Fe N4 O4", "cofactor"),
    ("NAG", "2-acetamido-2-deoxy-beta-D-glucopyranose", "C8 H15 N O6", "sugar"),
    ("ATP", "ADENOSINE-5'-TRIPHOSPHATE", "C10 H16 N5 O13 P3", "cofactor"),
    ("LDA", "LAURYL DIMETHYLAMINE-N-OXIDE", "C14 H31 N O", "detergent"),
    ("MSE", "SELENOMETHIONINE", "C5 H11 N O2 Se", "covalent_modifier"),
])
def test_seeded_classes(ccd, name, formula, expected):
    result = classify(ccd, name=name, formula=formula,
                      heavy_atoms=heavy_atoms_from_formula(formula))
    assert result.ccd_class == expected
    assert result.rule, "every classification must record which rule fired"


def test_a_drug_like_ligand_is_a_glue_candidate():
    result = classify("RAP", name="RAPAMYCIN IMMUNOSUPPRESSANT DRUG",
                      formula="C51 H79 N O13", heavy_atoms=65)
    assert result.ccd_class == "glue_candidate"


def test_every_class_returned_is_in_the_declared_set():
    cases = [("ZN", "Zn"), ("GOL", "C3 H8 O3"), ("XYZ", "C25 H30 N4 O3"), ("Q", "")]
    for ccd, formula in cases:
        result = classify(ccd, formula=formula,
                          heavy_atoms=heavy_atoms_from_formula(formula))
        assert result.ccd_class in CLASSES


def test_furniture_set_is_a_subset_of_the_declared_classes():
    assert FURNITURE_CLASSES <= set(CLASSES)


@pytest.mark.parametrize("smiles,expected", [
    # A PEG oligomer named nothing like a PEG must still classify from structure.
    ("OCCOCCOCCOCCOCCOCCOCCO", "cryoprotectant"),
    # A phosphocholine lipid.
    ("CCCCCCCCCCCCCCCC(=O)OCC(COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC", "lipid"),
    # A long alkane.
    ("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", "lipid"),
    # A glycoside detergent.
    ("CCCCCCCCOC1OC(CO)C(O)C(O)C1O", "detergent"),
    # Spermidine, a routine additive.
    ("NCCCNCCCCN", "buffer"),
])
def test_structural_rules_classify_from_structure_alone(smiles, expected):
    result = structural_class(smiles)
    assert result is not None, f"no structural rule fired for {smiles}"
    assert result[0] == expected


def test_a_drug_like_molecule_triggers_no_structural_furniture_rule():
    """The structural rules must not claim a real ligand is furniture."""
    # Nevirapine.
    assert structural_class("CC1=CC=CN2C1=NC(=O)C3=C(N=CC=C3)N2C4CC4") is None
    # Imatinib.
    assert structural_class(
        "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"
    ) is None


def test_structure_is_consulted_before_name():
    """A systematically named PEG is caught by structure, not by its name."""
    result = classify("XPG", name="3,6,9,12,15-pentaoxanonadecan-1-ol",
                      formula="C14 H30 O6", heavy_atoms=20,
                      smiles="OCCOCCOCCOCCOCCOCCCC")
    assert result.ccd_class == "cryoprotectant"
    assert result.rule.startswith("structure:")


def test_classify_takes_no_artefact_list_argument():
    """Spec 9.1 depends on the BioLiP artefact list being held out (D-007)."""
    import inspect

    parameters = set(inspect.signature(classify).parameters)
    for forbidden in ("artefacts", "artefact_list", "biolip", "biolip_artefacts"):
        assert forbidden not in parameters, (
            "the artefact list must not be an input to classification, or spec 9.1 "
            "measures a lookup rather than a classifier"
        )
