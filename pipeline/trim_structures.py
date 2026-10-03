"""Stage 1.5: write trimmed, gzipped mmCIF for the viewers (spec 1.5, 6.4).

The droplet serves a precomputed atlas, so each bridge needs a small structure
file rather than the full assembly: the two bridged chains plus everything within
`atlas.structure_trim_radius_a`, with waters dropped.

**Representatives only.** The atlas holds tens of thousands of bridges and many
share an entry. One file per (entry, ligand CCD) is written and every bridge row
in that entry pointing at that ligand references it, which keeps the bundle
inside the spec 6.5 budget without losing any viewer.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    ATLAS, INTERIM, Fetcher, Manifest, load_config, log_event, write_jsonl,
)

STAGE = "trimmed_structures"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "structures"
MAP_FILE = INTERIM / "structure_map.jsonl"
DB_PATH = ATLAS / "binman.sqlite"


def representatives(limit: int | None, min_balance: float) -> list[dict]:
    """One row per (entry, ligand), best bridge first.

    Only glue candidates get a file: a cryoprotectant bridging two chains is
    recorded in the atlas and classified, but nobody needs to look at it in 3D,
    and writing one would multiply the bundle for no gain.
    """
    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT pdb_id, ccd_id, ligand_label, chain_a, chain_b, assembly_id, "
            "       MAX(bridging_balance) AS best_balance, "
            "       MAX(dsasa_total) AS best_dsasa "
            "FROM bridge "
            "WHERE status = 'ok' AND ccd_class = 'glue_candidate' "
            "  AND symmetry_mediated = 0 AND bridging_balance >= ? "
            "GROUP BY pdb_id, ccd_id "
            "ORDER BY best_balance DESC, best_dsasa DESC",
            (min_balance,),
        ).fetchall()
    finally:
        connection.close()
    rows = [dict(r) for r in rows]
    return rows[:limit] if limit else rows


def run(limit: int | None = 4000, min_balance: float | None = None) -> dict:
    config = load_config()
    if not DB_PATH.exists():
        raise SystemExit("build the atlas first")
    if min_balance is None:
        min_balance = float(config.t("bridging.glue_balance_floor"))
    radius = float(config.t("atlas.structure_trim_radius_a"))

    manifest = Manifest(STAGE)
    fetcher = Fetcher("rcsb", config=config)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from pipeline.rcsb import download_assembly
    from pipeline.structures import write_trimmed_assembly

    targets = representatives(limit, min_balance)
    log_event("1.5", f"Trimmed structures: {len(targets):,} representative "
                     f"(entry, ligand) pairs at balance >= {min_balance}, "
                     f"trim radius {radius} A.")

    mapping: list[dict] = []
    written = failed = skipped = 0
    total_bytes = 0

    for index, target in enumerate(targets, start=1):
        key = f"{target['pdb_id']}:{target['ccd_id']}"
        name = f"{target['pdb_id']}_{target['ccd_id']}.cif.gz"
        destination = OUTPUT_DIR / name

        if manifest.done(key) and destination.exists():
            skipped += 1
            mapping.append({"pdb_id": target["pdb_id"], "ccd_id": target["ccd_id"],
                            "structure_file": name})
            total_bytes += destination.stat().st_size
            continue

        try:
            source = download_assembly(target["pdb_id"],
                                       target.get("assembly_id") or "1",
                                       fetcher=fetcher)
            keep = {
                (target["chain_a"] or "").split("/")[0],
                (target["chain_b"] or "").split("/")[0],
            } - {""}
            result = write_trimmed_assembly(
                source, destination, keep_chains=keep,
                ligand_label=target["ligand_label"], radius=radius,
            )
            written += 1
            total_bytes += result["bytes_gzipped"]
            mapping.append({"pdb_id": target["pdb_id"], "ccd_id": target["ccd_id"],
                            "structure_file": name})
            manifest.record(key, status="ok", bytes=result["bytes_gzipped"],
                            residues=result["residues"], chains=result["chains"])
        except Exception as exc:  # noqa: BLE001
            failed += 1
            manifest.fail(key, f"{type(exc).__name__}: {exc}"[:150])

        if index % 500 == 0:
            log_event("1.5", f"{index:,}/{len(targets):,} trimmed, "
                             f"{total_bytes / 1024 / 1024:.0f} MB so far, "
                             f"{failed:,} failed.")

    write_jsonl(MAP_FILE, mapping)
    counts = {
        "representatives": len(targets), "written": written, "reused": skipped,
        "failed": failed, "megabytes": round(total_bytes / 1024 / 1024, 1),
    }
    manifest.record("summary", status="ok", **counts)
    log_event("1.5", f"Trimmed structures complete: {written:,} written, "
                     f"{skipped:,} reused, {failed:,} failed, "
                     f"{counts['megabytes']} MB total.")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Write trimmed viewer structures")
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--min-balance", type=float, default=None)
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit, min_balance=args.min_balance), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
