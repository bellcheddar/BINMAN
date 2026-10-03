"""Bridging ligand geometry (spec 5.1).

A non-polymer entity instance *L* bridges polymer chains *A* and *B* when all of:

1. dSASA buried against *A* >= `bridging.min_dsasa_per_chain_a2` and the same
   against *B*, where dSASA(X) = SASA(L) + SASA(X) - SASA(L + X).
2. At least `bridging.min_heavy_atom_contacts` heavy-atom contacts under
   `bridging.contact_cutoff_a` to each of *A* and *B*.
3. *A* and *B* are distinct polymer entity instances in the same assembly.
4. Ligand heavy-atom count >= `bridging.min_ligand_heavy_atoms`, waived when the
   CCD is already classed `glue_candidate`.

Every cutoff is read from `config/thresholds.toml`. There is no scientific
literal anywhere in this file.

The bridging balance, min(dSASA_A, dSASA_B) / max(dSASA_A, dSASA_B), is the
discriminating quantity: near 1.0 is the signature of a genuine glue, near 0 is
a ligand bound to one chain that happens to graze another.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from pipeline.common import Config, load_config

# Bondi van der Waals radii in Angstrom (J. Phys. Chem. 1964, 68, 441), with the
# later revisions for the halogens and a 2.0 default for anything unlisted.
# freesasa's own classifier needs a PDB file; BINMAN works from coordinate
# arrays, so radii are assigned here by element and the choice is explicit.
VDW_RADII: dict[str, float] = {
    "H": 1.20, "HE": 1.40, "LI": 1.82, "BE": 1.53, "B": 1.92, "C": 1.70,
    "N": 1.55, "O": 1.52, "F": 1.47, "NE": 1.54, "NA": 2.27, "MG": 1.73,
    "AL": 1.84, "SI": 2.10, "P": 1.80, "S": 1.80, "CL": 1.75, "AR": 1.88,
    "K": 2.75, "CA": 2.31, "SC": 2.11, "TI": 1.87, "V": 1.79, "CR": 1.89,
    "MN": 1.97, "FE": 1.94, "CO": 1.92, "NI": 1.84, "CU": 1.86, "ZN": 1.39,
    "GA": 1.87, "GE": 2.11, "AS": 1.85, "SE": 1.90, "BR": 1.85, "KR": 2.02,
    "RB": 3.03, "SR": 2.49, "MO": 2.06, "RU": 2.07, "PD": 2.02, "AG": 1.72,
    "CD": 1.58, "IN": 1.93, "SN": 2.17, "SB": 2.06, "TE": 2.06, "I": 1.98,
    "XE": 2.16, "CS": 3.43, "BA": 2.68, "W": 2.10, "RE": 2.05, "OS": 2.05,
    "IR": 2.04, "PT": 1.75, "AU": 1.66, "HG": 1.55, "TL": 1.96, "PB": 2.02,
    "BI": 2.07, "U": 1.86,
}
DEFAULT_RADIUS = 2.0

# Waters and single-atom ions are never bridging ligands in their own right.
# They are classified rather than deleted (spec 4.3), so this set exists only to
# keep them out of the candidate loop.
WATER_NAMES = {"HOH", "DOD", "WAT", "H2O", "D2O"}


def element_radius(element: str) -> float:
    return VDW_RADII.get(element.strip().upper(), DEFAULT_RADIUS)


# --------------------------------------------------------------------------- #
# atom groups
# --------------------------------------------------------------------------- #

@dataclass
class AtomGroup:
    """Heavy atoms of one structural unit, ready for SASA and contact work."""

    label: str
    coords: list[float] = field(default_factory=list)   # flat x,y,z triples
    radii: list[float] = field(default_factory=list)
    elements: list[str] = field(default_factory=list)
    residue_keys: list[str] = field(default_factory=list)  # "<resname> <seqid>"
    atom_names: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.radii)

    def add(self, x: float, y: float, z: float, element: str,
            residue_key: str, atom_name: str) -> None:
        self.coords.extend((float(x), float(y), float(z)))
        self.radii.append(element_radius(element))
        self.elements.append(element.strip().upper())
        self.residue_keys.append(residue_key)
        self.atom_names.append(atom_name)

    def xyz(self, index: int) -> tuple[float, float, float]:
        base = 3 * index
        return self.coords[base], self.coords[base + 1], self.coords[base + 2]


def merge(*groups: AtomGroup) -> AtomGroup:
    out = AtomGroup(label="+".join(g.label for g in groups))
    for group in groups:
        out.coords.extend(group.coords)
        out.radii.extend(group.radii)
        out.elements.extend(group.elements)
        out.residue_keys.extend(group.residue_keys)
        out.atom_names.extend(group.atom_names)
    return out


# --------------------------------------------------------------------------- #
# SASA
# --------------------------------------------------------------------------- #

class SasaCalculator:
    """FreeSASA over coordinate arrays, with the spec's parameters and a cache.

    SASA(chain) is recomputed once per chain and reused across every ligand in
    the assembly, which is where the saving is: a 12-chain assembly with 30
    ligands would otherwise repeat the expensive half of the calculation 360
    times.
    """

    def __init__(self, config: Config | None = None) -> None:
        import freesasa

        config = config or load_config()
        algorithm = str(config.t("bridging.sasa_algorithm"))
        probe = float(config.t("bridging.sasa_probe_radius_a"))
        known = {"LeeRichards": freesasa.LeeRichards, "ShrakeRupley": freesasa.ShrakeRupley}
        if algorithm not in known:
            raise ValueError(
                f"bridging.sasa_algorithm must be one of {sorted(known)}, got {algorithm!r}"
            )
        self._freesasa = freesasa
        self._params = freesasa.Parameters(
            {"algorithm": known[algorithm], "probe-radius": probe}
        )
        self._cache: dict[str, float] = {}
        self._atom_cache: dict[str, list[float]] = {}

    def total(self, group: AtomGroup, cache_key: str | None = None) -> float:
        """Total SASA of a group, in Angstrom^2."""
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]
        if len(group) == 0:
            return 0.0
        result = self._freesasa.calcCoord(group.coords, group.radii, self._params)
        total = float(result.totalArea())
        if cache_key is not None:
            self._cache[cache_key] = total
        return total

    def per_atom(self, group: AtomGroup, cache_key: str | None = None) -> list[float]:
        """Per-atom SASA, needed for the ligand's buried fraction and for lysines."""
        if cache_key is not None and cache_key in self._atom_cache:
            return self._atom_cache[cache_key]
        if len(group) == 0:
            return []
        result = self._freesasa.calcCoord(group.coords, group.radii, self._params)
        areas = [float(result.atomArea(i)) for i in range(result.nAtoms())]
        if cache_key is not None:
            self._atom_cache[cache_key] = areas
        return areas

    def delta(self, ligand: AtomGroup, chain: AtomGroup,
              ligand_key: str, chain_key: str) -> float:
        """dSASA(X) = SASA(L) + SASA(X) - SASA(L + X), the spec 5.1 definition.

        This is the total interface area (both sides of the contact), not the
        ligand-side area alone. The 25 A^2 floor in thresholds.toml is stated in
        this convention.
        """
        sasa_l = self.total(ligand, ligand_key)
        sasa_x = self.total(chain, chain_key)
        sasa_lx = self.total(merge(ligand, chain))
        return sasa_l + sasa_x - sasa_lx


# --------------------------------------------------------------------------- #
# contacts
# --------------------------------------------------------------------------- #

def _cell_key(x: float, y: float, z: float, size: float) -> tuple[int, int, int]:
    return (math.floor(x / size), math.floor(y / size), math.floor(z / size))


class ContactGrid:
    """Uniform-grid neighbour search over one chain's heavy atoms.

    gemmi ships a NeighborSearch, but it is tied to a gemmi Structure and BINMAN
    needs contacts between arbitrary atom groups (including trimmed and
    symmetry-expanded ones), so the grid is built here over plain coordinates.
    Cell size is the contact cutoff, so a query touches 27 cells at most.
    """

    def __init__(self, group: AtomGroup, cutoff: float) -> None:
        self.group = group
        self.cutoff = cutoff
        self.cutoff_sq = cutoff * cutoff
        self._cells: dict[tuple[int, int, int], list[int]] = {}
        for index in range(len(group)):
            x, y, z = group.xyz(index)
            self._cells.setdefault(_cell_key(x, y, z, cutoff), []).append(index)

    def neighbours(self, x: float, y: float, z: float) -> Iterable[int]:
        cx, cy, cz = _cell_key(x, y, z, self.cutoff)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for index in self._cells.get((cx + dx, cy + dy, cz + dz), ()):
                        ax, ay, az = self.group.xyz(index)
                        if (ax - x) ** 2 + (ay - y) ** 2 + (az - z) ** 2 <= self.cutoff_sq:
                            yield index


@dataclass
class ContactResult:
    count: int
    interface_residues: list[str]
    min_distance: float


def count_contacts(ligand: AtomGroup, chain_grid: ContactGrid) -> ContactResult:
    """Heavy-atom contacts from a ligand to one chain, plus the interface residues."""
    total = 0
    residues: dict[str, None] = {}
    closest = float("inf")
    for index in range(len(ligand)):
        x, y, z = ligand.xyz(index)
        for hit in chain_grid.neighbours(x, y, z):
            total += 1
            residues[chain_grid.group.residue_keys[hit]] = None
            ax, ay, az = chain_grid.group.xyz(hit)
            distance = math.dist((x, y, z), (ax, ay, az))
            closest = min(closest, distance)
    return ContactResult(
        count=total,
        interface_residues=list(residues),
        min_distance=round(closest, 3) if total else float("inf"),
    )


# --------------------------------------------------------------------------- #
# the bridging test
# --------------------------------------------------------------------------- #

def bridging_balance(dsasa_a: float, dsasa_b: float) -> float:
    """min/max of the two buried areas. 0.0 when either side is non-positive."""
    if dsasa_a <= 0 or dsasa_b <= 0:
        return 0.0
    return round(min(dsasa_a, dsasa_b) / max(dsasa_a, dsasa_b), 4)


@dataclass
class ChainContact:
    """One ligand-to-chain half-interface."""

    chain_label: str
    entity_id: str
    dsasa: float
    contacts: int
    interface_residues: list[str]
    min_distance: float

    def passes(self, min_dsasa: float, min_contacts: int) -> bool:
        return self.dsasa >= min_dsasa and self.contacts >= min_contacts


@dataclass
class Bridge:
    """One row of the Glue Atlas: a ligand instance against a chain pair."""

    ligand_label: str
    ccd_id: str
    chain_a: str
    chain_b: str
    entity_a: str
    entity_b: str
    dsasa_a: float
    dsasa_b: float
    dsasa_total: float
    contacts_a: int
    contacts_b: int
    bridging_balance: float
    buried_fraction: float
    interface_residues_a: list[str]
    interface_residues_b: list[str]
    symmetry_mediated: bool
    heavy_atoms: int

    def as_row(self) -> dict:
        return {
            "ligand_label": self.ligand_label, "ccd_id": self.ccd_id,
            "chain_a": self.chain_a, "chain_b": self.chain_b,
            "entity_a": self.entity_a, "entity_b": self.entity_b,
            "dsasa_a": round(self.dsasa_a, 2), "dsasa_b": round(self.dsasa_b, 2),
            "dsasa_total": round(self.dsasa_total, 2),
            "contacts_a": self.contacts_a, "contacts_b": self.contacts_b,
            "bridging_balance": self.bridging_balance,
            "buried_fraction": round(self.buried_fraction, 4),
            "interface_residues_a": self.interface_residues_a,
            "interface_residues_b": self.interface_residues_b,
            "symmetry_mediated": int(self.symmetry_mediated),
            "heavy_atoms": self.heavy_atoms,
        }


def find_bridges(
    ligand: AtomGroup,
    ccd_id: str,
    chains: Sequence[tuple[str, str, AtomGroup, bool]],
    *,
    config: Config | None = None,
    sasa: SasaCalculator | None = None,
    is_glue_candidate: bool = False,
) -> tuple[list[Bridge], list[ChainContact], str]:
    """Test one ligand instance against every polymer chain in an assembly.

    `chains` is a sequence of (chain_label, entity_id, atoms, is_symmetry_copy).

    Returns the bridges found, every half-interface considered (so a near miss
    can be reported in the misses list), and a reject reason when the ligand
    never reached the pair stage.
    """
    config = config or load_config()
    sasa = sasa or SasaCalculator(config)

    min_dsasa = float(config.t("bridging.min_dsasa_per_chain_a2"))
    min_contacts = int(config.t("bridging.min_heavy_atom_contacts"))
    cutoff = float(config.t("bridging.contact_cutoff_a"))
    min_heavy = int(config.t("bridging.min_ligand_heavy_atoms"))

    heavy_atoms = len(ligand)
    # Criterion 4: the size floor, waived for a known glue CCD.
    if heavy_atoms < min_heavy and not is_glue_candidate:
        return [], [], f"too_small:{heavy_atoms}<{min_heavy}"

    ligand_key = f"lig:{ligand.label}"
    half_interfaces: list[ChainContact] = []

    for chain_label, entity_id, atoms, _is_symmetry in chains:
        if len(atoms) == 0:
            continue
        grid = ContactGrid(atoms, cutoff)
        contact = count_contacts(ligand, grid)
        # Criterion 2 gates the expensive step: no contacts means no dSASA call.
        if contact.count == 0:
            continue
        dsasa = sasa.delta(ligand, atoms, ligand_key, f"chain:{chain_label}")
        half_interfaces.append(ChainContact(
            chain_label=chain_label, entity_id=entity_id, dsasa=dsasa,
            contacts=contact.count, interface_residues=contact.interface_residues,
            min_distance=contact.min_distance,
        ))

    qualifying = [h for h in half_interfaces if h.passes(min_dsasa, min_contacts)]
    if len(qualifying) < 2:
        reason = f"single_chain:{len(qualifying)}_qualifying_of_{len(half_interfaces)}"
        return [], half_interfaces, reason

    # Buried fraction of the ligand, measured against every chain it touches at
    # once rather than chain by chain, so a ligand in a deep multi-chain pocket
    # does not report a fraction above 1.
    contacted = merge(*[
        atoms for chain_label, _entity, atoms, _sym in chains
        if any(h.chain_label == chain_label for h in half_interfaces)
    ]) if half_interfaces else AtomGroup("none")
    sasa_ligand_alone = sasa.total(ligand, ligand_key)
    if sasa_ligand_alone > 0 and len(contacted):
        complex_atoms = merge(ligand, contacted)
        areas = sasa.per_atom(complex_atoms)
        ligand_in_complex = sum(areas[: len(ligand)])
        buried_fraction = max(0.0, (sasa_ligand_alone - ligand_in_complex) / sasa_ligand_alone)
    else:
        buried_fraction = 0.0

    symmetry_by_label = {
        chain_label: is_symmetry for chain_label, _e, _a, is_symmetry in chains
    }

    bridges: list[Bridge] = []
    for i in range(len(qualifying)):
        for j in range(i + 1, len(qualifying)):
            left, right = qualifying[i], qualifying[j]
            # Criterion 3: distinct polymer entity instances. Two copies of the
            # same chain are distinct instances and do count; the same chain
            # cannot pair with itself.
            if left.chain_label == right.chain_label:
                continue
            bridges.append(Bridge(
                ligand_label=ligand.label, ccd_id=ccd_id,
                chain_a=left.chain_label, chain_b=right.chain_label,
                entity_a=left.entity_id, entity_b=right.entity_id,
                dsasa_a=left.dsasa, dsasa_b=right.dsasa,
                dsasa_total=left.dsasa + right.dsasa,
                contacts_a=left.contacts, contacts_b=right.contacts,
                bridging_balance=bridging_balance(left.dsasa, right.dsasa),
                buried_fraction=buried_fraction,
                interface_residues_a=left.interface_residues,
                interface_residues_b=right.interface_residues,
                symmetry_mediated=bool(
                    symmetry_by_label.get(left.chain_label)
                    or symmetry_by_label.get(right.chain_label)
                ),
                heavy_atoms=heavy_atoms,
            ))
    return bridges, half_interfaces, ""
