"""Fetch Europe PMC abstracts for the curated databases' own references (spec 3.4).

Spec 3.4 allows a Task B input to be "entry title plus ligand list, **or a Europe
PMC abstract**". That second form matters: the structural inputs are limited to
what has been crystallised, and PROTACs are large and floppy so almost none have
been. 15,502 PROTACs in PROTAC-DB, 57 with a PDB entry, 32 whose chemical
component reaches the atlas. Abstracts are not limited that way.

Each abstract inherits the class of the database that cited it, so the label
still comes from a published curated source and never from this project.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import Fetcher, Manifest, VALIDATION, log_event, write_jsonl  # noqa: E402

RAW = VALIDATION / "raw"
OUTPUT = VALIDATION / "class_abstracts.jsonl"
STAGE = "task_b_abstracts"
SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def protac_dois() -> set[str]:
    path = RAW / "protac.xlsx"
    if not path.exists():
        return set()
    import openpyxl

    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True)["Sheet1"]
    stream = sheet.iter_rows(values_only=True)
    header = [str(x or "").strip() for x in next(stream)]
    if "Article DOI" not in header:
        return set()
    column = header.index("Article DOI")
    out = set()
    for row in stream:
        if not row or column >= len(row):
            continue
        value = str(row[column] or "").strip()
        if value and value.lower() != "none":
            out.add(value)
    return out


def glue_references() -> tuple[set[str], set[str]]:
    """PMIDs and DOIs cited by MGDB and MGTbind."""
    pmids: set[str] = set()
    dois: set[str] = set()
    mgdb = RAW / "mgdb_articles.csv"
    if mgdb.exists():
        for row in csv.DictReader(mgdb.open(encoding="utf-8-sig")):
            if row.get("PMID", "").strip().isdigit():
                pmids.add(row["PMID"].strip())
    mgt = RAW / "mgtbind_citations.csv"
    if mgt.exists():
        for row in csv.DictReader(mgt.open(encoding="utf-8-sig")):
            if row.get("pubmed_id", "").strip().isdigit():
                pmids.add(row["pubmed_id"].strip())
            if row.get("doi", "").strip():
                dois.add(row["doi"].strip())
    return pmids, dois


def fetch_abstract(identifier: str, kind: str, fetcher: Fetcher) -> dict | None:
    """One Europe PMC record by DOI or PMID."""
    query = f'DOI:"{identifier}"' if kind == "doi" else f"EXT_ID:{identifier}"
    try:
        payload = fetcher.fetch_json(
            SEARCH,
            params={"query": query, "format": "json", "resultType": "core",
                    "pageSize": 1},
            key=f"epmc_abs_{kind}_{identifier.replace('/', '_')[:70]}",
        )
    except Exception:  # noqa: BLE001
        return None
    results = (payload.get("resultList") or {}).get("result") or []
    if not results:
        return None
    record = results[0]
    abstract = (record.get("abstractText") or "").strip()
    if len(abstract) < 180:
        return None
    return {
        "identifier": identifier,
        "kind": kind,
        "title": (record.get("title") or "").strip(),
        "abstract": abstract,
        "journal": (record.get("journalTitle") or "").strip(),
        "year": record.get("pubYear"),
    }


def build(limit_per_class: int | None = None) -> dict:
    fetcher = Fetcher("europepmc")
    manifest = Manifest(STAGE)

    sources = {
        "protac": [(d, "doi") for d in sorted(protac_dois())],
    }
    pmids, dois = glue_references()
    sources["molecular_glue"] = (
        [(p, "pmid") for p in sorted(pmids)] + [(d, "doi") for d in sorted(dois)]
    )

    rows: list[dict] = []
    tally: dict[str, int] = {}
    for label, identifiers in sources.items():
        if limit_per_class:
            identifiers = identifiers[:limit_per_class]
        found = 0
        for index, (identifier, kind) in enumerate(identifiers, start=1):
            record = fetch_abstract(identifier, kind, fetcher)
            if record is None:
                continue
            record["label"] = label
            rows.append(record)
            found += 1
            if index % 150 == 0:
                log_event("3.4", f"Abstracts for {label}: {found:,} fetched of "
                                 f"{index:,} identifiers tried.")
        tally[label] = found
        log_event("3.4", f"Abstracts for {label}: {found:,} of "
                         f"{len(identifiers):,} identifiers resolved.")

    # One abstract can be cited by both a glue and a PROTAC database. An
    # ambiguous label is worse than none, so those are dropped.
    by_identifier: dict[str, list[dict]] = {}
    for row in rows:
        by_identifier.setdefault(row["identifier"], []).append(row)
    unambiguous = [
        group[0] for group in by_identifier.values()
        if len({g["label"] for g in group}) == 1
    ]
    dropped = len(by_identifier) - len(unambiguous)

    written = write_jsonl(OUTPUT, unambiguous)
    report = {"per_class": tally, "unique_abstracts": written,
              "dropped_ambiguous": dropped}
    manifest.record("build", status="ok", **{k: v for k, v in report.items()
                                             if isinstance(v, int)})
    log_event("3.4", f"Class abstracts: {written:,} unique, {dropped:,} dropped as "
                     f"ambiguous (cited by both a glue and a PROTAC database).")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest class-labelled abstracts")
    parser.add_argument("--limit-per-class", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(build(limit_per_class=args.limit_per_class), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
