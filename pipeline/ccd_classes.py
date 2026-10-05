"""Chemical component classification (spec 4.3).

Crystallisation additives are **classified, not deleted**: a deleted row cannot
train the triage model and cannot be audited, and the counts would stop
reconciling. Every CCD code the pipeline sees lands in
`data/reference/ccd_classes.tsv` under exactly one of:

    glue_candidate | cofactor | metal | cryoprotectant | buffer | detergent
    lipid | sugar | peptide_like | covalent_modifier | unknown

**The BioLiP2 artefact list is deliberately not an input to this classifier.**
Spec 9.1 scores BINMAN on whether it independently classes BioLiP's artefact
ligands as furniture. Feeding that list in would make the metric measure a
lookup rather than a classifier, so it is carried as an evaluation-only column
and `classify()` never reads it. See DECISIONS.md D-007.

Classification runs in a fixed order and records which rule fired, so every row
is auditable:

1. single heavy atom of an ion element   -> metal
2. explicit CCD code in a seeded set     -> that class
3. structural rule over SMILES           -> that class  (pipeline.chem_rules)
4. name keyword match                    -> that class
5. CCD type from the chemical dictionary -> peptide_like / sugar
6. size and the absence of any furniture signal -> glue_candidate
7. anything left                         -> unknown

Structure is consulted before name because the same chemistry is deposited under
wildly different names: a PEG oligomer appears as "PEG", as
"DI(HYDROXYETHYL)ETHER" and as "nonaoxaheptatriacontan-1-ol". See
`pipeline/chem_rules.py`.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pipeline.common import REFERENCE

CLASSES = (
    "glue_candidate", "cofactor", "metal", "cryoprotectant", "buffer",
    "detergent", "lipid", "sugar", "peptide_like", "covalent_modifier", "unknown",
)

OUTPUT = REFERENCE / "ccd_classes.tsv"

# --------------------------------------------------------------------------- #
# seeds: explicit CCD codes
# --------------------------------------------------------------------------- #

# Ion and metal elements. A single-heavy-atom component of one of these is a
# metal or simple ion whatever its name says.
ION_ELEMENTS = {
    "LI", "NA", "K", "RB", "CS", "BE", "MG", "CA", "SR", "BA", "AL", "GA", "IN",
    "TL", "SC", "TI", "V", "CR", "MN", "FE", "CO", "NI", "CU", "ZN", "Y", "ZR",
    "NB", "MO", "TC", "RU", "RH", "PD", "AG", "CD", "HF", "TA", "W", "RE", "OS",
    "IR", "PT", "AU", "HG", "PB", "BI", "LA", "CE", "PR", "ND", "SM", "EU", "GD",
    "TB", "DY", "HO", "ER", "TM", "YB", "LU", "TH", "U", "F", "CL", "BR", "I",
    "SE", "AS", "SB", "TE", "XE", "KR", "AR", "NE", "HE",
}

CRYOPROTECTANT = {
    "GOL",  # glycerol
    "EDO", "PEG", "PG4", "PG5", "PG6", "PGE", "P6G", "1PE", "2PE", "7PE", "12P",
    "15P", "33O", "XPE", "M2M", "P33", "P4C", "P4G", "PE3", "PE4", "PE5", "PE7",
    "PE8", "PEU", "DIO", "TOE", "MPD", "MRD", "MPO", "BU1", "BU2", "BU3", "PDO",
    "ETE", "ETX", "TRT", "SBT", "IPA", "IOH", "EOH", "MOH", "DMS",  # DMSO
    "SUC",  # sucrose as cryo
    "TRE", "SOR", "XYL", "ERY", "MAN",
}

BUFFER = {
    "TRS",  # Tris
    "EPE",  # HEPES
    "MES", "MOP", "PIN", "CIT", "FLC", "CAC", "ACT", "ACY", "ACE", "FMT", "TLA",
    "TAR", "MLA", "MLT", "MLI", "SIN", "SUA", "GLV", "OXL", "PO4", "2PO", "3PO",
    "SO4", "SUL", "NO3", "NO2", "CO3", "BCT", "BO3", "BO4", "AZI", "CN", "SCN",
    "IMD", "IMZ", "HIS", "GLY", "BTB", "BCN", "EPD", "TAM", "TMA", "NH4", "NHE",
    "PIP", "P33", "CCN", "SOH", "AKG", "MPT", "BME", "DTT", "DTU", "DTV", "TCE",
    "EDT", "EDO", "EDD", "EGL", "URE", "GAI", "ARF", "MAE", "MOO", "WO4", "VO4",
    "AF3", "ALF", "BEF", "PER", "CLO", "BRO", "IOD", "PT4", "HGI",
}
# EDO appears in both tables; CRYOPROTECTANT is checked first and wins.

DETERGENT = {
    "LDA", "LDAO", "DDQ", "C8E", "C10", "C12", "CE1", "CE9", "CXE", "P15", "JEF",
    "BNG", "BOG", "BGL", "B3P", "HTG", "HTO", "OTG", "SDS", "LAU", "LMT", "LMU",
    "DDM", "UND", "UMQ", "MYS", "D10", "D12", "TRX", "TWT", "F09", "F6H", "CPS",
    "CHS", "CHD", "CHT", "BAM", "7E8", "7E9", "9E8", "DXC", "DAO", "ANAPOE",
}

LIPID = {
    "PLM", "MYR", "STE", "OLA", "OLB", "OLC", "PAM", "DAO", "HEX", "HXD", "DEC",
    "DOD", "D12", "PC", "PCW", "PEE", "PEF", "PEV", "PGV", "PGW", "PSC", "POV",
    "LHG", "DGA", "DGG", "CDL", "CL1", "CLR", "CHL", "ERG", "HEM", "HEC", "HEA",
    "SQL", "RET", "BCR", "LUT", "ZEX", "PEK", "3PH", "D3D", "LPP", "MC3", "SPH",
    "CER", "16Y", "Y01", "LFA", "LNK", "LNL", "LPE", "LPC",
}
# HEM and its relatives are cofactors by function, not lipids. They are seeded
# into COFACTOR too, which is checked before LIPID.

SUGAR = {
    "NAG", "NDG", "BGC", "GLC", "GAL", "GLA", "MAN", "BMA", "FUC", "FUL", "XYS",
    "XYP", "RIB", "RIP", "SIA", "NGA", "A2G", "GCU", "IDS", "ADA", "RAM", "RHM",
    "ARA", "ARB", "LAT", "LBT", "MAL", "CBI", "TRE", "GLO", "FRU", "SOE", "INS",
    "BGL", "G6P", "G1P", "F6P", "FBP", "AGL", "GCS", "GCD", "MBG", "MMA",
}

COFACTOR = {
    "ATP", "ADP", "AMP", "ANP", "ACP", "AGS", "APC", "ATR", "GTP", "GDP", "GMP",
    "GNP", "GSP", "GCP", "CTP", "CDP", "CMP", "UTP", "UDP", "UMP", "TTP", "TDP",
    "NAD", "NAI", "NAP", "NDP", "NAX", "NAJ", "FAD", "FDA", "FMN", "FNR", "RBF",
    "SAM", "SAH", "SFG", "COA", "ACO", "CAA", "COO", "HXC", "MCA", "SCA", "BCO",
    "TPP", "TDM", "THD", "PLP", "PMP", "P5P", "B12", "COB", "CNC", "B1Z",
    "HEM", "HEC", "HEA", "HEB", "HDD", "DHE", "HNI", "SRM", "VER", "CLA", "CHL",
    "BCL", "BPH", "PHO", "F43", "MQ7", "MQ8", "MQ9", "UQ1", "UQ2", "UQ6", "UQ8",
    "PQN", "TTQ", "PQQ", "MDO", "MGD", "2MD", "MSS", "SF4", "FES", "FS4", "F3S",
    "SF3", "CFM", "CFN", "ICS", "HCA", "NFV", "WCC", "CUA", "CUB", "CUZ", "MOS",
    "GSH", "GDS", "GTT", "BTN", "BTI", "THF", "THG", "FOL", "5FU", "MTX",
    "PNS", "DPM", "H4B", "BH4", "MHZ", "LPA", "TPQ", "TOP", "SAP",
}

COVALENT_MODIFIER = {
    "PTR", "SEP", "TPO", "ALY", "MLY", "M3L", "MLZ", "CSO", "CSD", "CSS", "CSX",
    "OCS", "CME", "CSW", "SNC", "NEP", "HIC", "MHS", "AGM", "CIR", "NMM", "DAH",
    "HYP", "PCA", "FME", "MSE", "KCX", "LLP", "PLP", "SNN", "NH2", "ACE", "FOR",
    "MYR", "PLM", "CAF", "SMC", "BHD", "4HT", "SUI", "GL3", "CGU", "TYS", "OMT",
}

PEPTIDE_LIKE_TYPES = {
    "L-PEPTIDE LINKING", "D-PEPTIDE LINKING", "PEPTIDE LINKING",
    "L-PEPTIDE NH3 AMINO TERMINUS", "L-PEPTIDE COOH CARBOXY TERMINUS",
    "PEPTIDE-LIKE", "D-BETA-PEPTIDE, C-GAMMA LINKING",
    "L-BETA-PEPTIDE, C-GAMMA LINKING", "D-GAMMA-PEPTIDE, C-DELTA LINKING",
    "L-GAMMA-PEPTIDE, C-DELTA LINKING",
}
SACCHARIDE_TYPES = {
    "D-SACCHARIDE", "L-SACCHARIDE", "SACCHARIDE",
    "D-SACCHARIDE, BETA LINKING", "D-SACCHARIDE, ALPHA LINKING",
    "L-SACCHARIDE, BETA LINKING", "L-SACCHARIDE, ALPHA LINKING",
    "D-SACCHARIDE 1,4 AND 1,4 LINKING", "OLIGOSACCHARIDE",
}

# --------------------------------------------------------------------------- #
# name keyword rules, applied in order
# --------------------------------------------------------------------------- #

NAME_RULES: tuple[tuple[str, str], ...] = (
    # IUPAC polyether naming: "...oxa...an-1-ol" is how a PEG oligomer is named
    # when it is not called a PEG. Two or more "oxa" locants is the signal.
    (r"(di|tri|tetra|penta|hexa|hepta|octa|nona|deca|undeca|dodeca)oxa", "cryoprotectant"),
    (r"polyethylene glycol|peg\b|tetraethylene|triethylene|diethylene|"
     r"pentaethylene|hexaethylene|heptaethylene|octaethylene|glycol ether", "cryoprotectant"),
    (r"glycerol|ethylene glycol|propanediol|butanediol|pentanediol|hexanediol|"
     r"methylpentanediol|\bmpd\b|dimethyl sulfoxide|\bdmso\b|cryo", "cryoprotectant"),
    (r"\btris\b|tris\(hydroxymethyl\)|hepes|\bmes\b|\bmops\b|\bpipes\b|bicine|"
     r"tricine|\bbis-tris\b|\bcaps\b|\btaps\b|\bcacodylate\b|imidazole|"
     r"\bcitrate\b|citric acid|tartrate|tartaric|\bacetate\b|acetic acid|"
     r"\bformate\b|formic acid|\bmalonate\b|\bsuccinate\b|\bmalate\b|\boxalate\b|"
     r"\bphosphate\b|\bsulfate\b|\bsulphate\b|\bnitrate\b|\bcarbonate\b|"
     r"\bborate\b|\bazide\b|thiocyanate|\bbuffer\b|\burea\b|guanidin|"
     r"dithiothreitol|mercaptoethanol|\bedta\b|\begta\b", "buffer"),
    (r"detergent|\bchaps\b|\btriton\b|\btween\b|nonidet|lauryl|dodecyl|octyl|"
     r"decyl|nonyl|undecyl|glucoside|maltoside|maltopyranoside|"
     r"glucopyranoside|cholate|deoxycholate|\bdmso?-?nao\b|"
     r"dimethylamine oxide|polyoxyethylene", "detergent"),
    (r"phosphatidyl|phosphocholine|phosphoethanolamine|phosphoglycerol|"
     r"cardiolipin|sphingo|ceramide|cholesterol|ergosterol|monoolein|"
     r"\bmyristic\b|\bpalmitic\b|\bstearic\b|\boleic\b|fatty acid|"
     r"\btriglyceride\b|diacylglycerol", "lipid"),
    (r"coenzyme a\b|\bnad\b|\bnadp\b|\bfad\b|\bfmn\b|flavin|riboflavin|"
     r"\bheme\b|\bhaem\b|protoporphyrin|chlorophyll|bacteriochlorophyll|"
     r"cobalamin|\bbiotin\b|thiamine|pyridoxal|\bfolate\b|tetrahydrofolate|"
     r"s-adenosyl|glutathione|iron-sulfur|iron/sulfur|molybdopterin|"
     r"ubiquinone|menaquinone|plastoquinone|pyrroloquinoline|"
     r"adenosine-5'-tri|adenosine-5'-di|guanosine-5'-tri", "cofactor"),
    (r"pyranose|furanose|\bglucose\b|\bgalactose\b|\bmannose\b|\bfucose\b|"
     r"\bxylose\b|\bribose\b|\barabinose\b|\brhamnose\b|acetylglucosamine|"
     r"acetylgalactosamine|sialic acid|neuraminic|\bsucrose\b|\btrehalose\b|"
     r"\bmaltose\b|\blactose\b|\bcellobiose\b|saccharide", "sugar"),
)

# --------------------------------------------------------------------------- #
# classification
# --------------------------------------------------------------------------- #

SEED_SETS: tuple[tuple[str, set[str]], ...] = (
    ("cofactor", COFACTOR),
    ("cryoprotectant", CRYOPROTECTANT),
    ("buffer", BUFFER),
    ("detergent", DETERGENT),
    ("sugar", SUGAR),
    ("lipid", LIPID),
    ("covalent_modifier", COVALENT_MODIFIER),
)

# Classes whose members are small by nature. A name match for one of these on a
# molecule larger than this is rejected: see the guard in `classify`.
SIZE_GUARDED_CLASSES = frozenset({"buffer", "cryoprotectant"})
# A detergent is an amphiphile with a simple head. Triton's single phenyl is
# the most any genuine one here carries; two or more rings means a drug.
MAX_DETERGENT_AROMATIC_RINGS = 1
MAX_FURNITURE_HEAVY_ATOMS = 12

FURNITURE_CLASSES = frozenset(
    {"cryoprotectant", "buffer", "detergent", "metal", "sugar", "covalent_modifier"}
)


@dataclass
class Classification:
    ccd_id: str
    ccd_class: str
    rule: str          # which rule fired, so every row is auditable
    name: str = ""
    formula: str = ""
    mw: float | None = None
    heavy_atoms: int | None = None
    ccd_type: str = ""
    smiles: str = ""

    def as_row(self) -> dict:
        return {
            "ccd_id": self.ccd_id, "ccd_class": self.ccd_class, "rule": self.rule,
            "name": self.name, "formula": self.formula,
            "mw": f"{self.mw:.3f}" if self.mw is not None else "",
            "heavy_atoms": self.heavy_atoms if self.heavy_atoms is not None else "",
            "ccd_type": self.ccd_type, "smiles": self.smiles,
            "is_furniture": int(self.ccd_class in FURNITURE_CLASSES),
        }


def _element_from_formula(formula: str) -> str | None:
    """Element symbol when a formula describes a single atom, else None.

    Handles "Zn", "ZN 2", "Mg 2+" and "Fe" alike.
    """
    tokens = [t for t in re.split(r"[\s]+", (formula or "").strip()) if t]
    if not tokens:
        return None
    first = re.sub(r"[^A-Za-z]", "", tokens[0]).upper()
    if not first or len(first) > 2:
        return None
    # A single-atom formula is one element token, optionally followed by a
    # charge token. Anything with a second element token is not monatomic.
    if len(tokens) > 1 and re.search(r"[A-Za-z]{1,2}\d*$", tokens[1]) and \
            not re.fullmatch(r"[0-9+-]+", tokens[1]):
        return None
    return first


def _aromatic_rings(smiles: str) -> int:
    """Aromatic ring count, or 0 when the structure cannot be read.

    Falling back to 0 keeps an unreadable SMILES on the old behaviour rather
    than silently reclassifying it on missing evidence.
    """
    try:
        from pipeline.chem_rules import features

        found = features(smiles)
        return int(found.aromatic_rings) if found else 0
    except Exception:
        return 0


def classify(
    ccd_id: str,
    *,
    name: str = "",
    formula: str = "",
    mw: float | None = None,
    heavy_atoms: int | None = None,
    ccd_type: str = "",
    smiles: str = "",
    min_glue_heavy_atoms: int = 10,
) -> Classification:
    """Assign one CCD code to one class.

    Deliberately does **not** take the BioLiP artefact list as an argument: that
    list is the held-out evaluation set for spec 9.1 (DECISIONS D-007).
    """
    code = (ccd_id or "").strip().upper()
    lowered = (name or "").lower()
    upper_type = (ccd_type or "").strip().upper()

    def result(ccd_class: str, rule: str) -> Classification:
        return Classification(
            ccd_id=code, ccd_class=ccd_class, rule=rule, name=name,
            formula=formula, mw=mw, heavy_atoms=heavy_atoms,
            ccd_type=ccd_type, smiles=smiles,
        )

    # 1. monatomic ions and metals
    element = _element_from_formula(formula)
    if element and element in ION_ELEMENTS:
        if heavy_atoms is None or heavy_atoms <= 1:
            return result("metal", f"monatomic_ion:{element}")
    if code in ION_ELEMENTS and (heavy_atoms is None or heavy_atoms <= 1):
        return result("metal", "ccd_code_is_element")

    # 1b. polyoxometalate clusters (decavanadate, tungstates, molybdates).
    # These frequently carry no usable SMILES, so the formula is the signal.
    formula_elements = re.findall(r"([A-Za-z]{1,2})(\d*)", (formula or ""))
    metal_atoms = sum(
        int(count or 1) for element, count in formula_elements
        if element.upper() in ION_ELEMENTS and element.upper() not in {"F", "CL", "BR", "I"}
    )
    oxygen_atoms = sum(
        int(count or 1) for element, count in formula_elements if element.upper() == "O"
    )
    carbon_atoms = sum(
        int(count or 1) for element, count in formula_elements if element.upper() == "C"
    )
    if metal_atoms >= 2 and carbon_atoms == 0 and oxygen_atoms >= 6:
        return result("buffer", f"polyoxometalate:{metal_atoms}_metal_{oxygen_atoms}_oxygen")

    # 2. explicit seed sets, in priority order
    for ccd_class, codes in SEED_SETS:
        if code in codes:
            return result(ccd_class, f"seed_set:{ccd_class}")

    # 3. structural rules over SMILES, which generalise where names do not
    if smiles:
        try:
            from pipeline.chem_rules import structural_class

            structural = structural_class(smiles)
        except Exception:  # noqa: BLE001 - RDKit absence must not break classification
            structural = None
        if structural is not None:
            ccd_class, reason = structural
            return result(ccd_class, f"structure:{reason}")

    # 4. name keywords.
    #
    # Guarded by size. A buffer, a cryoprotectant and a simple salt are all
    # small, and the name patterns are substrings: "indole-3-acetic acid"
    # contains "acetic acid", which classified auxin, the canonical plant
    # molecular glue, as a buffer and made 2P1Q a recall miss. A molecule far
    # larger than the buffer it is named after is not that buffer, so above the
    # size guard only the curated seed sets may assign a furniture class.
    for pattern, ccd_class in NAME_RULES:
        if not re.search(pattern, lowered):
            continue
        if ccd_class in SIZE_GUARDED_CLASSES and heavy_atoms is not None \
                and heavy_atoms > MAX_FURNITURE_HEAVY_ATOMS:
            continue
        # The detergent pattern matches alkyl-chain words (octyl, dodecyl,
        # lauryl, decyl) anywhere in the name, and an IUPAC name says "octyl"
        # for any eight-carbon linker. That classified RN3 and RN6 as
        # detergent and marked them furniture: both are CRBN-recruiting BET
        # degraders, thalidomide joined to JQ1 through a C8 linker, filed as
        # crystallisation plastic on a substring (D-065).
        #
        # Size cannot separate them: the largest correctly classed detergent
        # here is a 1,165 Da maltoside. Aromatic rings can. Of the 59 CCDs this
        # rule claimed, 48 have none or one and are genuine amphiphiles, and
        # all 10 with two or more are drugs, degraders or alkyl-chain natural
        # products.
        if ccd_class == "detergent" and smiles \
                and _aromatic_rings(smiles) >= MAX_DETERGENT_AROMATIC_RINGS + 1:
            continue
        return result(ccd_class, f"name_rule:{ccd_class}")

    # 5. chemical dictionary type
    if upper_type in PEPTIDE_LIKE_TYPES:
        return result("peptide_like", f"ccd_type:{upper_type}")
    if upper_type in SACCHARIDE_TYPES:
        return result("sugar", f"ccd_type:{upper_type}")

    # 6. big enough, drug-like and no furniture signal: a glue candidate
    if heavy_atoms is not None and heavy_atoms >= min_glue_heavy_atoms:
        return result("glue_candidate", f"size_and_no_furniture_signal:{heavy_atoms}_heavy")
    if heavy_atoms is None and mw is not None and mw >= 150:
        return result("glue_candidate", f"size_and_no_furniture_signal:mw_{mw:.0f}")

    # 7. small, unseeded, unnamed
    return result("unknown", "no_rule_matched")


def heavy_atoms_from_formula(formula: str) -> int | None:
    """Count non-hydrogen atoms in a CCD formula string such as "C51 H79 N O13"."""
    if not formula:
        return None
    total = 0
    found = False
    for token in formula.split():
        match = re.fullmatch(r"([A-Za-z]{1,2})(\d*)", token)
        if not match:
            continue
        element = match.group(1).upper()
        count = int(match.group(2)) if match.group(2) else 1
        if element in {"H", "D", "T"}:
            continue
        total += count
        found = True
    return total if found else None


# --------------------------------------------------------------------------- #
# table maintenance
# --------------------------------------------------------------------------- #

FIELDNAMES = (
    "ccd_id", "ccd_class", "rule", "name", "formula", "mw", "heavy_atoms",
    "ccd_type", "smiles", "is_furniture",
)


def load_table(path: Path = OUTPUT) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return {
            row["ccd_id"]: row
            for row in csv.DictReader(handle, delimiter="\t")
            if row.get("ccd_id")
        }


def save_table(rows: Iterable[dict], path: Path = OUTPUT) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: r["ccd_id"])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDNAMES), delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ordered)
    return len(ordered)


def class_counts(table: dict[str, dict]) -> dict[str, int]:
    counts = {name: 0 for name in CLASSES}
    for row in table.values():
        counts[row.get("ccd_class", "unknown")] = counts.get(row.get("ccd_class", "unknown"), 0) + 1
    counts["total"] = len(table)
    return counts
