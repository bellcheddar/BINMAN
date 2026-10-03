"""Structural classification rules over SMILES, using RDKit.

Name matching cannot carry this job. A PEG oligomer is deposited as "PEG", as
"DI(HYDROXYETHYL)ETHER" and as "3,6,9,12,15,18,21,24,27-nonaoxaheptatriacontan-
1-ol"; a phosphatidylcholine appears both as "1,2-DIACYL-SN-GLYCERO-3-
PHOSHOCHOLINE" (with the typo) and as "(7R,17E)-4-HYDROXY-N,N,N,7-TETRAMETHYL-
7-[(8E)-OCTADEC-8-ENOYLOXY]...". The chemistry is identical in each case and the
string is not.

These rules therefore work on the structure. Each is a general statement about a
chemical class, not a list of codes, so they transfer to components the author
never saw. Every rule returns the class it claims plus a short reason, which is
written into `ccd_classes.tsv` so any row can be audited.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

# SMARTS patterns, compiled once. Keys are referenced by the rules below.
_SMARTS: dict[str, str] = {
    # two or more ethylene-oxide repeats: the PEG and glyme family
    "peg_repeat": "[OX2;!$(O=*)]CC[OX2;!$(O=*)]CC[OX2;!$(O=*)]",
    # a carboxylic ester, the glycerolipid and wax linkage
    "ester": "[CX3](=O)[OX2H0][#6]",
    # phosphate or phosphonate ester
    "phosphate": "[PX4](=O)([OX2,OX1-])([OX2,OX1-])[OX2,OX1-]",
    # quaternary ammonium: the choline head group
    "quaternary_n": "[NX4+]([CH3])([CH3])[CH3]",
    # primary amine on a short ethoxy arm: the ethanolamine head group
    "ethanolamine": "[NX3;H2,H3][CH2][CH2][OX2]P",
    # para and ortho quinone cores
    "quinone": "[#6]1(=O)[#6]=[#6][#6](=O)[#6]=[#6]1",
    "quinone_fused": "O=C1C=CC(=O)c2ccccc21",
    # a sugar ring: pyranose or furanose with multiple hydroxyls
    "pyranose": "[CX4]1[OX2][CX4][CX4][CX4][CX4]1",
    "furanose": "[CX4]1[OX2][CX4][CX4][CX4]1",
    # porphyrin / chlorin macrocycle core
    "porphyrin": "c1cc2cc3ccc(cc4ccc(cc5ccc(cc1n2)[nX2,nX3]5)[nX2,nX3]4)[nX2,nX3]3",
    # thiol reducing agents
    "dithiol": "[SX2H][CX4][CX4][SX2H]",
    # sulfonic acid: the Good's buffer family (MES, HEPES, CAPS, CHES, MOPS)
    "sulfonic_acid": "[SX4](=O)(=O)[OX2H,OX1-]",
    # purine and pyrimidine nucleobases
    "purine": "c1ncc2[nX2,nX3]c[nX2,nX3]c2n1",
    "purine_alt": "c1nc2c(n1)ncnc2",
    "pyrimidine_base": "O=c1[nX3][cX3]([#8,#7])[#6][#6][nX3]1",
    "pyrimidine_alt": "O=c1cc[nX3]c(=O)[nX3]1",
    # a ribose or deoxyribose sugar attached to a nitrogen: the nucleoside bond
    "n_glycoside": "[nX3,NX3]-[CX4]1[OX2][CX4][CX4][CX4]1",
    # carboxylic acid
    "carboxylic_acid": "[CX3](=O)[OX2H,OX1-]",
    # a carbon-to-metalloid or heavy-metal bond: an organomercurial or arsenical
    "organometallic": "[#6]-[Hg,As,Sb,Pb,Sn,Tl,Pt,Au]",
}


@lru_cache(maxsize=1)
def _patterns() -> dict:
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    compiled = {}
    for name, smarts in _SMARTS.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is not None:
            compiled[name] = pattern
    return compiled


@lru_cache(maxsize=65536)
def _mol(smiles: str):
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    if not smiles:
        return None
    return Chem.MolFromSmiles(smiles)


@dataclass
class Features:
    """Structural descriptors a classification rule can reason about."""

    heavy_atoms: int
    carbons: int
    oxygens: int
    nitrogens: int
    phosphorus: int
    sulfur: int
    halogens: int
    metals: int
    rings: int
    aromatic_rings: int
    rotatable_bonds: int
    longest_carbon_chain: int
    peg_repeats: int
    esters: int
    has_phosphate: bool
    has_quaternary_n: bool
    has_ethanolamine_phosphate: bool
    has_quinone: bool
    sugar_rings: int
    has_porphyrin: bool
    has_dithiol: bool
    has_sulfonic_acid: bool
    has_nucleobase: bool
    has_n_glycoside: bool
    carboxylic_acids: int
    has_organometallic: bool
    hydroxyls: int
    aliphatic_amines: int
    conjugated_cc_double_bonds: int
    fraction_sp3: float


METAL_ATOMIC_NUMBERS = set(range(21, 31)) | set(range(39, 49)) | set(range(72, 81)) | {
    3, 4, 11, 12, 13, 19, 20, 31, 37, 38, 49, 50, 55, 56, 81, 82, 83,
} | set(range(57, 72)) | set(range(89, 104))


def longest_aliphatic_carbon_chain(mol) -> int:
    """Longest path of acyclic sp3 carbons, which is what makes a tail a tail.

    Implemented as a depth-first longest path over the acyclic-carbon subgraph.
    These fragments are small (tens of atoms), so the exponential worst case
    never bites, and a visited set keeps each walk simple.
    """
    carbons = [
        atom.GetIdx() for atom in mol.GetAtoms()
        if atom.GetSymbol() == "C" and not atom.IsInRing()
    ]
    if not carbons:
        return 0
    allowed = set(carbons)
    neighbours = {
        idx: [n.GetIdx() for n in mol.GetAtomWithIdx(idx).GetNeighbors()
              if n.GetIdx() in allowed]
        for idx in carbons
    }

    best = 0

    def walk(node: int, seen: frozenset[int]) -> int:
        longest = 1
        for neighbour in neighbours[node]:
            if neighbour in seen:
                continue
            longest = max(longest, 1 + walk(neighbour, seen | {neighbour}))
        return longest

    for start in carbons:
        best = max(best, walk(start, frozenset({start})))
    return best


def count_conjugated_cc_doubles(mol) -> int:
    from rdkit import Chem

    total = 0
    for bond in mol.GetBonds():
        if (bond.GetBondType() == Chem.BondType.DOUBLE
                and bond.GetIsConjugated()
                and bond.GetBeginAtom().GetSymbol() == "C"
                and bond.GetEndAtom().GetSymbol() == "C"
                and not bond.GetBeginAtom().GetIsAromatic()
                and not bond.GetEndAtom().GetIsAromatic()):
            total += 1
    return total


def features(smiles: str) -> Features | None:
    """Compute structural features, or None when the SMILES will not parse."""
    from rdkit.Chem import Descriptors, rdMolDescriptors

    mol = _mol(smiles)
    if mol is None:
        return None
    patterns = _patterns()

    def matches(name: str) -> int:
        pattern = patterns.get(name)
        if pattern is None:
            return 0
        return len(mol.GetSubstructMatches(pattern))

    counts: dict[str, int] = {}
    metals = 0
    halogens = 0
    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        counts[symbol] = counts.get(symbol, 0) + 1
        if atom.GetAtomicNum() in METAL_ATOMIC_NUMBERS:
            metals += 1
        if symbol in {"F", "Cl", "Br", "I"}:
            halogens += 1

    sugar_rings = matches("pyranose") + matches("furanose")
    try:
        fraction_sp3 = float(rdMolDescriptors.CalcFractionCSP3(mol))
    except Exception:  # noqa: BLE001
        fraction_sp3 = 0.0

    return Features(
        heavy_atoms=mol.GetNumHeavyAtoms(),
        carbons=counts.get("C", 0),
        oxygens=counts.get("O", 0),
        nitrogens=counts.get("N", 0),
        phosphorus=counts.get("P", 0),
        sulfur=counts.get("S", 0),
        halogens=halogens,
        metals=metals,
        rings=rdMolDescriptors.CalcNumRings(mol),
        aromatic_rings=rdMolDescriptors.CalcNumAromaticRings(mol),
        rotatable_bonds=rdMolDescriptors.CalcNumRotatableBonds(mol),
        longest_carbon_chain=longest_aliphatic_carbon_chain(mol),
        peg_repeats=matches("peg_repeat"),
        esters=matches("ester"),
        has_phosphate=bool(matches("phosphate")),
        has_quaternary_n=bool(matches("quaternary_n")),
        has_ethanolamine_phosphate=bool(matches("ethanolamine")),
        has_quinone=bool(matches("quinone") or matches("quinone_fused")),
        sugar_rings=sugar_rings,
        has_porphyrin=bool(matches("porphyrin")),
        has_dithiol=bool(matches("dithiol")),
        has_sulfonic_acid=bool(matches("sulfonic_acid")),
        has_nucleobase=bool(
            matches("purine") or matches("purine_alt")
            or matches("pyrimidine_base") or matches("pyrimidine_alt")
        ),
        has_n_glycoside=bool(matches("n_glycoside")),
        carboxylic_acids=matches("carboxylic_acid"),
        has_organometallic=bool(matches("organometallic")),
        hydroxyls=sum(
            1 for atom in mol.GetAtoms()
            if atom.GetSymbol() == "O" and atom.GetTotalNumHs() >= 1
            and not atom.IsInRing()
        ),
        aliphatic_amines=sum(
            1 for atom in mol.GetAtoms()
            if atom.GetSymbol() == "N" and not atom.GetIsAromatic()
            and not atom.IsInRing()
        ),
        conjugated_cc_double_bonds=count_conjugated_cc_doubles(mol),
        fraction_sp3=fraction_sp3,
    )


# --------------------------------------------------------------------------- #
# the structural rules
# --------------------------------------------------------------------------- #

def structural_class(smiles: str) -> tuple[str, str] | None:
    """Classify from structure alone. Returns (class, reason) or None.

    Ordered most specific first. Each condition is a general statement about a
    chemical class rather than a lookup, so it generalises to components not
    seen during development.
    """
    feature = features(smiles)
    if feature is None:
        return None
    f = feature

    # Polyethers: PEG, glymes, and the "nonaoxaheptatriacontan-1-ol" family.
    # Two or more ethylene-oxide repeats with essentially nothing else present.
    if f.peg_repeats >= 1 and f.rings == 0 and f.nitrogens == 0 and f.phosphorus == 0:
        if f.oxygens >= 3 and f.carbons >= 4 and f.oxygens * 3 >= f.carbons:
            return "cryoprotectant", f"polyether:{f.peg_repeats}_eo_repeats"

    # Phosphocholine and phosphoethanolamine lipids, however they are named.
    if f.has_phosphate and (f.has_quaternary_n or f.has_ethanolamine_phosphate):
        if f.longest_carbon_chain >= 8:
            return "lipid", f"phospholipid_head_plus_c{f.longest_carbon_chain}_tail"

    # Phosphoglycerolipids with no amine head group: phosphatidylglycerol,
    # phosphatidic acid, phosphatidylinositol. Phosphate plus acyl ester plus
    # a tail, which is the general form the head-group rule above misses.
    if f.has_phosphate and f.esters >= 1 and f.longest_carbon_chain >= 6:
        return "lipid", f"phosphoglycerolipid_c{f.longest_carbon_chain}_tail"

    # Acyl glycerolipids, waxes and fatty acid esters: an ester with a long tail.
    if f.esters >= 1 and f.longest_carbon_chain >= 10 and f.aromatic_rings == 0:
        return "lipid", f"acyl_ester_c{f.longest_carbon_chain}_tail"

    # Free fatty acids and long alkanes.
    if (f.rings == 0 and f.longest_carbon_chain >= 14
            and f.nitrogens == 0 and f.phosphorus == 0
            and f.oxygens <= 3 and f.fraction_sp3 >= 0.7):
        return "lipid", f"aliphatic_c{f.longest_carbon_chain}"

    # Detergents: a sugar or polyol head group on a long aliphatic tail.
    if f.sugar_rings >= 1 and f.longest_carbon_chain >= 8:
        return "detergent", f"glycoside_head_plus_c{f.longest_carbon_chain}_tail"

    # Isoprenoid quinones: ubiquinone, plastoquinone, menaquinone.
    if f.has_quinone and f.longest_carbon_chain >= 10:
        return "cofactor", f"isoprenoid_quinone_c{f.longest_carbon_chain}"

    # Porphyrins, chlorins and their metal complexes.
    if f.has_porphyrin:
        return "cofactor", "porphyrin_macrocycle"

    # Carotenoids and other long polyenes: an extended conjugated chain.
    if f.conjugated_cc_double_bonds >= 6 and f.carbons >= 30:
        return "cofactor", f"polyene:{f.conjugated_cc_double_bonds}_conjugated_cc"

    # Polyoxometalates: decavanadate, tungstate and molybdate clusters.
    if f.metals >= 2 and f.carbons == 0 and f.oxygens >= 6:
        return "buffer", f"polyoxometalate:{f.metals}_metal_{f.oxygens}_oxygen"

    # Thiol reducing agents: DTT and relatives.
    if f.has_dithiol and f.heavy_atoms <= 12:
        return "buffer", "dithiol_reducing_agent"

    # Nucleosides, nucleotides and free nucleobases. Metabolites and cofactor
    # fragments rather than designed ligands.
    if f.has_nucleobase and (f.has_n_glycoside or f.has_phosphate or f.heavy_atoms <= 14):
        return "cofactor", "nucleobase_or_nucleotide"

    # Sugar phosphates and phosphorylated metabolites: glycolysis intermediates.
    if f.has_phosphate and f.carbons <= 8 and f.hydroxyls >= 1 and f.rings <= 1:
        return "cofactor", "small_phosphorylated_metabolite"

    # Good's buffers: a sulfonic acid on a small aliphatic or alicyclic scaffold.
    if f.has_sulfonic_acid and f.aromatic_rings == 0 and f.heavy_atoms <= 24:
        return "buffer", "sulfonic_acid_buffer"

    # Polyamines: spermine, spermidine and relatives, routine crystallisation
    # additives and nucleic acid condensing agents.
    if (f.aliphatic_amines >= 3 and f.rings == 0
            and f.oxygens == 0 and f.phosphorus == 0):
        return "buffer", f"polyamine:{f.aliphatic_amines}_amines"

    # Heavy-atom derivatives: organomercurials and arsenicals used for phasing.
    if f.has_organometallic:
        return "covalent_modifier", "organometallic_heavy_atom_derivative"

    # Free fatty acids of medium chain length. Separate from the long-chain rule
    # above because a carboxylic acid head makes a shorter tail diagnostic.
    if (f.carboxylic_acids >= 1 and f.longest_carbon_chain >= 7
            and f.rings == 0 and f.nitrogens == 0 and f.oxygens <= 3):
        return "lipid", f"fatty_acid_c{f.longest_carbon_chain}"

    # Acyclic polyols: glycerol, the butanediols, MPD, the sugar alcohols.
    if (f.rings == 0 and f.hydroxyls >= 3 and f.carbons <= 8
            and f.nitrogens == 0 and f.phosphorus == 0 and f.sulfur == 0
            and f.hydroxyls * 3 >= f.carbons):
        return "cryoprotectant", f"acyclic_polyol:{f.hydroxyls}_oh"

    return None
