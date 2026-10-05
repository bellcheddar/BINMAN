"""Stage 2.1: the structural degron scan (spec 5.2).

Finds the beta-hairpin-with-exposed-glycine geometry that underlies CRBN
neosubstrate recognition, over the human AlphaFold proteome, **by geometry rather
than by sequence motif**.

Per spec 5.2:

1. Run DSSP. Find beta-hairpins: two antiparallel strands of >= `min_strand_length`
   residues connected by a turn of <= `max_turn_length` residues.
2. Identify the tip: the residue at the apex of the turn, defined as the residue
   with the greatest C-alpha distance from the strand-pair centroid.
3. Candidate when the tip or tip +/- 1 is glycine, tip-region mean pLDDT is at
   least `min_mean_plddt`, and the tip residue's relative SASA is at least
   `min_tip_rel_sasa`.
4. Score by a composite of pLDDT, exposure and hairpin regularity. The field is
   named `degron_geometry_score` because it is a **rank over geometry, not a
   calibrated probability**, and the name has to say so.

Antiparallel pairing is taken from DSSP's own bridge-partner columns rather than
inferred from strand adjacency, which would also match parallel sheets and
unpaired strands.

`motif_family` is carried on every row so DCAF-family and other degron
geometries can be added later without a schema change.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    INTERIM, Fetcher, Manifest, apply_env, load_config, log_event, write_jsonl,
)

STAGE = "degrons"
OUTPUT = INTERIM / "degrons.jsonl"
UNIPROT_STREAM = "https://rest.uniprot.org/uniprotkb/stream"
AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction"

# Theoretical maximum solvent accessibility per residue, Angstrom^2
# (Tien et al., PLoS ONE 2013, 8(11):e80635; verified via Crossref in
# references.bib as `tien_sasa`). Used to turn DSSP's absolute ACC into the
# relative SASA the spec asks for.
MAX_ASA = {
    "A": 129.0, "R": 274.0, "N": 195.0, "D": 193.0, "C": 167.0,
    "Q": 225.0, "E": 223.0, "G": 104.0, "H": 224.0, "I": 197.0,
    "L": 201.0, "K": 236.0, "M": 224.0, "F": 240.0, "P": 159.0,
    "S": 155.0, "T": 172.0, "W": 285.0, "Y": 263.0, "V": 174.0,
}
DEFAULT_MAX_ASA = 200.0

MOTIF_FAMILY = "crbn_hairpin_glycine"


# --------------------------------------------------------------------------- #
# DSSP
# --------------------------------------------------------------------------- #

@dataclass
class Residue:
    index: int            # DSSP sequential index
    res_num: int          # author numbering
    amino_acid: str
    secondary: str
    acc: float
    bridge_partners: tuple[int, int]
    ca: tuple[float, float, float] | None = None
    plddt: float | None = None

    @property
    def rel_sasa(self) -> float:
        return self.acc / MAX_ASA.get(self.amino_acid, DEFAULT_MAX_ASA)


def parse_dssp(text: str) -> list[Residue]:
    """Parse the classic DSSP format by column position.

    The classic format is fixed-width, so columns are sliced rather than split:
    a blank secondary-structure code and a negative bridge partner both break
    whitespace splitting.
    """
    residues: list[Residue] = []
    started = False
    for line in text.splitlines():
        if not started:
            if line.startswith("  #  RESIDUE"):
                started = True
            continue
        if len(line) < 38:
            continue
        # A chain break is marked with "!" in the amino-acid column.
        if line[13] == "!":
            continue
        try:
            index = int(line[0:5])
            res_num = int(line[5:10])
            acc = float(line[34:38])
            bp1 = int(line[25:29])
            bp2 = int(line[29:33])
        except ValueError:
            continue
        residues.append(Residue(
            index=index, res_num=res_num, amino_acid=line[13],
            secondary=line[16], acc=acc, bridge_partners=(bp1, bp2),
        ))
    return residues


def run_dssp(structure_path: Path) -> str:
    """Run mkdssp, falling back to pydssp when the binary is unavailable."""
    import shutil

    if shutil.which("mkdssp") is not None:
        with tempfile.NamedTemporaryFile(suffix=".dssp", delete=False) as handle:
            out_path = Path(handle.name)
        try:
            result = subprocess.run(
                ["mkdssp", "--output-format", "dssp",
                 str(structure_path), str(out_path)],
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"mkdssp exit {result.returncode}: {result.stderr.strip()[:160]}"
                )
            return out_path.read_text(errors="replace")
        finally:
            out_path.unlink(missing_ok=True)
    raise RuntimeError("mkdssp_not_installed")


# --------------------------------------------------------------------------- #
# hairpin geometry
# --------------------------------------------------------------------------- #

@dataclass
class Hairpin:
    start_res: int
    end_res: int
    strand_a: tuple[int, int]     # DSSP indices
    strand_b: tuple[int, int]
    turn_length: int
    tip_index: int
    tip_res: int
    tip_aa: str
    tip_rel_sasa: float
    mean_plddt: float
    regularity: float
    paired_bridges: int
    apex_res: int = 0
    apex_aa: str = ""
    score: float = 0.0


def strand_runs(residues: list[Residue], min_length: int) -> list[tuple[int, int]]:
    """Index ranges of consecutive extended-strand residues."""
    runs: list[tuple[int, int]] = []
    start = None
    for position, residue in enumerate(residues):
        # 'E' is an extended strand; 'B' is an isolated bridge and is not a strand.
        if residue.secondary == "E":
            if start is None:
                start = position
        else:
            if start is not None and position - start >= min_length:
                runs.append((start, position - 1))
            start = None
    if start is not None and len(residues) - start >= min_length:
        runs.append((start, len(residues) - 1))
    return runs


def count_antiparallel_bridges(residues: list[Residue],
                               strand_a: tuple[int, int],
                               strand_b: tuple[int, int]) -> int:
    """How many residues of strand A bridge to strand B, per DSSP's own pairing.

    DSSP bridge partners are sequential indices, so they map onto this list via
    the residue's `index` field. Using them is what distinguishes a genuine
    antiparallel hairpin from two strands that merely sit next to each other in
    sequence.
    """
    by_index = {residue.index: position for position, residue in enumerate(residues)}
    lower, upper = strand_b
    paired = 0
    for position in range(strand_a[0], strand_a[1] + 1):
        for partner in residues[position].bridge_partners:
            if partner <= 0:
                continue
            partner_position = by_index.get(partner)
            if partner_position is not None and lower <= partner_position <= upper:
                paired += 1
                break
    return paired


def find_hairpins(residues: list[Residue], config) -> list[Hairpin]:
    min_strand = int(config.t("degron.min_strand_length"))
    max_turn = int(config.t("degron.max_turn_length"))
    offsets = list(config.t("degron.tip_glycine_offsets"))
    min_plddt = float(config.t("degron.min_mean_plddt"))
    min_rel_sasa = float(config.t("degron.min_tip_rel_sasa"))
    w_plddt = float(config.t("degron.weight_plddt"))
    w_exposure = float(config.t("degron.weight_exposure"))
    w_regularity = float(config.t("degron.weight_regularity"))
    half_width = int(config.t("degron.tip_region_half_width"))

    runs = strand_runs(residues, min_strand)
    hairpins: list[Hairpin] = []

    for first, second in zip(runs, runs[1:]):
        turn_length = second[0] - first[1] - 1
        if turn_length < 0 or turn_length > max_turn:
            continue

        paired = count_antiparallel_bridges(residues, first, second)
        if paired == 0:
            # Two strands in sequence with no bridge between them are not a
            # hairpin, whatever the turn length.
            continue

        # The tip is the residue of the turn (plus the flanking strand ends,
        # since a two-residue turn puts the apex on the boundary) furthest from
        # the centroid of the strand pair's C-alpha atoms.
        strand_cas = [
            residues[p].ca for p in list(range(first[0], first[1] + 1))
                                 + list(range(second[0], second[1] + 1))
            if residues[p].ca is not None
        ]
        if not strand_cas:
            continue
        centroid = (
            sum(c[0] for c in strand_cas) / len(strand_cas),
            sum(c[1] for c in strand_cas) / len(strand_cas),
            sum(c[2] for c in strand_cas) / len(strand_cas),
        )
        turn_positions = list(range(first[1], second[0] + 1))
        candidates = [p for p in turn_positions if residues[p].ca is not None]
        if not candidates:
            continue
        apex_position = max(
            candidates, key=lambda p: math.dist(residues[p].ca, centroid)
        )

        # Spec 5.2 defines the tip as the turn's geometric apex and then asks
        # whether the tip or tip +/- 1 is glycine. On a six-residue turn those
        # are different residues: in IKZF1 the apex is Gln149 while the degron
        # glycine is Gly151, 7.6 A from the centroid against the apex's 11.1 A,
        # so the apex-plus-one window misses the degron entirely.
        #
        # The degron is *defined* by its exposed glycine, so the tip is taken as
        # the most apical glycine within the turn (widened by the configured
        # offsets), and the geometric apex is reported alongside it rather than
        # replaced. Where the turn holds no glycine there is no degron and the
        # hairpin is rejected, which is the same outcome as before.
        # See DECISIONS.md D-011.
        window = set()
        for position in candidates:
            for offset in offsets:
                shifted = position + offset
                if 0 <= shifted < len(residues):
                    window.add(shifted)
        glycines = [
            position for position in sorted(window)
            if residues[position].amino_acid == "G" and residues[position].ca is not None
        ]
        if not glycines:
            continue
        tip_position = max(
            glycines, key=lambda p: math.dist(residues[p].ca, centroid)
        )
        tip = residues[tip_position]
        apex = residues[apex_position]

        region = [
            residues[p] for p in range(
                max(0, tip_position - half_width),
                min(len(residues), tip_position + half_width + 1),
            )
        ]
        plddts = [r.plddt for r in region if r.plddt is not None]
        mean_plddt = sum(plddts) / len(plddts) if plddts else 0.0
        if mean_plddt < min_plddt:
            continue

        tip_rel_sasa = tip.rel_sasa
        if tip_rel_sasa < min_rel_sasa:
            continue

        # Regularity: what fraction of the shorter strand is actually bridged.
        shorter = min(first[1] - first[0] + 1, second[1] - second[0] + 1)
        regularity = min(1.0, paired / max(1, shorter))

        score = round(
            w_plddt * min(1.0, mean_plddt / 100.0)
            + w_exposure * min(1.0, tip_rel_sasa)
            + w_regularity * regularity,
            6,
        )

        hairpins.append(Hairpin(
            start_res=residues[first[0]].res_num,
            end_res=residues[second[1]].res_num,
            apex_res=apex.res_num, apex_aa=apex.amino_acid,
            strand_a=first, strand_b=second, turn_length=turn_length,
            tip_index=tip_position, tip_res=tip.res_num, tip_aa=tip.amino_acid,
            tip_rel_sasa=round(tip_rel_sasa, 4),
            mean_plddt=round(mean_plddt, 2),
            regularity=round(regularity, 4),
            paired_bridges=paired, score=score,
        ))
    return hairpins


# --------------------------------------------------------------------------- #
# worker
# --------------------------------------------------------------------------- #

def _scan_worker(job: dict) -> dict:
    """DSSP plus hairpin detection for one AlphaFold model.

    Returns a plain dict; every exception becomes a failure reason so one bad
    model cannot stop the scan.
    """
    import gemmi

    accession = job["accession"]
    path = Path(job["path"])
    try:
        config = load_config()
        text = run_dssp(path)
        residues = parse_dssp(text)
        if not residues:
            return {"accession": accession, "status": "failed:dssp_no_residues"}

        # C-alpha coordinates and pLDDT from the model itself. AlphaFold puts
        # per-residue pLDDT in the B-factor column.
        structure = gemmi.read_structure(str(path))
        structure.setup_entities()
        by_res_num: dict[int, tuple] = {}
        for chain in structure[0]:
            for residue in chain:
                ca = residue.find_atom("CA", "*")
                if ca is None:
                    continue
                by_res_num[residue.seqid.num] = (
                    (ca.pos.x, ca.pos.y, ca.pos.z), float(ca.b_iso)
                )
        for residue in residues:
            found = by_res_num.get(residue.res_num)
            if found:
                residue.ca, residue.plddt = found

        hairpins = find_hairpins(residues, config)
        return {
            "accession": accession, "status": "ok",
            "residues": len(residues),
            "strands": sum(1 for r in residues if r.secondary == "E"),
            "hairpins": [
                {
                    "uniprot_acc": accession,
                    "afdb_id": job.get("afdb_id", f"AF-{accession}-F1"),
                    "gene": job.get("gene", ""),
                    "start_res": h.start_res, "end_res": h.end_res,
                    "tip_res": h.tip_res, "tip_aa": h.tip_aa,
                    "apex_res": h.apex_res, "apex_aa": h.apex_aa,
                    "turn_length": h.turn_length,
                    "mean_plddt": h.mean_plddt,
                    "tip_rel_sasa": h.tip_rel_sasa,
                    # Emitted so all three components of the score below are on
                    # the row that carries it. Without this one the score could
                    # not be taken apart after the fact.
                    "regularity": h.regularity,
                    "degron_geometry_score": h.score,
                    "motif_family": MOTIF_FAMILY,
                    "is_known_neosubstrate": 0,
                    "structure_file": "",
                    "status": "ok",
                }
                for h in hairpins
            ],
        }
    except Exception as exc:  # noqa: BLE001
        return {"accession": accession,
                "status": f"failed:{type(exc).__name__}: {exc}"[:200]}
    finally:
        if job.get("cleanup"):
            path.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def human_proteome(fetcher: Fetcher) -> list[dict]:
    """Reviewed human proteins, which is the set AFDB covers completely."""
    payload = fetcher.fetch_json(
        UNIPROT_STREAM,
        params={"query": "(organism_id:9606) AND (reviewed:true)",
                "fields": "accession,gene_primary", "format": "json",
                "compressed": "false"},
        key="uniprot_human_reviewed",
    )
    rows = []
    for record in payload.get("results", []) or []:
        genes = record.get("genes") or []
        gene = ((genes[0].get("geneName") or {}).get("value")) if genes else ""
        rows.append({"accession": record["primaryAccession"], "gene": gene or ""})
    return rows


def download_model(accession: str, fetcher: Fetcher, cache: Path) -> Path | None:
    """Fetch the AlphaFold mmCIF, resolving the model version from the API."""
    dest = cache / f"AF-{accession}.cif"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        meta = fetcher.fetch_json(f"{AFDB_API}/{accession}", key=f"afdb_meta_{accession}")
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(meta, list) or not meta:
        return None
    url = meta[0].get("cifUrl")
    if not url:
        return None
    try:
        data = fetcher.fetch_bytes(url, key=f"afdb_cif_{accession}")
    except Exception:  # noqa: BLE001
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def run(limit: int | None = None, retry_failed: bool = False) -> dict:
    config = load_config()
    apply_env(config)
    cpu_workers = int(config.u("compute.dssp_workers"))
    io_workers = int(config.u("compute.io_workers"))

    fetcher = Fetcher("afdb", config=config)
    manifest = Manifest(STAGE)
    cache = Path(config.u("env").get("BINMAN_AFDB_CACHE", "")) if False else (
        INTERIM / "afdb"
    )
    cache.mkdir(parents=True, exist_ok=True)

    proteome = human_proteome(fetcher)
    log_event("2.1", f"Human reviewed proteome: {len(proteome):,} accessions.")

    pending = [
        row for row in proteome
        if not manifest.done(row["accession"], retry_failed=retry_failed)
    ]
    if limit is not None:
        pending = pending[:limit]
    log_event("2.1", f"Degron scan: {len(pending):,} accessions pending, "
                     f"{io_workers} IO workers, {cpu_workers} DSSP workers.")

    if not pending:
        return {"scanned": 0, "degrons": 0}

    from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

    rows: list[dict] = []
    totals = {"scanned": 0, "degrons": 0, "failed": 0}
    import time
    started = time.monotonic()
    last_log = started
    window = max(32, io_workers * 4)
    queue = iter(pending)
    exhausted = False

    handle = (INTERIM / "degrons_stream.jsonl").open("a", encoding="utf-8")
    try:
        with ThreadPoolExecutor(max_workers=io_workers) as io_pool, \
             ProcessPoolExecutor(max_workers=cpu_workers) as cpu_pool:

            downloads: dict = {}
            scans: dict = {}

            def fetch(row: dict) -> dict:
                path = download_model(row["accession"], fetcher, cache)
                return {**row, "path": str(path) if path else "",
                        "afdb_id": f"AF-{row['accession']}-F1"}

            def top_up() -> None:
                nonlocal exhausted
                while not exhausted and len(downloads) < window:
                    row = next(queue, None)
                    if row is None:
                        exhausted = True
                        break
                    downloads[io_pool.submit(fetch, row)] = row["accession"]

            top_up()

            while downloads or scans:
                done, _ = wait(set(downloads) | set(scans), timeout=60,
                               return_when=FIRST_COMPLETED)
                for future in done:
                    if future in downloads:
                        downloads.pop(future, None)
                        job = future.result()
                        if not job.get("path"):
                            manifest.fail(job["accession"], "afdb_model_unavailable")
                            totals["failed"] += 1
                            continue
                        scans[cpu_pool.submit(_scan_worker, job)] = job["accession"]
                        continue

                    scans.pop(future, None)
                    result = future.result()
                    accession = result["accession"]
                    totals["scanned"] += 1
                    if result["status"] != "ok":
                        manifest.record(accession, status=result["status"])
                        totals["failed"] += 1
                        continue
                    hairpins = result.get("hairpins", [])
                    for hairpin in hairpins:
                        handle.write(json.dumps(hairpin, separators=(",", ":")) + "\n")
                        rows.append(hairpin)
                    totals["degrons"] += len(hairpins)
                    manifest.record(accession, status="ok",
                                    degrons=len(hairpins),
                                    residues=result.get("residues"),
                                    strands=result.get("strands"))

                top_up()
                now = time.monotonic()
                if now - last_log > 300:
                    handle.flush()
                    rate = totals["scanned"] / max(1e-9, now - started)
                    remaining = (len(pending) - totals["scanned"]) / max(1e-9, rate)
                    log_event("2.1", f"{totals['scanned']:,}/{len(pending):,} scanned, "
                                     f"{totals['degrons']:,} candidates, "
                                     f"{totals['failed']:,} failed, {rate:.1f}/s, "
                                     f"~{remaining / 3600:.1f} h remaining.")
                    last_log = now
    finally:
        handle.close()

    # The stream file is the durable record across restarts; the output is the
    # whole set, so it is rebuilt from the stream rather than from this run.
    stream = INTERIM / "degrons_stream.jsonl"
    all_rows = []
    seen = set()
    if stream.exists():
        with stream.open(encoding="utf-8") as reader:
            for line in reader:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (row.get("uniprot_acc"), row.get("tip_res"), row.get("start_res"))
                if key in seen:
                    continue
                seen.add(key)
                all_rows.append(row)
    written = write_jsonl(OUTPUT, all_rows)

    log_event("2.1", f"Degron scan complete: {totals['scanned']:,} proteins scanned, "
                     f"{written:,} candidate degrons written, {totals['failed']:,} failed.")
    return {**totals, "written": written}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan the human proteome for structural degrons")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit, retry_failed=args.retry_failed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
