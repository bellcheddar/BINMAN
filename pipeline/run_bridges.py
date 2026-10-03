"""Stages 1.2 to 1.4: download, geometry and classification (spec 1.2, 1.3, 1.4).

Concurrency follows spec 2.3: a thread pool downloads biological assemblies while
a process pool runs the geometry, and a geometry job is submitted the moment its
download lands rather than after the whole batch. Communication is through files
and manifests only: no shared memory, no queue service.

Resumable and idempotent. Every entry writes one manifest row, and a restart
reads the manifest and skips what is done. A failure is recorded as data
(`status = "failed:<reason>"`) and never raises past the worker, so one bad entry
cannot stop the run.

Outputs:
    data/manifests/bridges.jsonl    one row per entry: counts, timing, status
    data/interim/bridges.jsonl      one row per (entry, ligand, chain pair)
    data/interim/halves.jsonl       every half-interface considered, for the misses list
    data/reference/ccd_classes.tsv  every CCD seen, classified (spec 4.3)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import (
    FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait,
)
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    INTERIM, MANIFESTS, Fetcher, Manifest, apply_env, check_gate_g5, load_config,
    log_event, read_jsonl,
)

STAGE = "bridges"
BRIDGE_ROWS = INTERIM / "bridges.jsonl"
HALF_ROWS = INTERIM / "halves.jsonl"
CATALOGUE = MANIFESTS / "catalogue.jsonl"


# --------------------------------------------------------------------------- #
# the geometry worker: runs in a separate process
# --------------------------------------------------------------------------- #

def _geometry_worker(job: dict) -> dict:
    """Run the full geometry path on one downloaded assembly.

    Returns a plain dict so nothing but data crosses the process boundary. Every
    exception is caught and returned as a failure reason: a worker that raises
    would take its entry's result with it.
    """
    # Imports live inside the worker so each process initialises its own RDKit
    # and FreeSASA state rather than inheriting a forked copy.
    from pipeline.ccd_classes import classify, heavy_atoms_from_formula
    from pipeline.geometry import SasaCalculator, find_bridges
    from pipeline.structures import load_assembly

    pdb_id = job["pdb_id"]
    started = time.monotonic()
    try:
        config = load_config()
        assembly = load_assembly(
            job["path"], pdb_id=pdb_id, assembly_id=job["assembly_id"],
            resolution=job.get("resolution"),
        )
        if not assembly.polymers:
            return {"pdb_id": pdb_id, "status": "failed:no_polymer_chains",
                    "seconds": round(time.monotonic() - started, 3)}

        # Work cap: the bridging test is O(ligands x chains) and the tail of the
        # PDB holds assemblies where that product runs to hundreds of thousands.
        # Skipping them is recorded as data so the counts reconcile.
        chains_count = len(assembly.polymers)
        ligands_count = len(assembly.ligands)
        cap = int(config.t("bridging.max_chain_ligand_pairs"))
        if chains_count * ligands_count > cap:
            return {
                "pdb_id": pdb_id,
                "status": f"failed:too_complex:{chains_count}x{ligands_count}",
                "seconds": round(time.monotonic() - started, 3),
                "polymer_units": chains_count, "ligands_considered": ligands_count,
            }

        # CCD metadata comes from the catalogue row, so the worker makes no
        # network call of its own.
        ligand_meta = {
            (entity.get("ccd_id") or "").upper(): entity
            for entity in job.get("nonpolymer_entities", [])
        }

        classifications: dict[str, dict] = {}
        for ccd_id, entity in ligand_meta.items():
            if not ccd_id:
                continue
            heavy = heavy_atoms_from_formula(entity.get("formula", ""))
            result = classify(
                ccd_id, name=entity.get("name", ""), formula=entity.get("formula", ""),
                mw=entity.get("mw"), heavy_atoms=heavy,
                ccd_type=entity.get("ccd_type", ""), smiles=entity.get("smiles", ""),
            )
            classifications[ccd_id] = result.as_row()

        sasa = SasaCalculator(config)
        chains = assembly.chain_tuples()
        bridge_rows: list[dict] = []
        half_rows: list[dict] = []
        considered = 0

        for ligand in assembly.ligands:
            ccd_id = ligand.ccd_id.upper()
            row = classifications.get(ccd_id)
            if row is None:
                # A ligand present in the coordinates but absent from the entry
                # metadata still gets classified, from the structure alone.
                result = classify(ccd_id, heavy_atoms=ligand.heavy_atoms)
                row = result.as_row()
                classifications[ccd_id] = row
            considered += 1

            bridges, halves, reject = find_bridges(
                ligand.atoms, ccd_id, chains, config=config, sasa=sasa,
                is_glue_candidate=(row.get("ccd_class") == "glue_candidate"),
            )
            for half in halves:
                half_rows.append({
                    "pdb_id": pdb_id, "ccd_id": ccd_id,
                    "ligand_label": ligand.label, "chain": half.chain_label,
                    "entity_id": half.entity_id, "dsasa": round(half.dsasa, 2),
                    "contacts": half.contacts, "min_distance": half.min_distance,
                })
            if reject and not bridges:
                continue
            for bridge in bridges:
                record = bridge.as_row()
                record.update({
                    "pdb_id": pdb_id,
                    "assembly_id": assembly.assembly_id,
                    "ccd_class": row.get("ccd_class", "unknown"),
                    "ligand_auth_chain": ligand.auth_chain,
                    "ligand_seq_id": ligand.seq_id,
                })
                bridge_rows.append(record)

        return {
            "pdb_id": pdb_id, "status": "ok",
            "seconds": round(time.monotonic() - started, 3),
            "polymer_units": len(assembly.polymers),
            "distinct_polymer_entities": assembly.distinct_polymer_entities,
            "ligands_considered": considered,
            "bridges": len(bridge_rows),
            "bridge_rows": bridge_rows,
            "half_rows": half_rows,
            "classifications": classifications,
            "waters": assembly.waters,
            "warnings": assembly.warnings,
        }
    except Exception as exc:  # noqa: BLE001 - a worker never raises past here
        return {
            "pdb_id": pdb_id,
            "status": f"failed:geometry:{type(exc).__name__}: {exc}"[:300],
            "seconds": round(time.monotonic() - started, 3),
        }


# --------------------------------------------------------------------------- #
# the driver
# --------------------------------------------------------------------------- #

def _download(job: dict, fetcher) -> dict:
    from pipeline.rcsb import download_assembly

    try:
        path = download_assembly(job["pdb_id"], job["assembly_id"], fetcher=fetcher)
        job["path"] = str(path)
        return job
    except Exception as exc:  # noqa: BLE001
        job["download_error"] = f"{type(exc).__name__}: {exc}"[:200]
        return job


def run(max_tier: int = 3, limit: int | None = None, retry_failed: bool = False) -> dict:
    config = load_config()
    apply_env(config)

    io_workers = int(config.u("compute.io_workers"))
    cpu_workers = int(config.u("compute.cpu_workers"))

    manifest = Manifest(STAGE)
    catalogue = read_jsonl(CATALOGUE)
    if not catalogue:
        raise SystemExit("catalogue is empty: run pipeline/catalogue.py first")

    pending = [
        row for row in catalogue
        if row.get("tier", 9) <= max_tier
        and not manifest.done(row["pdb_id"], retry_failed=retry_failed)
    ]
    if limit is not None:
        pending = pending[:limit]

    log_event("1.3", f"Bridge run starting: {len(pending):,} entries pending of "
                     f"{len(catalogue):,} catalogued (tiers 1 to {max_tier}), "
                     f"{io_workers} IO workers, {cpu_workers} geometry workers.")

    if not pending:
        return manifest.counts()

    fetcher = Fetcher("rcsb")
    totals = {"entries": 0, "bridges": 0, "failed": 0, "ligands": 0, "seconds": 0.0}
    all_classifications: dict[str, dict] = {}

    bridge_handle = BRIDGE_ROWS.open("a", encoding="utf-8")
    half_handle = HALF_ROWS.open("a", encoding="utf-8")
    started = time.monotonic()
    last_log = started

    # Bounded in-flight window. An earlier revision submitted every download
    # first and only collected geometry afterwards, which meant no result was
    # recorded (and nothing was resumable) until the last of 52,761 downloads
    # landed about two hours in. Both pools are now drained in one loop, so a
    # geometry result is written the moment it is ready and a kill at any point
    # loses at most the work currently in flight.
    window = max(32, io_workers * 4)
    queue = iter(pending)
    exhausted = False

    try:
        with ThreadPoolExecutor(max_workers=io_workers) as io_pool, \
             ProcessPoolExecutor(max_workers=cpu_workers) as cpu_pool:

            downloads: dict = {}
            geometries: dict = {}

            def top_up() -> bool:
                """Keep the download window full. Returns False when the queue ends."""
                nonlocal exhausted
                while not exhausted and len(downloads) < window:
                    row = next(queue, None)
                    if row is None:
                        exhausted = True
                        break
                    downloads[io_pool.submit(_download, dict(row), fetcher)] = row["pdb_id"]
                return not exhausted

            top_up()

            while downloads or geometries:
                done, _ = wait(
                    set(downloads) | set(geometries),
                    timeout=30, return_when=FIRST_COMPLETED,
                )

                for future in done:
                    if future in downloads:
                        downloads.pop(future, None)
                        job = future.result()
                        pdb_id = job["pdb_id"]
                        if job.get("download_error"):
                            manifest.fail(pdb_id, f"download:{job['download_error']}")
                            totals["failed"] += 1
                            continue
                        geometries[cpu_pool.submit(_geometry_worker, job)] = pdb_id
                        continue

                    if future in geometries:
                        geometries.pop(future, None)
                        result = future.result()
                        pdb_id = result["pdb_id"]
                        totals["entries"] += 1
                        totals["seconds"] += result.get("seconds", 0.0)

                        if result["status"] != "ok":
                            manifest.record(pdb_id, status=result["status"],
                                            seconds=result.get("seconds"))
                            totals["failed"] += 1
                            continue

                        for row in result["bridge_rows"]:
                            bridge_handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                        for row in result["half_rows"]:
                            half_handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                        all_classifications.update(result["classifications"])

                        totals["bridges"] += result["bridges"]
                        totals["ligands"] += result["ligands_considered"]
                        manifest.record(
                            pdb_id, status="ok", bridges=result["bridges"],
                            ligands=result["ligands_considered"],
                            polymer_units=result["polymer_units"],
                            seconds=result["seconds"], waters=result["waters"],
                        )

                top_up()

                now = time.monotonic()
                if now - last_log > 300:
                    bridge_handle.flush()
                    half_handle.flush()
                    rate = totals["entries"] / max(1e-9, now - started)
                    remaining = (len(pending) - totals["entries"]) / max(1e-9, rate)
                    log_event("1.3", f"{totals['entries']:,}/{len(pending):,} entries, "
                                     f"{totals['bridges']:,} bridges, "
                                     f"{totals['failed']:,} failed, "
                                     f"{rate:.1f} entries/s, "
                                     f"~{remaining / 3600:.1f} h remaining.")
                    _write_ccd_table(all_classifications)
                    check_gate_g5(config)
                    last_log = now
    finally:
        bridge_handle.close()
        half_handle.close()

    _write_ccd_table(all_classifications)
    elapsed = time.monotonic() - started
    log_event("1.3", f"Bridge run finished: {totals['entries']:,} entries in "
                     f"{elapsed / 60:.1f} min, {totals['bridges']:,} bridges, "
                     f"{totals['failed']:,} failed, "
                     f"{totals['entries'] / max(1e-9, elapsed):.1f} entries/s.")
    totals["elapsed_seconds"] = round(elapsed, 1)
    totals["ccd_codes"] = len(all_classifications)
    return totals


def _write_ccd_table(classifications: dict[str, dict]) -> None:
    """Merge newly classified CCDs into the reference table (spec 4.3)."""
    from pipeline.ccd_classes import load_table, save_table

    if not classifications:
        return
    existing = load_table()
    existing.update(classifications)
    save_table(existing.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the BINMAN bridge geometry stage")
    parser.add_argument("--max-tier", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    totals = run(max_tier=args.max_tier, limit=args.limit, retry_failed=args.retry_failed)
    print(json.dumps(totals, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
