"""Fit the reach boundaries on induced ternary complexes, not on monomers.

Spec 5.4's reach window is four numbers: one lysine-exposure threshold and
three Cb-Cb distance boundaries measured **from a ligand site**. Only the first
has ever been fitted, and D-054 recorded why the other three could not be: the
diGly data was matched to AlphaFold monomers, and "an AlphaFold monomer with an
observed ubiquitylation site carries no ligand site for the distance to be
measured from".

BINMAN's own atlas holds the missing geometry. 89 PDB entries have a ligand
bridging an E3 ligase to a non-E3 partner, and 74 have a local trimmed
structure. Those are induced ternary complexes: CRBN with BRD4 through a PROTAC,
DCAF15 with RBM39, beta-TrCP1 with beta-catenin. The ligand site is present, the
substrate chain is present, and the distance the spec asks about is measurable.

This also narrows the second half of the metric's own caveat. "Observed
ubiquitylation sites come from native E3 biology, not from induced ternary
complexes, so the window is a proxy." The geometry here *is* induced. The site
labels are still native, so the caveat is reduced rather than removed, and that
is said plainly rather than quietly dropped.

**The numbering trap this module exists to avoid.** `measure_lysines` reports
author numbering from the deposited structure. The ubiquitylation labels are in
UniProt numbering. For many entries these coincide and for many they do not,
because of expression tags, construct offsets and renumbering, and a mismatch
produces labels that are wrong without being empty: every lysine still gets a
label, just the wrong one. So the alignment is **checked rather than assumed**,
against the cached AlphaFold model for the substrate, which is UniProt-numbered
by construction: if the structure's lysine positions are not lysines in the
model, the entry is dropped and counted as dropped.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import ATLAS, INTERIM, VALIDATION, load_config, log_event  # noqa: E402

DB = ATLAS / "binman.sqlite"
STRUCTURES = ROOT / "app" / "static" / "structures"
CACHE = INTERIM / "afdb"
LABELS = VALIDATION / "assayed_ubiquitylation.tsv"
REPORT = INTERIM / "degradability_reach.json"
# A substrate chain must have at least this fraction of its lysines land on a
# lysine in the UniProt-numbered model before the entry is trusted.
MIN_NUMBERING_AGREEMENT = 0.8


def ternary_complexes(connection: sqlite3.Connection) -> list[dict]:
    """Entries where a ligand bridges an E3 to a non-E3 partner."""
    connection.create_function("asym", 1, lambda s: (s or "").split("/")[0])
    rows = connection.execute("""
        SELECT b.pdb_id, b.ccd_id, b.structure_file,
               ea.uniprot_acc AS acc_a, eb.uniprot_acc AS acc_b,
               b.chain_a, b.chain_b
        FROM bridge b
        JOIN polymer_entity ea ON ea.pdb_id = b.pdb_id AND ea.asym_id = asym(b.chain_a)
        JOIN polymer_entity eb ON eb.pdb_id = b.pdb_id AND eb.asym_id = asym(b.chain_b)
        WHERE b.status = 'ok'
          AND ((ea.uniprot_acc IN (SELECT uniprot_acc FROM ligase)
                AND eb.uniprot_acc NOT IN (SELECT uniprot_acc FROM ligase))
            OR (eb.uniprot_acc IN (SELECT uniprot_acc FROM ligase)
                AND ea.uniprot_acc NOT IN (SELECT uniprot_acc FROM ligase)))
    """).fetchall()
    e3s = {r[0] for r in connection.execute("SELECT uniprot_acc FROM ligase")}
    out = []
    for pdb, ccd, path, acc_a, acc_b, chain_a, chain_b in rows:
        if acc_a in e3s:
            e3, substrate, sub_chain = acc_a, acc_b, chain_b
        else:
            e3, substrate, sub_chain = acc_b, acc_a, chain_a
        if not substrate or not path:
            continue
        out.append({"pdb_id": pdb, "ccd_id": ccd, "structure_file": path,
                    "e3": e3, "substrate": substrate,
                    # the auth chain id, which is what gemmi names a chain
                    "substrate_chain": (sub_chain or "").split("/")[-1]})
    return out


def model_sequence(accession: str) -> dict[int, str]:
    """Residue number to one-letter code from the AlphaFold model.

    AlphaFold numbers by the UniProt sequence, so this is the reference the
    deposited structure's author numbering is checked against.
    """
    import gemmi

    path = next(iter(CACHE.glob(f"AF-{accession}*")), None)
    if path is None:
        return {}
    structure = gemmi.read_structure(str(path))
    structure.setup_entities()
    out: dict[int, str] = {}
    if not len(structure):
        return out
    for chain in structure[0]:
        for residue in chain:
            code = gemmi.find_tabulated_residue(residue.name)
            if code and code.is_amino_acid():
                out[residue.seqid.num] = code.one_letter_code.upper()
    return out


def measure(entry: dict, labels: dict, sasa) -> tuple[list[dict], str]:
    """Lysines of the substrate chain, with reach from the bridging ligand."""
    import gemmi

    from pipeline.degradability import measure_lysines

    path = STRUCTURES / entry["structure_file"]
    if not path.exists():
        return [], "no_structure_file"

    structure = gemmi.read_structure(str(path))
    structure.setup_entities()
    if not len(structure):
        return [], "empty_structure"

    # The site is the bridging ligand's atoms, for the centroid distance, and
    # the protein residues lining it, for the Cb-Cb distance.
    #
    # `measure_lysines` takes the Cb-Cb distance from a lysine to the nearest
    # CB among `site_residues`. Passing the ligand residue itself gives a site
    # with no CB at all, so every distance came back as the NaN sentinel and
    # the whole set was silently discarded. The site residues are the pocket,
    # not the ligand.
    site_atoms: list[tuple[float, float, float]] = []
    for chain in structure[0]:
        for residue in chain:
            if residue.name == entry["ccd_id"]:
                for atom in residue:
                    site_atoms.append((atom.pos.x, atom.pos.y, atom.pos.z))
    if not site_atoms:
        return [], "ligand_absent"

    lining = float(load_config().t("bridging.contact_cutoff_a"))
    site_residues: list[tuple[str, int]] = []
    for chain in structure[0]:
        for residue in chain:
            if residue.name == entry["ccd_id"]:
                continue
            if not any(
                min((ax - x) ** 2 + (ay - y) ** 2 + (az - z) ** 2
                    for x, y, z in site_atoms) <= lining * lining
                for ax, ay, az in ((a.pos.x, a.pos.y, a.pos.z) for a in residue)
            ):
                continue
            site_residues.append((chain.name, residue.seqid.num))
    if not site_residues:
        return [], "no_pocket_residues"

    reference = model_sequence(entry["substrate"])
    if not reference:
        return [], "no_alphafold_model"

    measurements = measure_lysines(
        path, site_atoms, site_residues, entry["substrate"],
        entry["pdb_id"], entry["ccd_id"], sasa,
        chains={entry["substrate_chain"]})
    if not measurements:
        return [], "no_lysines"

    # Numbering check: the deposited author numbers must land on lysines in the
    # UniProt-numbered model, or the labels would be attached to the wrong
    # residues without any of them looking empty.
    agree = sum(1 for m in measurements if reference.get(m.res_num) == "K")
    if agree / len(measurements) < MIN_NUMBERING_AGREEMENT:
        return [], f"numbering_mismatch:{agree}/{len(measurements)}"

    rows = []
    for m in measurements:
        label = labels.get((entry["substrate"], m.res_num))
        if label is None:
            continue        # not assayed: no evidence either way
        if m.cb_cb_distance < 0:
            continue        # -1 is the no-Cb-Cb sentinel, not a short distance
        rows.append({
            "pdb_id": entry["pdb_id"], "ccd_id": entry["ccd_id"],
            "e3": entry["e3"], "substrate": entry["substrate"],
            "res_num": m.res_num,
            "nz_rel_sasa": round(m.nz_rel_sasa, 4),
            "cb_cb_distance": round(m.cb_cb_distance, 2),
            "nz_centroid_distance": round(m.nz_centroid_distance, 2),
            "ubiquitylated": label,
        })
    return rows, "ok"


def run() -> dict:
    import numpy as np
    from sklearn.metrics import roc_auc_score

    from pipeline.geometry import SasaCalculator

    config = load_config()
    labels: dict[tuple[str, int], int] = {}
    with LABELS.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            labels[(row["uniprot"], int(row["res_num"]))] = int(row["ubiquitylated"])

    connection = sqlite3.connect(DB)
    entries = ternary_complexes(connection)
    connection.close()

    sasa = SasaCalculator(config)
    rows: list[dict] = []
    reasons = collections.Counter()
    for entry in entries:
        produced, reason = measure(entry, labels, sasa)
        reasons[reason.split(":")[0]] += 1
        rows.extend(produced)

    report: dict = {
        "question": ("do the spec 5.4 Cb-Cb reach boundaries separate "
                     "ubiquitylated lysines from assayed-unmodified ones, "
                     "measured in induced ternary complexes"),
        "n_ternary_entries": len(entries),
        "entry_outcomes": dict(reasons),
        "n_lysines": len(rows),
        "n_ubiquitylated": sum(r["ubiquitylated"] for r in rows),
        "geometry_is_induced": True,
        "labels_are_native": ("the ternary geometry is induced, the "
                              "ubiquitylation labels are still native E3 "
                              "biology, so the proxy caveat is narrowed and "
                              "not removed"),
    }
    if rows:
        y = np.asarray([r["ubiquitylated"] for r in rows])
        if 0 < y.sum() < len(y):
            for field in ("cb_cb_distance", "nz_centroid_distance", "nz_rel_sasa"):
                values = np.asarray([r[field] for r in rows], dtype=float)
                # Reach is a closeness argument, so a shorter distance should
                # mean more degradable: the distance is negated before scoring.
                scored = -values if "distance" in field else values
                report[f"auc_{field}"] = round(float(roc_auc_score(y, scored)), 4)
        report["cb_cb_summary"] = {
            "ubiquitylated_median": round(float(np.median(
                [r["cb_cb_distance"] for r in rows if r["ubiquitylated"]])), 2),
            "unmodified_median": round(float(np.median(
                [r["cb_cb_distance"] for r in rows if not r["ubiquitylated"]])), 2),
        }
    (INTERIM / "degradability_reach.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    log_event("9.4", f"Reach on induced ternaries: {len(rows)} assayed lysines "
                     f"over {len(entries)} complexes, "
                     f"{report['n_ubiquitylated']} ubiquitylated.")
    return report


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
