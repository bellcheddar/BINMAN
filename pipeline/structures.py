"""mmCIF loading and atom-group extraction with gemmi.

Turns a biological assembly mmCIF into the two things `pipeline.geometry` needs:
polymer chain instances and non-polymer ligand instances, as flat heavy-atom
coordinate groups.

Three details that matter:

* **The unit of a polymer chain is the subchain, not the auth chain.** In an
  assembly file a ligand often sits inside the auth chain of the protein it
  binds (RAP lives in auth chain A of 1FAP), so splitting on auth chain alone
  would merge a ligand into its own receptor and the bridging test would never
  fire.
* **Symmetry copies are kept and flagged, not dropped** (spec 5.1 criterion 3).
  RCSB names a symmetry-generated chain with a numeric suffix, which is how they
  are detected here.
* **Hydrogens and waters are excluded from the geometry** but waters are still
  counted and reported, because spec 4.3 classifies crystallisation furniture
  rather than deleting it.
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from pathlib import Path

import gemmi

from pipeline.geometry import WATER_NAMES, AtomGroup

# RCSB names a symmetry-generated chain by appending "-<n>" to the auth id.
SYMMETRY_SUFFIX = re.compile(r"-\d+$")

# Single-atom species are classified as metals or ions downstream; they never
# reach the bridging loop because the heavy-atom floor excludes them, but naming
# them here keeps the ligand inventory readable.
HYDROGEN = {"H", "D"}


@dataclass
class LigandInstance:
    """One non-polymer entity instance: a single residue in a non-polymer subchain."""

    label: str            # "<auth_chain>/<subchain>/<ccd>/<seqid>", unique in the assembly
    ccd_id: str
    entity_id: str
    auth_chain: str
    subchain: str
    seq_id: str
    atoms: AtomGroup
    is_symmetry_copy: bool

    @property
    def heavy_atoms(self) -> int:
        return len(self.atoms)


@dataclass
class PolymerUnit:
    """One polymer chain instance in the assembly."""

    label: str            # "<auth_chain>/<subchain>"
    entity_id: str
    auth_chain: str
    subchain: str
    atoms: AtomGroup
    residue_count: int
    is_symmetry_copy: bool


@dataclass
class Assembly:
    """A parsed biological assembly."""

    pdb_id: str
    assembly_id: str
    path: Path
    polymers: list[PolymerUnit] = field(default_factory=list)
    ligands: list[LigandInstance] = field(default_factory=list)
    waters: int = 0
    spacegroup: str = ""
    resolution: float | None = None
    warnings: list[str] = field(default_factory=list)

    def chain_tuples(self) -> list[tuple[str, str, AtomGroup, bool]]:
        """The `chains` argument shape that `geometry.find_bridges` expects."""
        return [(p.label, p.entity_id, p.atoms, p.is_symmetry_copy) for p in self.polymers]

    @property
    def distinct_polymer_entities(self) -> int:
        return len({p.entity_id for p in self.polymers})

    def summary(self) -> dict:
        return {
            "pdb_id": self.pdb_id,
            "assembly_id": self.assembly_id,
            "polymer_units": len(self.polymers),
            "distinct_polymer_entities": self.distinct_polymer_entities,
            "ligand_instances": len(self.ligands),
            "distinct_ccds": len({l.ccd_id for l in self.ligands}),
            "waters": self.waters,
            "symmetry_polymer_units": sum(1 for p in self.polymers if p.is_symmetry_copy),
            "warnings": self.warnings,
        }


def _read_any(path: Path) -> gemmi.Structure:
    """Read a .cif, .cif.gz, .bcif or .pdb path."""
    text_path = str(path)
    if text_path.endswith(".gz"):
        # gemmi reads gzip directly for cif, but go through the raw bytes so a
        # truncated download fails here with a clear message rather than deep in
        # the parser.
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            doc = gemmi.cif.read_string(handle.read())
        return gemmi.make_structure_from_block(doc.sole_block())
    return gemmi.read_structure(text_path)


def is_polymer_residue(residue: gemmi.Residue) -> bool:
    info = gemmi.find_tabulated_residue(residue.name)
    return bool(info and (info.is_amino_acid() or info.is_nucleic_acid()))


def load_assembly(
    path: Path | str,
    pdb_id: str = "",
    assembly_id: str = "1",
    *,
    resolution: float | None = None,
) -> Assembly:
    """Parse an assembly mmCIF into polymer units and ligand instances."""
    path = Path(path)
    structure = _read_any(path)
    structure.setup_entities()
    structure.remove_alternative_conformations()
    structure.remove_hydrogens()

    entity_type_by_subchain: dict[str, gemmi.EntityType] = {}
    entity_id_by_subchain: dict[str, str] = {}
    for entity in structure.entities:
        for subchain in entity.subchains:
            entity_type_by_subchain[subchain] = entity.entity_type
            entity_id_by_subchain[subchain] = entity.name

    assembly = Assembly(
        pdb_id=(pdb_id or structure.name or path.stem).upper().replace("-ASSEMBLY1", ""),
        assembly_id=assembly_id,
        path=path,
        spacegroup=structure.spacegroup_hm or "",
        resolution=resolution if resolution is not None else (structure.resolution or None),
    )
    if len(structure) == 0:
        assembly.warnings.append("no models in file")
        return assembly

    model = structure[0]

    # Group residues by (auth_chain, subchain), which is the real chain instance.
    polymer_groups: dict[tuple[str, str], list[gemmi.Residue]] = {}
    for chain in model:
        for residue in chain:
            subchain = residue.subchain or chain.name
            kind = entity_type_by_subchain.get(subchain)

            if residue.name in WATER_NAMES or kind == gemmi.EntityType.Water:
                assembly.waters += 1
                continue

            is_symmetry = bool(SYMMETRY_SUFFIX.search(chain.name))

            # Treat anything the entity table calls a polymer, plus anything the
            # CCD tabulates as an amino or nucleic acid, as polymer. The second
            # clause rescues files whose entity table is thin.
            if kind == gemmi.EntityType.Polymer or (
                kind is None and is_polymer_residue(residue)
            ):
                polymer_groups.setdefault((chain.name, subchain), []).append(residue)
                continue

            # Everything else is a non-polymer entity instance: one ligand.
            group = AtomGroup(
                label=f"{chain.name}/{subchain}/{residue.name}/{residue.seqid.num}"
            )
            for atom in residue:
                element = atom.element.name
                if element.upper() in HYDROGEN:
                    continue
                group.add(
                    atom.pos.x, atom.pos.y, atom.pos.z, element,
                    f"{residue.name} {residue.seqid.num}", atom.name,
                )
            if len(group) == 0:
                continue
            assembly.ligands.append(LigandInstance(
                label=group.label, ccd_id=residue.name,
                entity_id=entity_id_by_subchain.get(subchain, "?"),
                auth_chain=chain.name, subchain=subchain,
                seq_id=str(residue.seqid.num), atoms=group,
                is_symmetry_copy=is_symmetry,
            ))

    for (auth_chain, subchain), residues in polymer_groups.items():
        group = AtomGroup(label=f"{auth_chain}/{subchain}")
        for residue in residues:
            key = f"{residue.name} {residue.seqid.num}"
            for atom in residue:
                element = atom.element.name
                if element.upper() in HYDROGEN:
                    continue
                group.add(atom.pos.x, atom.pos.y, atom.pos.z, element, key, atom.name)
        if len(group) == 0:
            continue
        assembly.polymers.append(PolymerUnit(
            label=group.label,
            entity_id=entity_id_by_subchain.get(subchain, "?"),
            auth_chain=auth_chain, subchain=subchain, atoms=group,
            residue_count=len(residues),
            is_symmetry_copy=bool(SYMMETRY_SUFFIX.search(auth_chain)),
        ))

    if not assembly.polymers:
        assembly.warnings.append("no polymer chains parsed")
    return assembly


def write_trimmed_assembly(
    source: Path | str,
    dest: Path | str,
    keep_chains: set[str],
    ligand_label: str | None = None,
    radius: float = 8.0,
) -> dict:
    """Write a trimmed, gzipped mmCIF for the viewer (spec 6.4).

    Keeps the named auth chains in full plus every residue within `radius` of
    them, and drops waters. The result is what the droplet serves, so it must be
    small and must still render as a sensible biological unit.

    Builds a fresh structure rather than editing in place: gemmi chains are not
    cleanly replaceable mid-iteration, and a rebuild is both shorter and safer.
    """
    import math

    source, dest = Path(source), Path(dest)
    structure = _read_any(source)
    structure.setup_entities()
    structure.remove_alternative_conformations()
    structure.remove_hydrogens()
    structure.remove_waters()

    if len(structure) == 0:
        raise ValueError(f"{source.name} has no models")
    model = structure[0]

    present = {chain.name for chain in model}
    missing = keep_chains - present
    if missing == keep_chains:
        raise ValueError(
            f"none of {sorted(keep_chains)} present in {source.name} "
            f"(chains: {sorted(present)})"
        )

    # Reference set: every atom of the chains being kept in full.
    cell = radius
    radius_sq = radius * radius
    grid: dict[tuple[int, int, int], list[tuple[float, float, float]]] = {}
    for chain in model:
        if chain.name not in keep_chains:
            continue
        for residue in chain:
            for atom in residue:
                pos = (atom.pos.x, atom.pos.y, atom.pos.z)
                key = (math.floor(pos[0] / cell), math.floor(pos[1] / cell),
                       math.floor(pos[2] / cell))
                grid.setdefault(key, []).append(pos)

    def near_reference(atom_pos) -> bool:
        x, y, z = atom_pos.x, atom_pos.y, atom_pos.z
        cx, cy, cz = math.floor(x / cell), math.floor(y / cell), math.floor(z / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for ox, oy, oz in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        if (ox - x) ** 2 + (oy - y) ** 2 + (oz - z) ** 2 <= radius_sq:
                            return True
        return False

    trimmed = gemmi.Structure()
    trimmed.name = structure.name
    trimmed.spacegroup_hm = structure.spacegroup_hm
    trimmed.cell = structure.cell
    trimmed.resolution = structure.resolution

    new_model = gemmi.Model("1")
    for chain in model:
        new_chain = gemmi.Chain(chain.name)
        full = chain.name in keep_chains
        for residue in chain:
            if full or any(near_reference(atom.pos) for atom in residue):
                new_chain.add_residue(residue)
        if len(new_chain):
            new_model.add_chain(new_chain)
    trimmed.add_model(new_model)
    trimmed.setup_entities()

    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = trimmed.make_mmcif_document().as_string().encode("utf-8")
    with gzip.open(dest, "wb", compresslevel=9) as handle:
        handle.write(raw)

    return {
        "path": str(dest),
        "chains": [c.name for c in new_model],
        "residues": sum(len(c) for c in new_model),
        "bytes_gzipped": dest.stat().st_size,
        "bytes_raw": len(raw),
        "ligand_label": ligand_label or "",
        "trim_radius_a": radius,
        "missing_chains": sorted(missing),
    }
