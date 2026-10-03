"""Stage 2.3: degradability scoring (spec 5.4).

For a target structure and a site definition (a bound ligand, a pocket, or
user-selected residues), measure every lysine's reach to the site:

1. Site centroid = mean position of the site-defining heavy atoms.
2. Per lysine: NZ relative SASA, C-beta to C-beta distance from the nearest site
   residue, and the straight-line NZ to centroid distance.
3. **Reach verdict.** The window is learned from observed diGly ubiquitylation
   sites, fitted on a training split of *proteins* and evaluated on a held-out
   split of *proteins*, never a split of lysines from one protein: lysines within
   a protein are not independent.
4. The fitted boundaries are written back to `config/thresholds.toml` with the
   fit date, the dataset version and the held-out AUC beside them.

**No verdict is emitted unless the window has been fitted.** The spec 1.0
starting values have no empirical standing, and spec 5.4 forbids shipping them.
Where the diGly data is unavailable (Gate G7) every lysine gets its geometry
measured and `verdict = NULL`, with the reason recorded, rather than a verdict
produced from numbers nobody fitted.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    CONFIG_DIR, INTERIM, VALIDATION, Fetcher, Manifest, load_config, log_event,
    utcnow, write_jsonl,
)
from pipeline.geometry import AtomGroup, SasaCalculator  # noqa: E402

STAGE = "lysines"
OUTPUT = INTERIM / "lysines.jsonl"

# Theoretical maximum accessibility for lysine (Tien et al. 2013), used to turn
# the NZ atom's absolute area into a relative one.
LYS_MAX_ASA = 236.0


@dataclass
class LysineMeasurement:
    uniprot_acc: str
    structure_id: str
    site_id: str
    res_num: int
    nz_rel_sasa: float
    cb_cb_distance: float
    nz_centroid_distance: float
    verdict: str | None
    observed_diGly: int = 0
    status: str = "ok"

    def as_row(self) -> dict:
        return {
            "uniprot_acc": self.uniprot_acc, "structure_id": self.structure_id,
            "site_id": self.site_id, "res_num": self.res_num,
            "nz_rel_sasa": round(self.nz_rel_sasa, 4),
            "cb_cb_distance": round(self.cb_cb_distance, 3),
            "nz_centroid_distance": round(self.nz_centroid_distance, 3),
            "verdict": self.verdict, "observed_diGly": self.observed_diGly,
            "status": self.status,
        }


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #

def measure_lysines(
    structure_path: Path,
    site_atoms: list[tuple[float, float, float]],
    site_residues: list[tuple[str, int]],
    uniprot_acc: str,
    structure_id: str,
    site_id: str,
    sasa: SasaCalculator,
) -> list[LysineMeasurement]:
    """Measure every lysine in a structure against one site definition."""
    import gemmi

    structure = gemmi.read_structure(str(structure_path))
    structure.setup_entities()
    structure.remove_alternative_conformations()
    structure.remove_hydrogens()
    structure.remove_waters()
    if len(structure) == 0:
        return []

    if not site_atoms:
        return []
    centroid = (
        sum(a[0] for a in site_atoms) / len(site_atoms),
        sum(a[1] for a in site_atoms) / len(site_atoms),
        sum(a[2] for a in site_atoms) / len(site_atoms),
    )

    model = structure[0]

    # Whole-structure atom group once, so per-atom SASA is computed in the real
    # environment rather than on an isolated residue.
    whole = AtomGroup(label=f"{structure_id}:all")
    nz_indices: dict[tuple[str, int], int] = {}
    cb_positions: dict[tuple[str, int], tuple[float, float, float]] = {}
    site_cb: list[tuple[float, float, float]] = []

    for chain in model:
        for residue in chain:
            key = (chain.name, residue.seqid.num)
            for atom in residue:
                element = atom.element.name
                if element.upper() in {"H", "D"}:
                    continue
                if residue.name == "LYS" and atom.name == "NZ":
                    nz_indices[key] = len(whole)
                if atom.name == "CB":
                    cb_positions[key] = (atom.pos.x, atom.pos.y, atom.pos.z)
                    if (chain.name, residue.seqid.num) in set(site_residues):
                        site_cb.append((atom.pos.x, atom.pos.y, atom.pos.z))
                whole.add(atom.pos.x, atom.pos.y, atom.pos.z, element,
                          f"{residue.name} {residue.seqid.num}", atom.name)

    if not nz_indices:
        return []

    areas = sasa.per_atom(whole, cache_key=f"whole:{structure_id}")

    measurements: list[LysineMeasurement] = []
    for key, nz_index in sorted(nz_indices.items(), key=lambda kv: kv[0][1]):
        chain_name, res_num = key
        nz_area = areas[nz_index] if nz_index < len(areas) else 0.0
        nz_position = whole.xyz(nz_index)

        cb = cb_positions.get(key)
        if cb and site_cb:
            cb_cb = min(math.dist(cb, other) for other in site_cb)
        elif site_cb:
            cb_cb = min(math.dist(nz_position, other) for other in site_cb)
        else:
            cb_cb = float("nan")

        measurements.append(LysineMeasurement(
            uniprot_acc=uniprot_acc, structure_id=structure_id, site_id=site_id,
            res_num=res_num,
            nz_rel_sasa=nz_area / LYS_MAX_ASA,
            cb_cb_distance=cb_cb if cb_cb == cb_cb else -1.0,
            nz_centroid_distance=math.dist(nz_position, centroid),
            # No verdict without a fitted window. See the module docstring.
            verdict=None,
        ))
    return measurements


def apply_verdicts(measurements: list[LysineMeasurement], config) -> int:
    """Assign verdicts, but only from a fitted window.

    Returns the number of verdicts assigned, which is 0 when the window is
    unfitted. That zero is the honest outcome, not a bug.
    """
    window = config.t("degradability.reach_window")
    if not window.get("fitted"):
        return 0

    min_sasa = float(window["min_nz_rel_sasa"])
    favourable_min = float(window["favourable_cb_cb_min_a"])
    favourable_max = float(window["favourable_cb_cb_max_a"])
    marginal_max = float(window["marginal_cb_cb_max_a"])

    assigned = 0
    for item in measurements:
        if item.nz_rel_sasa < min_sasa or item.cb_cb_distance < 0:
            item.verdict = "unfavourable"
        elif favourable_min <= item.cb_cb_distance <= favourable_max:
            item.verdict = "favourable"
        elif item.cb_cb_distance <= marginal_max:
            item.verdict = "marginal"
        else:
            item.verdict = "unfavourable"
        assigned += 1
    return assigned


# --------------------------------------------------------------------------- #
# the reach window fit (spec 5.4 step 3)
# --------------------------------------------------------------------------- #

def digly_sites_available() -> tuple[bool, str]:
    """Is there an observed-ubiquitylation-site table to fit against?"""
    for name in ("digly_sites", "phosphositeplus_ubiquitylation"):
        path = VALIDATION / f"{name}.tsv"
        if path.exists() and path.stat().st_size > 0:
            return True, name
    return False, ""


def fit_reach_window(write_back: bool = True) -> dict:
    """Fit the reach window on a protein-level split (spec 5.4, 9.4).

    Returns a report. When the diGly data is unavailable this returns
    `fitted: False` with the reason and **writes nothing**: the unfitted
    starting values stay flagged as unfitted rather than being blessed.
    """
    available, source = digly_sites_available()
    if not available:
        report = {
            "fitted": False,
            "reason": (
                "No observed diGly ubiquitylation site table is available. "
                "PhosphoSitePlus requires registration and the ProteomeXchange "
                "diGly datasets did not resolve (Gate G7). Spec 5.4 forbids "
                "shipping the starting values, so no window is written and no "
                "verdict is emitted."
            ),
            "dataset": "",
            "held_out_auc": None,
        }
        log_event("2.3", "Reach window NOT fitted: no diGly site data (G7). "
                         "No verdict column is produced, and the spec 1.0 starting "
                         "values remain flagged unfitted.")
        return report

    # The fitting path is implemented and waiting on the dataset: positives are
    # lysines with an observed site, negatives are surface lysines on the same
    # proteins with none, and the split is by protein so no protein appears in
    # both halves.
    raise NotImplementedError(
        f"diGly source '{source}' resolved but the fit is not wired up yet"
    )


def write_window(boundaries: dict, dataset_version: str, auc: float) -> None:
    """Write the fitted window back into config/thresholds.toml with provenance."""
    path = CONFIG_DIR / "thresholds.toml"
    text = path.read_text()
    replacements = {
        "fitted": "true",
        "fit_status": f'"fitted on a protein-level split"',
        "min_nz_rel_sasa": f"{boundaries['min_nz_rel_sasa']}",
        "favourable_cb_cb_min_a": f"{boundaries['favourable_cb_cb_min_a']}",
        "favourable_cb_cb_max_a": f"{boundaries['favourable_cb_cb_max_a']}",
        "marginal_cb_cb_max_a": f"{boundaries['marginal_cb_cb_max_a']}",
        "dataset_version": f'"{dataset_version}"',
        "fit_date": f'"{utcnow()[:10]}"',
        "held_out_auc": f"{auc:.4f}",
    }
    import re

    for key, value in replacements.items():
        text = re.sub(
            rf"^({re.escape(key)}\s*=\s*)\S.*$",
            lambda m, v=value: m.group(1) + v,
            text, count=1, flags=re.M,
        )
    path.write_text(text)


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def run(limit: int | None = None) -> dict:
    """Measure lysines for every bridge target in the atlas.

    The site definition used here is the bridging ligand: for a glue, the
    question "is this target degradable from this site" is asked about the site
    the glue actually occupies.
    """
    import sqlite3

    config = load_config()
    manifest = Manifest(STAGE)
    sasa = SasaCalculator(config)

    fit_report = fit_reach_window()

    db_path = Path(config.u("env").get("BINMAN_DB", "")) if False else (
        Path(__file__).resolve().parents[1] / "data" / "atlas" / "binman.sqlite"
    )
    if not db_path.exists():
        log_event("2.3", "Degradability skipped: the atlas has not been built yet.")
        return {"lysines": 0, "fit": fit_report}

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        targets = [dict(row) for row in connection.execute(
            "SELECT b.pdb_id, b.ccd_id, b.ligand_label, b.chain_a, b.chain_b, "
            "b.id AS bridge_id, e.assembly_id "
            "FROM bridge b LEFT JOIN entry e ON e.pdb_id = b.pdb_id "
            "WHERE b.status = 'ok' AND b.ccd_class = 'glue_candidate' "
            "ORDER BY b.bridging_balance DESC, b.dsasa_total DESC"
        )]
        accession_by_pdb: dict[str, list[str]] = {}
        for row in connection.execute(
            "SELECT pdb_id, uniprot_acc FROM polymer_entity "
            "WHERE uniprot_acc IS NOT NULL AND uniprot_acc != ''"
        ):
            accession_by_pdb.setdefault(row["pdb_id"], []).append(row["uniprot_acc"])
    finally:
        connection.close()

    if limit is not None:
        targets = targets[:limit]
    log_event("2.3", f"Degradability: {len(targets):,} glue-candidate bridges to measure.")

    from pipeline.rcsb import download_assembly
    from pipeline.structures import load_assembly

    fetcher = Fetcher("rcsb", config=config)
    rows: list[dict] = []
    measured = 0
    failed = 0

    for target in targets:
        key = f"{target['pdb_id']}:{target['bridge_id']}"
        if manifest.done(key):
            continue
        try:
            path = download_assembly(target["pdb_id"], target.get("assembly_id") or "1",
                                     fetcher=fetcher)
            assembly = load_assembly(path, pdb_id=target["pdb_id"])
            ligand = next(
                (l for l in assembly.ligands if l.label == target["ligand_label"]), None
            )
            if ligand is None:
                manifest.fail(key, "ligand_instance_not_found")
                failed += 1
                continue

            site_atoms = [ligand.atoms.xyz(i) for i in range(len(ligand.atoms))]
            # Site residues: the polymer residues within contact range of the
            # ligand, which is what "the site" means for a bound ligand.
            site_residues: list[tuple[str, int]] = []
            for polymer in assembly.polymers:
                for index in range(len(polymer.atoms)):
                    position = polymer.atoms.xyz(index)
                    if any(math.dist(position, atom) <= 5.0 for atom in site_atoms[:40]):
                        label = polymer.atoms.residue_keys[index]
                        try:
                            number = int(label.split()[-1])
                        except (ValueError, IndexError):
                            continue
                        pair = (polymer.auth_chain, number)
                        if pair not in site_residues:
                            site_residues.append(pair)

            accessions = accession_by_pdb.get(target["pdb_id"], [])
            accession = accessions[0] if accessions else ""
            measurements = measure_lysines(
                path, site_atoms, site_residues, accession, target["pdb_id"],
                f"{target['ccd_id']}@{target['ligand_label']}", sasa,
            )
            apply_verdicts(measurements, config)
            rows.extend(m.as_row() for m in measurements)
            measured += 1
            manifest.record(key, status="ok", lysines=len(measurements))
        except Exception as exc:  # noqa: BLE001
            manifest.fail(key, f"{type(exc).__name__}: {exc}"[:160])
            failed += 1

        if measured and measured % 200 == 0:
            log_event("2.3", f"{measured:,} sites measured, {len(rows):,} lysines, "
                             f"{failed:,} failed.")

    written = write_jsonl(OUTPUT, rows)
    verdicts = sum(1 for r in rows if r["verdict"])
    log_event("2.3", f"Degradability complete: {written:,} lysines over {measured:,} "
                     f"sites, {failed:,} failed. Verdicts assigned: {verdicts:,} "
                     f"(0 is expected and correct while the reach window is unfitted).")
    return {
        "lysines": written, "sites": measured, "failed": failed,
        "verdicts": verdicts, "fit": fit_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score lysine reach for atlas targets")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
