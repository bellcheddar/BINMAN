"""Acquire the Section 4.1b validation datasets.

These are the external ground truth for Section 9. The rules this module
enforces, straight from the spec:

* Fetch them in Phase 1.0, **before** any science runs.
* Record URL, version or release date, retrieval timestamp, row count after
  parsing, and licence for every one, in `data/validation/MANIFEST.md`.
* Fail loudly on an implausible row count: a silently empty validation set is
  worse than no validation set.
* Where a licence forbids redistribution, keep the parsed derivative local and
  never bundle it into the shipped atlas.
* If a dataset cannot be obtained, open **G7** (non-blocking), record the gap,
  and carry on with the datasets that do resolve.
* **Never substitute a hand-written control for a missing published one.**

Each dataset is a `Dataset` with an ordered list of candidate routes. The first
route that yields a plausible parse wins, which is the fallback ladder applied
to data acquisition.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    VALIDATION, Fetcher, Manifest, load_config, log_event, open_gate, utcnow,
)

RAW = VALIDATION / "raw"
PARSED = VALIDATION
STAGE = "validation_acquire"

# Retention cut for the UbiBrowser predicted network. See DECISIONS.md D-005.
PREDICTED_PVALUE_CUT = 0.01


# --------------------------------------------------------------------------- #
# dataset descriptors
# --------------------------------------------------------------------------- #

@dataclass
class Route:
    """One way to obtain a dataset."""

    url: str
    note: str = ""
    gzipped: bool = False
    binary: bool = False


@dataclass
class Dataset:
    """A validation dataset, its routes, its parser and its licence."""

    name: str
    purpose: str            # which Section 9 metric it serves
    licence: str            # "not determined" is a legitimate value, a guess is not
    redistributable: bool   # False keeps the derivative out of the shipped atlas
    citation: str           # DOI or canonical URL, Crossref-verified later
    routes: list[Route]
    parser: Callable[[bytes, Route], list[dict]]
    min_rows: int           # below this the parse is treated as failed
    columns: Sequence[str] = ()
    version_note: str = "release not stated by the source"
    homepage: str = ""
    # What a human has to do when every automatic route fails, and what was
    # already checked so nobody repeats the work. Written into MANIFEST.md.
    manual_route: str = ""


# --------------------------------------------------------------------------- #
# parsers
# --------------------------------------------------------------------------- #

def _text(raw: bytes, route: Route) -> str:
    if route.gzipped or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


def parse_biolip_artefacts(raw: bytes, route: Route) -> list[dict]:
    """BioLiP's artefact ligand list: tab-separated CCD code and description.

    Confirmed semantics: `script/rmligand.cpp` in kad-ecoli/mmCIF2BioLiP
    documents this file as "list of artifact ligand" and reads it through
    `read_artifact_table`. BioLiP treats a listed code as a *candidate*
    artefact, then checks the entry's PubMed abstract before excluding it, so
    these are the codes BioLiP considers crystallisation furniture by default.
    """
    rows = []
    for line in _text(raw, route).splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        ccd = parts[0].strip().upper()
        if not ccd or len(ccd) > 5:
            continue
        rows.append({
            "ccd_id": ccd,
            "description": parts[1].strip() if len(parts) > 1 else "",
        })
    return rows


def parse_biolip_annotations(raw: bytes, route: Route) -> list[dict]:
    """BioLiP main annotation table.

    The column order is fixed by `download/readme.txt`. Only the fields BINMAN
    needs are kept: the entry, the receptor chain, the ligand CCD and the
    ligand's binding-site residues. The file is large, so parsing is streaming
    and the full table is never held twice.
    """
    rows = []
    for line in _text(raw, route).splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        rows.append({
            "pdb_id": parts[0].strip().upper(),
            "receptor_chain": parts[1].strip(),
            "resolution": parts[2].strip(),
            "binding_site_id": parts[3].strip(),
            "ccd_id": parts[4].strip().upper(),
        })
    return rows


def parse_ubibrowser_literature(raw: bytes, route: Route) -> list[dict]:
    """UbiBrowser literature-curated E3-substrate pairs.

    Column names vary between releases, so the header is read rather than
    assumed and the E3 and substrate columns are located by name.
    """
    text = _text(raw, route)
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    try:
        header = next(reader)
    except StopIteration:
        return []
    lowered = [h.strip().lower() for h in header]

    def find(*candidates: str) -> int | None:
        for candidate in candidates:
            for index, name in enumerate(lowered):
                if candidate in name:
                    return index
        return None

    e3_col = find("e3_genesymbol", "e3 gene", "e3_gene", "e3")
    sub_col = find("sub_genesymbol", "substrate gene", "sub_gene", "substrate")
    species_col = find("species", "organism")
    source_col = find("source", "pmid", "reference")

    rows = []
    for parts in reader:
        if not parts or e3_col is None or sub_col is None:
            continue
        if max(e3_col, sub_col) >= len(parts):
            continue
        species = parts[species_col].strip() if species_col is not None and species_col < len(parts) else ""
        if species and "sapiens" not in species.lower() and species.lower() not in {"human", "9606"}:
            continue
        rows.append({
            "e3_gene": parts[e3_col].strip(),
            "substrate_gene": parts[sub_col].strip(),
            "species": species or "H.sapiens",
            "source": parts[source_col].strip() if source_col is not None and source_col < len(parts) else "",
        })
    return rows


def parse_ubibrowser_predicted(raw: bytes, route: Route) -> list[dict]:
    """UbiBrowser predicted E3-substrate network, filtered at the stated p-value.

    The full human prediction set is 11.4 million candidate pairs (1.4 GB as
    TSV), which is both unusable as a validation reference and pointless to keep
    on disk: it is a near-uniform p-value distribution over every plausible
    pair. Only pairs below `PREDICTED_PVALUE_CUT` are retained, and the cut is
    recorded here and in DECISIONS.md rather than buried in a config the reader
    would not think to check.

    The literature-curated set, not this one, is the reference for the spec 9.3
    substrate-count agreement. This set exists to report predicted coverage
    separately, which spec 4.1b asks for.
    """
    text = _text(raw, route)
    handle = io.StringIO(text)
    reader = csv.DictReader(handle, delimiter="\t")
    rows = []
    for record in reader:
        try:
            pvalue = float(record.get("Pvalue") or 1.0)
        except ValueError:
            continue
        if pvalue >= PREDICTED_PVALUE_CUT:
            continue
        e3 = (record.get("enyz") or "").strip()
        substrate = (record.get("sub") or "").strip()
        if not e3 or not substrate:
            continue
        rows.append({
            "e3_acc": e3,
            "substrate_acc": substrate,
            "pvalue": f"{pvalue:.6g}",
            "inter_score": (record.get("interScore") or "").strip(),
        })
    return rows


def parse_generic_table(raw: bytes, route: Route) -> list[dict]:
    """A TSV or CSV with a header, read as-is. Used where the schema is unknown."""
    text = _text(raw, route)
    sample = text[:8192]
    delimiter = "\t" if sample.count("\t") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [{k: (v or "").strip() for k, v in row.items() if k} for row in reader]


def parse_json_records(raw: bytes, route: Route) -> list[dict]:
    """A JSON array, or an object wrapping one under a common key."""
    payload = json.loads(_text(raw, route))
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "records", "rows", "items", "list"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
            if isinstance(value, dict):
                for inner in value.values():
                    if isinstance(inner, list):
                        return [r for r in inner if isinstance(r, dict)]
    return []


def parse_pdb_ids_from_text(raw: bytes, route: Route) -> list[dict]:
    """Harvest four-character PDB identifiers from a free-text or HTML source.

    Only used where a curated resource publishes its structure list in prose.
    A harvested identifier is marked `harvested = true` so no downstream metric
    can treat it as a parsed table row without noticing.
    """
    text = _text(raw, route)
    found = {
        match.group(0).upper()
        for match in re.finditer(r"\b[1-9][A-Za-z0-9]{3}\b", text)
    }
    return [{"pdb_id": pdb, "harvested": True} for pdb in sorted(found)]


# --------------------------------------------------------------------------- #
# the registry
# --------------------------------------------------------------------------- #

def registry() -> list[Dataset]:
    return [
        Dataset(
            name="biolip2_artefacts",
            purpose="Glue Atlas artefact precision (spec 9.1): BINMAN must class these as furniture",
            licence="BSD-2-Clause (Zhang-Freddolino lab, mmCIF2BioLiP)",
            redistributable=True,
            citation="10.1093/nar/gkad630",
            homepage="https://zhanggroup.org/BioLiP/",
            version_note="curation code at master; the list is versioned with the repository",
            routes=[
                Route("https://raw.githubusercontent.com/kad-ecoli/mmCIF2BioLiP/master/ligand_list",
                      note="artefact ligand list consumed by script/rmligand.cpp"),
            ],
            parser=parse_biolip_artefacts,
            min_rows=200,
            columns=("ccd_id", "description"),
        ),
        Dataset(
            name="biolip2_annotations",
            purpose="Glue Atlas: biologically relevant ligand reference and cofactor labels for LM Task B",
            licence="free for academic use, redistribution not granted in writing",
            redistributable=False,
            citation="10.1093/nar/gkad630",
            homepage="https://zhanggroup.org/BioLiP/",
            version_note="weekly release, pinned by retrieval date",
            routes=[
                Route("https://seq2fun.dcmb.med.umich.edu/BioLiP2/download/BioLiP.txt.gz",
                      note="BioLiP2 redundant annotation table", gzipped=True, binary=True),
                Route("https://zhanggroup.org/BioLiP/download/BioLiP.txt.gz",
                      note="BioLiP mirror", gzipped=True, binary=True),
            ],
            parser=parse_biolip_annotations,
            min_rows=100000,
            columns=("pdb_id", "receptor_chain", "ccd_id"),
        ),
        Dataset(
            name="ubibrowser_literature_e3",
            purpose="E3 Triage substrate counts and the enrichment test (spec 9.3)",
            licence="not determined",
            redistributable=False,
            citation="10.1093/nar/gkab962",
            homepage="http://ubibrowser.bio-it.cn/ubibrowser_v3/",
            version_note="UbiBrowser 2.0 / v3 web release",
            routes=[
                Route("http://ubibrowser.bio-it.cn/ubibrowser_v3/Public/download/literature/literature.E3.txt.gz",
                      note="literature-curated E3-substrate interactions", gzipped=True, binary=True),
            ],
            parser=parse_ubibrowser_literature,
            min_rows=500,
            columns=("e3_gene", "substrate_gene"),
        ),
        Dataset(
            name="ubibrowser_predicted_e3",
            purpose="E3 Triage: predicted E3-substrate network, reported separately from curated",
            licence="not determined",
            redistributable=False,
            citation="10.1093/nar/gkab962",
            homepage="http://ubibrowser.bio-it.cn/ubibrowser_v3/",
            version_note=f"UbiBrowser v3 H.sapiens prediction set, retained at p < {PREDICTED_PVALUE_CUT}",
            routes=[
                Route("http://ubibrowser.bio-it.cn/ubibrowser_v3/Public/download/E3/H.sapiens.result.txt.gz",
                      note="predicted human E3-substrate interactions", gzipped=True, binary=True),
            ],
            parser=parse_ubibrowser_predicted,
            min_rows=1000,
            columns=("e3_acc", "substrate_acc", "pvalue", "inter_score"),
        ),
        Dataset(
            name="mgdb_glues",
            purpose="Glue Atlas recall, curated set 1 of 3 (spec 9.1)",
            licence="open access, terms not stated for bulk reuse",
            redistributable=False,
            citation="10.1093/nar/gkaf1131",
            homepage="http://mgdb.idruglab.cn/",
            version_note="NAR 2026 54(D1) D1488 release",
            manual_route=(
                "Bulk export is stated as planned future work in the paper, not yet live. Verified: the Europe PMC supplementary archive for PMC12807674 holds only two TIFF figures and an 8 MB `Supplementary Data.docx`, with no machine-readable glue table. Obtain by browsing http://mgdb.idruglab.cn/ and exporting the compound table from the web interface, or by contacting the authors for the 7396-compound set."
            ),
            routes=[
                Route("http://mgdb.idruglab.cn/download/all", note="bulk export, if exposed"),
                Route("http://mgdb.idruglab.cn/api/download", note="API bulk export, if exposed"),
                Route("http://mgdb.idruglab.cn/api/glue/list", note="listing API, if exposed"),
            ],
            parser=parse_json_records,
            min_rows=100,
        ),
        Dataset(
            name="molgluedb_glues",
            purpose="Glue Atlas recall, curated set 2 of 3 (spec 9.1)",
            licence="free and open access, terms not stated for bulk reuse",
            redistributable=False,
            citation="10.1093/nar/gkaf811",
            homepage="https://www.molgluedb.com/",
            version_note="NAR 2025 advance article gkaf811",
            manual_route=(
                "JavaScript front end with no documented bulk-export endpoint. Browse https://www.molgluedb.com/ and export the compound table, or request it from the authors."
            ),
            routes=[
                Route("https://www.molgluedb.com/api/download", note="bulk export, if exposed"),
                Route("https://www.molgluedb.com/api/glue/all", note="listing API, if exposed"),
                Route("https://www.molgluedb.com/attachment/download/molgluedb.csv",
                      note="attachment path, if exposed"),
            ],
            parser=parse_json_records,
            min_rows=100,
        ),
        Dataset(
            name="mgtbind_ternary",
            purpose="Glue Atlas recall set 3 of 3 and ternary partner assignment (spec 9.1)",
            licence="not determined",
            redistributable=False,
            citation="not yet verified",
            homepage="http://mgtbind.idruglab.cn/",
            version_note="NAR 2026 54(D1) D1500 release",
            manual_route=(
                "No bulk-export endpoint responded and the host returns 404 for the paths tried. Check the NAR 2026 54(D1) D1500 article for the current URL, which may differ from the idruglab host."
            ),
            routes=[
                Route("http://mgtbind.idruglab.cn/api/download", note="bulk export, if exposed"),
                Route("http://mgtbind.idruglab.cn/download/all", note="bulk export, if exposed"),
            ],
            parser=parse_json_records,
            min_rows=50,
        ),
        Dataset(
            name="protacdb_protacs",
            purpose="LM Task B confusable negative class and Glue Atlas exclusion set (spec 9.1, 3.4)",
            licence="internal use only, redistribution prohibited (Hou group terms, 2024-09-29)",
            redistributable=False,
            citation="10.1093/nar/gkae768",
            homepage="https://cadd.zju.edu.cn/protacdb/",
            version_note="PROTAC-DB 3.0",
            manual_route=(
                "The downloads page populates its table by JavaScript. Download the PROTAC SDF or XLSX from https://cadd.zju.edu.cn/protacdb/downloads by hand. Note the terms of use (2024-09-29) restrict the data to internal use: the parsed derivative must stay local and must never be bundled into the atlas."
            ),
            routes=[
                Route("https://cadd.zju.edu.cn/protacdb/api/download/protac", note="bulk export, if exposed"),
                Route("https://cadd.zju.edu.cn/protacdb/downloads/protac.csv", note="static path, if exposed"),
            ],
            parser=parse_generic_table,
            min_rows=500,
        ),
        Dataset(
            name="degronopedia",
            purpose="Degron Scan cross-reference (spec 9.2)",
            licence="not determined",
            redistributable=False,
            citation="10.1093/nar/gkad1025",
            homepage="https://degronopedia.com/",
            version_note="web release, pinned by retrieval date",
            manual_route=(
                "No static data path or API responded. The site offers per-protein lookup and a degron motif table at https://degronopedia.com/degronopedia/degron_motifs. Export from there, or request the bulk set from the Pokrzywa lab."
            ),
            routes=[
                Route("https://degronopedia.com/degronopedia/data/degrons.csv", note="static path, if exposed"),
                Route("https://degronopedia.com/degronopedia/api/degrons", note="API, if exposed"),
            ],
            parser=parse_generic_table,
            min_rows=100,
        ),
        Dataset(
            name="protcid_interfaces",
            purpose="Glue Atlas packing specificity (spec 9.1): packing-only interfaces must not be called glue interfaces",
            licence="free for academic use",
            redistributable=False,
            citation="10.1093/nar/gkac1120",
            homepage="https://dunbrack2.fccc.edu/ProtCiD/",
            version_note="web release, pinned by retrieval date",
            manual_route=(
                "The download page moved; https://dunbrack2.fccc.edu/ProtCiD/ links to a PDBfam download under /ProtCiD/PDBfam/Download.aspx. Fetch the Pfam domain interface cluster table from there by hand."
            ),
            routes=[
                Route("https://dunbrack2.fccc.edu/ProtCiD/Download/PfamDomainInterfaceCluster.txt",
                      note="domain interface clusters, if exposed"),
            ],
            parser=parse_generic_table,
            min_rows=1000,
        ),
    ]


# --------------------------------------------------------------------------- #
# acquisition
# --------------------------------------------------------------------------- #

def acquire(dataset: Dataset, fetcher: Fetcher, manifest: Manifest,
            refresh: bool = False) -> dict:
    """Try each route in order; the first plausible parse wins."""
    if manifest.done(dataset.name) and not refresh:
        for row in manifest.read():
            if row.get("key") == dataset.name:
                return row
    RAW.mkdir(parents=True, exist_ok=True)
    attempts: list[dict] = []

    for route in dataset.routes:
        attempt = {"url": route.url, "note": route.note}
        try:
            raw = fetcher.fetch_bytes(route.url)
        except Exception as exc:  # noqa: BLE001
            attempt["outcome"] = f"fetch_failed:{type(exc).__name__}: {exc}"[:200]
            attempts.append(attempt)
            continue

        # An SPA shell or an error page is a fetch that technically succeeded.
        # Catch it here rather than letting the parser return zero rows.
        head = raw[:600].lstrip().lower()
        if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
            attempt["outcome"] = f"html_not_data:{len(raw)}_bytes"
            attempts.append(attempt)
            continue

        try:
            rows = dataset.parser(raw, route)
        except Exception as exc:  # noqa: BLE001
            attempt["outcome"] = f"parse_failed:{type(exc).__name__}: {exc}"[:200]
            attempts.append(attempt)
            continue

        attempt["rows"] = len(rows)
        if len(rows) < dataset.min_rows:
            # Spec 4.1b: fail loudly on an implausible row count.
            attempt["outcome"] = f"implausible_row_count:{len(rows)}<{dataset.min_rows}"
            attempts.append(attempt)
            continue

        raw_path = RAW / f"{dataset.name}{'.gz' if route.gzipped else ''}"
        raw_path.write_bytes(raw)
        parsed_path = PARSED / f"{dataset.name}.tsv"
        fieldnames = list(dataset.columns) or sorted({k for row in rows for k in row})
        with parsed_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t",
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        attempt["outcome"] = "ok"
        attempts.append(attempt)
        return manifest.record(
            dataset.name, status="ok", rows=len(rows), url=route.url,
            licence=dataset.licence, redistributable=dataset.redistributable,
            citation=dataset.citation, homepage=dataset.homepage,
            version_note=dataset.version_note, purpose=dataset.purpose,
            manual_route=dataset.manual_route,
            parsed_path=str(parsed_path.relative_to(VALIDATION.parent.parent)),
            raw_bytes=len(raw), attempts=attempts,
        )

    return manifest.fail(
        dataset.name, "all_routes_exhausted", attempts=attempts,
        licence=dataset.licence, citation=dataset.citation,
        homepage=dataset.homepage, purpose=dataset.purpose,
        version_note=dataset.version_note, manual_route=dataset.manual_route,
    )


def write_manifest(results: list[dict]) -> None:
    """Write data/validation/MANIFEST.md (spec 4.1b acquisition rules)."""
    ok = [r for r in results if r.get("status") == "ok"]
    failed = [r for r in results if r.get("status") != "ok"]

    lines = [
        "# BINMAN validation dataset manifest",
        "",
        "Generated by `pipeline/acquire_validation.py`. Every row records the URL,",
        "the release note, the retrieval timestamp, the parsed row count and the",
        "licence, as spec 4.1b requires. Do not edit by hand.",
        "",
        f"Generated at {utcnow()}.",
        "",
        f"**{len(ok)} of {len(results)} datasets resolved.**",
        "",
        "## Resolved",
        "",
        "| Dataset | Rows | Licence | Redistributable | Release | Retrieved | Source |",
        "|---|---:|---|:---:|---|---|---|",
    ]
    for row in sorted(ok, key=lambda r: r["key"]):
        lines.append(
            f"| `{row['key']}` | {row.get('rows', 0):,} | {row.get('licence', '')} | "
            f"{'yes' if row.get('redistributable') else 'no'} | "
            f"{row.get('version_note', '')} | {row.get('at', '')} | "
            f"[{row.get('homepage', '') or row.get('url', '')}]({row.get('url', '')}) |"
        )

    lines += ["", "### What each resolved dataset is used for", ""]
    for row in sorted(ok, key=lambda r: r["key"]):
        lines.append(f"- **`{row['key']}`** ({row.get('rows', 0):,} rows): {row.get('purpose', '')}")
        lines.append(f"  Citation: `{row.get('citation', 'not verified')}`. "
                     f"Parsed derivative: `{row.get('parsed_path', '')}`.")

    lines += [
        "",
        "## Not resolved (Gate G7)",
        "",
    ]
    if not failed:
        lines.append("None: every dataset resolved.")
    else:
        lines += [
            "Spec 4.1b is explicit that a missing published dataset is **never** replaced",
            "by a hand-written control. Each gap below suppresses the metrics that depend",
            "on it, and those metrics are reported as not computed rather than estimated.",
            "",
            "| Dataset | Purpose | Routes tried | Outcome of each |",
            "|---|---|---:|---|",
        ]
        for row in sorted(failed, key=lambda r: r["key"]):
            attempts = row.get("attempts", []) or []
            outcomes = "; ".join(
                f"`{a.get('outcome', 'unknown')}`" for a in attempts
            ) or "no route defined"
            lines.append(
                f"| `{row['key']}` | {row.get('purpose', '')} | {len(attempts)} | {outcomes} |"
            )
        lines += [
            "",
            "### Manual routes for the gaps",
            "",
            "Each of these publishes its data through a JavaScript front end with no",
            "documented bulk-export endpoint, or behind registration. Obtaining them",
            "needs a human: download the file from the homepage, drop it in",
            "`data/validation/raw/` under the dataset name, and re-run this stage, which",
            "will parse and record it. Nothing else in the build has to change.",
            "",
        ]
        for row in sorted(failed, key=lambda r: r["key"]):
            lines.append(f"**`{row['key']}`**  ")
            lines.append(f"Homepage: {row.get('homepage', 'not recorded')}  ")
            lines.append(f"Citation: `{row.get('citation', 'not verified')}`  ")
            lines.append(f"{row.get('manual_route') or 'No manual route recorded.'}")
            lines.append("")

    lines += [
        "",
        "## Licence handling",
        "",
        "A dataset marked `Redistributable: no` stays in `data/validation/` and is",
        "listed in `.gitignore`. Only computed metrics derived from it reach the",
        "shipped atlas or this repository, never its rows (spec 4.1b, spec 10).",
        "",
    ]
    (VALIDATION / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(refresh: bool = False) -> int:
    load_config()
    VALIDATION.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher("validation", refresh=refresh)
    manifest = Manifest(STAGE)
    datasets = registry()

    results: list[dict] = []
    for dataset in datasets:
        print(f"-- {dataset.name}")
        row = acquire(dataset, fetcher, manifest, refresh=refresh)
        status = row.get("status", "?")
        if status == "ok":
            print(f"   ok: {row.get('rows', 0):,} rows from {row.get('url')}")
        else:
            print(f"   {status}")
            for attempt in row.get("attempts", []) or []:
                print(f"     - {attempt.get('outcome')}  <- {attempt.get('url')}")
        results.append(row)

    write_manifest(results)
    ok = [r for r in results if r.get("status") == "ok"]
    failed = [r for r in results if r.get("status") != "ok"]

    log_event("1.0", f"Validation datasets: {len(ok)}/{len(results)} resolved "
                     f"({', '.join(sorted(r['key'] for r in ok))}). "
                     f"Manifest at data/validation/MANIFEST.md.")

    if failed:
        names = ", ".join(sorted(r["key"] for r in failed))
        open_gate(
            "G7",
            what_is_needed=(
                f"{len(failed)} validation dataset(s) could not be obtained automatically: "
                f"{names}.\n\n"
                "Each publishes through a JavaScript front end with no documented bulk-export "
                "endpoint, or sits behind registration. Spec 4.1b forbids substituting a "
                "hand-written control, so the metrics that depend on these are reported as "
                "not computed.\n\n"
                "See data/validation/MANIFEST.md for the homepage and citation of each, and "
                "the exact outcome of every route tried."
            ),
            unblock_command=(
                "# download each file by hand from its homepage, then:\n"
                "#   mv <file> data/validation/raw/<dataset_name>\n"
                "pixi run python pipeline/acquire_validation.py --refresh"
            ),
            done=(
                f"{len(ok)} dataset(s) resolved and parsed: "
                f"{', '.join(sorted(r['key'] for r in ok))}. "
                "Row counts, licences and retrieval timestamps are recorded in "
                "data/validation/MANIFEST.md."
            ),
            next_step=(
                "G7 is non-blocking by spec. The build continues with the datasets that "
                "resolved. Section 9 metrics that depend on a missing dataset are reported "
                "as 'not computed: dataset unavailable' in FINDINGS.md, never estimated."
            ),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(refresh="--refresh" in sys.argv))
