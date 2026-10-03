"""Stage 1.1: build the entry catalogue with priority tiers (spec 1.1, 2.4).

Writes `data/manifests/catalogue.jsonl`, one row per entry, carrying the metadata
the geometry stage needs and the priority tier that orders the queue. Ordering by
tier means a partial run still yields the headline figures:

    tier 1  entries referenced by the Section 9 validation datasets
    tier 2  >= 2 distinct polymer entities and a non-polymer entity over 150 Da
    tier 3  anything else with a non-polymer entity
    tier 4  single-chain entries, needed only for the triage negative class

Within a tier, shortest first, so the cheap entries clear early and the
projection in BUILD_LOG.md is based on real throughput rather than a guess.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    MANIFESTS, VALIDATION, Fetcher, Manifest, load_config, log_event, write_jsonl,
)
from pipeline.rcsb import (  # noqa: E402
    bridging_candidate_query, fetch_entry_metadata, search_count, search_entries,
    single_chain_with_ligand_query,
)

# Spec 1.1 puts the catalogue itself at data/manifests/catalogue.jsonl, so the
# stage's own manifest must use a different name or the two would write to the
# same file and the stage row would be read back as a malformed entry.
STAGE = "catalogue_stage"
CATALOGUE = MANIFESTS / "catalogue.jsonl"

# Structures named in spec 12.3 as methods and background references. They are
# seeded into tier 1 so the canonical glues are always processed first, whatever
# else resolves. This is a processing-order choice, not a validation set: these
# entries are never used as a positive control (spec 9.1 forbids it).
SPEC_REFERENCE_ENTRIES = {
    "1FAP",  # FKBP12-rapamycin-FRB
    "5HXB",  # CRBN-DDB1-CC-885-GSPT1
    "6UML",  # CRBN-DDB1-thalidomide-SALL4
    "2P1Q",  # TIR1-auxin-IAA7
    "6TD3",  # DDB1-CDK12-cyclin K-CR8
    "4CI1", "4CI2", "4CI3",  # DDB1-CRBN with thalidomide, lenalidomide, pomalidomide
    "5FQD",  # CRBN-DDB1-lenalidomide-CK1alpha
    "6UD7", "6SJ7", "6Q0R",  # DCAF15-DDB1-DDA1-RBM39 with aryl sulfonamides
    "5HXD",
}

LIGAND_MW_FLOOR = 150.0


def validation_referenced_entries() -> set[str]:
    """Entries named by whichever validation datasets resolved.

    BioLiP2's annotation table is the only resolved source that carries PDB
    identifiers. Where the curated glue databases resolve later, their entries
    join tier 1 automatically on the next run.
    """
    referenced: set[str] = set(SPEC_REFERENCE_ENTRIES)

    artefact_codes: set[str] = set()
    artefact_path = VALIDATION / "biolip2_artefacts.tsv"
    if artefact_path.exists():
        with artefact_path.open(encoding="utf-8") as handle:
            artefact_codes = {
                (row.get("ccd_id") or "").upper()
                for row in csv.DictReader(handle, delimiter="\t")
            }

    annotations = VALIDATION / "biolip2_annotations.tsv"
    if annotations.exists():
        # The table is a million rows. Only entries carrying an artefact-listed
        # CCD are needed in tier 1: those are the exemplars spec 2.4 asks for.
        with annotations.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if (row.get("ccd_id") or "").upper() in artefact_codes:
                    pdb_id = (row.get("pdb_id") or "").upper()
                    if len(pdb_id) == 4:
                        referenced.add(pdb_id)

    for name in ("mgdb_glues", "molgluedb_glues", "mgtbind_ternary", "protacdb_protacs"):
        path = VALIDATION / f"{name}.tsv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                for key, value in row.items():
                    if "pdb" in (key or "").lower() and value:
                        for token in str(value).replace(";", ",").split(","):
                            token = token.strip().upper()
                            if len(token) == 4 and token[0].isdigit():
                                referenced.add(token)
    return referenced


def assign_tier(metadata, referenced: set[str]) -> int:
    if metadata.pdb_id in referenced:
        return 1
    if metadata.polymer_entity_count >= 2 and metadata.ligand_max_mw >= LIGAND_MW_FLOOR:
        return 2
    if metadata.nonpolymer_entity_count >= 1 and metadata.polymer_entity_count >= 2:
        return 3
    return 4


def size_proxy(metadata) -> int:
    """Cost proxy for "shortest first": polymer instances times entity count.

    The real cost is atom count, which is only known after download. Instance
    count correlates well enough to order a queue and costs nothing.
    """
    instances = 0
    for assembly in metadata.assemblies:
        if assembly["assembly_id"] == metadata.default_assembly_id:
            instances = assembly.get("polymer_instances") or 0
            break
    return max(1, instances) * max(1, metadata.polymer_entity_count)


def build(limit: int | None = None, include_tier4: bool = False,
          refresh: bool = False) -> list[dict]:
    config = load_config()
    fetcher = Fetcher("rcsb", refresh=refresh)
    manifest = Manifest(STAGE)

    referenced = validation_referenced_entries()
    log_event("1.1", f"Tier 1 seed: {len(referenced):,} entries referenced by the "
                     f"resolved validation datasets plus the spec 12.3 reference list.")

    total_candidates = search_count(bridging_candidate_query(), fetcher=fetcher)
    log_event("1.1", f"RCSB Search API: {total_candidates:,} entries with >= 2 polymer "
                     f"entities and >= 1 non-polymer entity.")

    identifiers = search_entries(bridging_candidate_query(), fetcher=fetcher, limit=limit)
    log_event("1.1", f"Retrieved {len(identifiers):,} candidate identifiers.")

    if include_tier4:
        tier4 = search_entries(
            single_chain_with_ligand_query(), fetcher=fetcher,
            limit=min(limit or 20000, 20000),
        )
        log_event("1.1", f"Retrieved {len(tier4):,} single-chain identifiers for tier 4.")
        identifiers = identifiers + [i for i in tier4 if i not in set(identifiers)]

    rows: list[dict] = []
    seen: set[str] = set()
    processed = 0
    for metadata in fetch_entry_metadata(identifiers, fetcher=fetcher):
        processed += 1
        if metadata.pdb_id in seen:
            continue
        seen.add(metadata.pdb_id)
        rows.append({
            "pdb_id": metadata.pdb_id,
            "tier": assign_tier(metadata, referenced),
            "size_proxy": size_proxy(metadata),
            "title": metadata.title,
            "method": metadata.method,
            "resolution": metadata.resolution,
            "deposit_date": metadata.deposit_date,
            "release_date": metadata.release_date,
            "organism": metadata.organism,
            "assembly_id": metadata.default_assembly_id,
            "polymer_entity_count": metadata.polymer_entity_count,
            "nonpolymer_entity_count": metadata.nonpolymer_entity_count,
            "ligand_max_mw": round(metadata.ligand_max_mw, 3),
            "uniprot_accessions": metadata.uniprot_accessions,
            "polymer_entities": metadata.polymer_entities,
            "nonpolymer_entities": metadata.nonpolymer_entities,
        })
        if processed % 2000 == 0:
            log_event("1.1", f"Metadata fetched for {processed:,} of {len(identifiers):,} entries.")

    rows.sort(key=lambda row: (row["tier"], row["size_proxy"], row["pdb_id"]))
    written = write_jsonl(CATALOGUE, rows)

    tiers: dict[int, int] = {}
    for row in rows:
        tiers[row["tier"]] = tiers.get(row["tier"], 0) + 1
    manifest.record("build", status="ok", entries=written,
                    tier_counts={str(k): v for k, v in sorted(tiers.items())},
                    total_candidates=total_candidates)
    log_event("1.1", f"Catalogue written: {written:,} entries. "
                     f"Tier counts: {dict(sorted(tiers.items()))}.")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the BINMAN entry catalogue")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap the number of candidate entries (for a smoke run)")
    parser.add_argument("--include-tier4", action="store_true",
                        help="also catalogue single-chain entries for the triage negative class")
    parser.add_argument("--refresh", action="store_true", help="bypass the response cache")
    args = parser.parse_args()

    rows = build(limit=args.limit, include_tier4=args.include_tier4, refresh=args.refresh)
    tiers: dict[int, int] = {}
    for row in rows:
        tiers[row["tier"]] = tiers.get(row["tier"], 0) + 1
    print(f"\ncatalogue: {len(rows):,} entries at {CATALOGUE}")
    for tier in sorted(tiers):
        print(f"  tier {tier}: {tiers[tier]:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
