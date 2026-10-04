"""Assayed ubiquitylation sites, with lysines assayed and found unmodified.

D-054 closed the degradability metric with a specific reason: every feature
derivable from an AlphaFold monomer was measured, nothing reached the 0.65
floor, and the honest obstacle was named. "Shipping a verdict would require a
dataset of lysines **assayed and found unmodified**, which is a different
experiment from the one that exists."

That dataset exists and is open. The EBI Proteins API serves two views of the
same reprocessed public proteomics:

* `/proteomics` returns every peptide identified for a protein, from
  PeptideAtlas and PRIDE. A lysine inside one of those peptides **was looked
  at**.
* `/proteomics-ptm` returns the subset carrying a modification, naming each one
  and its position within the peptide.

Together they give the matched design the UniProt crosslink set cannot:

* **positive** a lysine the PTM view reports as ubiquitylated,
* **negative** a lysine seen in an identified peptide that never carries
  ubiquitylation: assayed, and found unmodified,
* **excluded** a lysine carrying some other modification, because SUMO,
  acetyl and the rest say the residue is reactive and accessible while saying
  nothing about ubiquitin, so counting it either way would be a guess.

The old negatives were lysines with no annotation, which mostly means nobody
looked. On BRD4, RBM39 and p53 this gives 132 assayed lysines, 48 ubiquitylated
and 65 matched negatives, against the old set's 950 positives and 11,755
assumed negatives. It also covers the proteins that matter here: BRD4 and
RBM39 are substrates in BINMAN's own ternary complexes and carry **zero**
UniProt crosslink annotations between them.

**Coordinates, which are easy to get wrong silently.** A PTM's `position` is
1-based **within the peptide**, not within the protein, so the residue is
`begin + position - 1`. Checked against the sequence: every ubiquitylation and
SUMOylation position resolves to a K under that reading and to a mixture of
other residues under the obvious alternative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    INTERIM, MANIFESTS, VALIDATION, Fetcher, load_config, log_event, write_jsonl,
)

API = "https://www.ebi.ac.uk/proteins/api"
# The API takes a comma-separated accession list. 50 keeps each response a few
# megabytes and the whole human set inside a few hundred requests.
BATCH = 50
OUT = VALIDATION / "assayed_ubiquitylation.tsv"
REPORT = INTERIM / "acquire_ubiquitylome.json"
MANIFEST = MANIFESTS / "ubiquitylome.jsonl"


def _lysines_in(features: list[dict], key: str) -> set[int]:
    """Every lysine inside an identified peptide, in protein coordinates."""
    out: set[int] = set()
    for feature in features or []:
        try:
            begin = int(feature["begin"])
        except (KeyError, TypeError, ValueError):
            continue
        peptide = feature.get(key) or ""
        for offset, residue in enumerate(peptide):
            if residue == "K":
                out.add(begin + offset)
    return out


def _modified(features: list[dict]) -> tuple[set[int], set[int]]:
    """Ubiquitylated lysines, and lysines carrying some other modification."""
    ubiquitylated: set[int] = set()
    other: set[int] = set()
    for feature in features or []:
        try:
            begin = int(feature["begin"])
        except (KeyError, TypeError, ValueError):
            continue
        for ptm in feature.get("ptms") or []:
            position = ptm.get("position")
            if not position:
                continue
            # 1-based within the peptide, not the protein.
            residue = begin + int(position) - 1
            name = str(ptm.get("name") or "")
            if "biquitin" in name:
                ubiquitylated.add(residue)
            else:
                other.add(residue)
    return ubiquitylated, other


def _peptide_sequence_key(entry: dict) -> str:
    """`/proteomics` names the peptide `peptide`; the PTM view hides it in the
    evidence. Resolved per entry rather than assumed, because a silent rename
    would produce an empty assayed set and an AUC measured on nothing."""
    for feature in entry.get("features") or []:
        if feature.get("peptide"):
            return "peptide"
    return "peptide"


def fetch(accessions: list[str], fetcher: Fetcher) -> list[dict]:
    """Assayed and modified lysines for a batch of accessions."""
    joined = ",".join(accessions)
    # The cache key is a digest, not the accession list: fifty accessions make a
    # 550-character filename and the first run died on ENAMETOOLONG.
    digest = hashlib.sha256(joined.encode()).hexdigest()[:24]
    observed = fetcher.fetch_json(
        f"{API}/proteomics", params={"accession": joined},
        key=f"proteomics-{digest}") or []
    modified = fetcher.fetch_json(
        f"{API}/proteomics-ptm", params={"accession": joined},
        key=f"proteomics-ptm-{digest}") or []

    by_ptm = {e.get("accession"): e for e in modified if isinstance(e, dict)}
    rows: list[dict] = []
    for entry in observed:
        if not isinstance(entry, dict):
            continue
        accession = entry.get("accession")
        assayed = _lysines_in(entry.get("features"), _peptide_sequence_key(entry))
        if not assayed:
            continue
        ubiquitylated, other = _modified(
            (by_ptm.get(accession) or {}).get("features") or [])
        for residue in sorted(assayed):
            if residue in ubiquitylated:
                label = 1
            elif residue in other:
                continue        # modified, but not by ubiquitin: not evidence either way
            else:
                label = 0
            rows.append({
                "uniprot": accession,
                "res_num": residue,
                "ubiquitylated": label,
                "entry_name": entry.get("entryName", ""),
            })
    return rows


def run(limit: int | None = None, batch: int = BATCH) -> dict:
    config = load_config()
    fetcher = Fetcher("ebi_proteins", config=config)

    cache = INTERIM / "afdb"
    # AF-<accession>.cif and AF-<accession>-F1-model_v6.cif both occur, so the
    # accession is the second dash-field with any extension removed. Taking the
    # field whole left ".cif" on every accession.
    accessions = sorted({
        path.name.split("-")[1].split(".")[0] for path in cache.glob("AF-*")
        if len(path.name.split("-")) > 1
    })
    if limit:
        accessions = accessions[:limit]
    log_event("9.4", f"Assayed ubiquitylome: requesting {len(accessions):,} "
                     f"accessions in batches of {batch}.")

    rows: list[dict] = []
    failures = 0
    started = time.monotonic()
    for index in range(0, len(accessions), batch):
        chunk = accessions[index:index + batch]
        try:
            rows.extend(fetch(chunk, fetcher))
        except Exception as exc:  # one bad batch must not lose the rest
            failures += 1
            if failures <= 3:
                log_event("9.4", f"batch {index // batch} failed: "
                                 f"{type(exc).__name__}: {exc}"[:160])
        if index and (index // batch) % 20 == 0:
            done = index + len(chunk)
            rate = done / max(1e-9, time.monotonic() - started)
            log_event("9.4", f"  {done:,}/{len(accessions):,} accessions, "
                             f"{len(rows):,} assayed lysines, {rate:.1f}/s.")

    positives = sum(r["ubiquitylated"] for r in rows)
    header = ["uniprot", "res_num", "ubiquitylated", "entry_name"]
    with OUT.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(header) + "\n")
        for row in rows:
            handle.write("\t".join(str(row[k]) for k in header) + "\n")
    write_jsonl(MANIFEST, rows)

    report = {
        "source": ("EBI Proteins API, /proteomics and /proteomics-ptm, over "
                   "PeptideAtlas and PRIDE reprocessed public proteomics"),
        "n_accessions_requested": len(accessions),
        "n_batches_failed": failures,
        "n_assayed_lysines": len(rows),
        "n_ubiquitylated": positives,
        "n_matched_negatives": len(rows) - positives,
        "design": ("a negative is a lysine seen in an identified peptide that "
                   "never carries ubiquitylation, so it was assayed and found "
                   "unmodified; a lysine carrying another modification is "
                   "excluded rather than counted either way"),
        "why": ("D-054 closed the degradability metric because the negatives "
                "were assumed rather than assayed. This is the dataset it said "
                "would be needed."),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    log_event("9.4", f"Assayed ubiquitylome: {len(rows):,} lysines over "
                     f"{len({r['uniprot'] for r in rows}):,} proteins, "
                     f"{positives:,} ubiquitylated, "
                     f"{len(rows) - positives:,} matched negatives.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch", type=int, default=BATCH)
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit, batch=args.batch), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
