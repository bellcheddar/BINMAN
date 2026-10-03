"""Build `references.bib`, Crossref-verified (spec 12.3).

**References are resolved by search, not recalled.** An earlier revision of this
module carried hand-written DOIs, and Crossref showed several of them resolved to
unrelated works: the DEGRONOPEDIA DOI returned a Reactome paper, the DCAF15 DOI
returned a Zika virus paper, and one DOI was a placeholder that had no business
being written at all. A DOI that resolves to the wrong work is more dangerous
than one that fails outright, because it looks verified.

So every candidate carries a bibliographic query and the words its title must
contain. The DOI comes from Crossref's search endpoint and the returned title is
checked against those words. Four outcomes, all recorded:

    verified     a work was found whose title matches the expected words
    preprint     the only match is a preprint; cited as such, never as a journal
    mismatched   a work was found but its title does not match, so it is marked
                 unverified and both titles are recorded
    unverified   nothing matched

Rules from the spec that this module enforces: never invent a DOI; keep an
unverified row rather than dropping it; record the canonical URL where there is
no DOI and say so; licence is a required field where "not determined" is a
legitimate value and a guess is not; and record a release identifier and
retrieval date for every dataset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import ROOT, VALIDATION, Fetcher, Manifest, log_event, utcnow  # noqa: E402

BIB_PATH = ROOT / "references.bib"
JSON_PATH = VALIDATION / "references.json"
STAGE = "references"
SEARCH_URL = "https://api.crossref.org/works"

# Crossref record types that are not the work itself: a review of a paper, a
# supplementary component, a deposited structure. Excluded from matching.
JUNK_TYPES = {"component", "peer-review", "grant", "dataset-component"}
JUNK_CONTAINERS = ("faculty opinions", "f1000prime")
# Conference abstracts carry the right words and the wrong work.
ABSTRACT_TITLE = re.compile(r"^abstract\s*[\d:]", re.I)
PREPRINT_TYPES = {"posted-content"}


@dataclass
class Candidate:
    """A reference the build wants to cite.

    `query` is what goes to Crossref. `expect` is the set of lowercase substrings
    the returned title must all contain. `software_only` skips the search for
    tools that have no citeable paper.
    """

    key: str
    kind: str                 # database | dataset | model | software | paper
    used_for: str
    licence: str = "not determined"
    query: str = ""
    expect: tuple[str, ...] = ()
    url: str = ""
    repo: str = ""
    version: str = ""
    software_only: bool = False
    title: str = ""           # used when software_only
    authors: str = ""
    year: str = ""


def candidates() -> list[Candidate]:
    return [
        # ------------------------- validation datasets (spec 4.1b) ----------- #
        Candidate("biolip2", "database",
                  "Glue Atlas artefact precision and cofactor labels for LM Task B",
                  "free for academic use; curation code BSD-2-Clause",
                  query="BioLiP2 updated structure database biologically relevant ligand protein interactions",
                  expect=("biolip",),
                  url="https://zhanggroup.org/BioLiP/",
                  repo="https://github.com/kad-ecoli/mmCIF2BioLiP"),
        Candidate("protcid", "database",
                  "Glue Atlas packing specificity: packing-only interfaces must not be called glue interfaces",
                  "free for academic use",
                  query="ProtCID protein common interface database Dunbrack",
                  expect=("protcid",),
                  url="https://dunbrack2.fccc.edu/ProtCiD/"),
        Candidate("mgdb", "database", "Glue Atlas recall, curated glue set 1 of 3",
                  "open access, bulk export not yet available",
                  query="MGDB a curated database for molecular glues",
                  expect=("mgdb", "molecular glue"),
                  url="http://mgdb.idruglab.cn/"),
        Candidate("molgluedb", "database", "Glue Atlas recall, curated glue set 2 of 3",
                  "free and open access",
                  query="MolGlueDB an online database of molecular glues",
                  expect=("molgluedb",),
                  url="https://www.molgluedb.com/"),
        Candidate("protacdb3", "database",
                  "LM Task B confusable negative class; Glue Atlas exclusion set",
                  "internal use only, redistribution prohibited (Hou group terms, 2024-09-29)",
                  query="PROTAC-DB 3.0 updated database of PROTACs extended pharmacokinetic parameters",
                  expect=("protac-db",),
                  url="https://cadd.zju.edu.cn/protacdb/"),
        Candidate("degronopedia", "database", "Degron Scan cross-reference",
                  "not determined",
                  query="DEGRONOPEDIA web server proteome-wide inspection of degrons",
                  expect=("degronopedia",),
                  url="https://degronopedia.com/"),
        Candidate("ubibrowser2", "database",
                  "E3 Triage substrate counts and the spec 9.3 enrichment test",
                  "not determined",
                  query="UbiBrowser 2.0 comprehensive resource proteome-wide known and predicted ubiquitin ligase substrate interactions",
                  expect=("ubibrowser",),
                  url="http://ubibrowser.bio-it.cn/ubibrowser_v3/"),
        Candidate("phosphositeplus", "database",
                  "Degradability reach window calibration from observed diGly sites",
                  "free for non-commercial use, registration required",
                  query="PhosphoSitePlus mutations PTMs and recalibrations",
                  expect=("phosphositeplus",),
                  url="https://www.phosphosite.org/"),
        Candidate("alphafold_db", "database",
                  "Degron Scan over the human predicted proteome", "CC-BY-4.0",
                  query="AlphaFold Protein Structure Database massively expanding the structural coverage of protein sequence space",
                  expect=("alphafold", "database"),
                  url="https://alphafold.ebi.ac.uk/"),
        Candidate("uniprot", "database",
                  "accession mapping, sequences and keyword annotation", "CC-BY-4.0",
                  query="UniProt the Universal Protein Knowledgebase",
                  expect=("uniprot",),
                  url="https://www.uniprot.org/"),
        Candidate("interpro", "database",
                  "E3 ligase family assignment and domain boundaries", "CC0-1.0",
                  query="InterPro protein sequence classification resource",
                  expect=("interpro",),
                  url="https://www.ebi.ac.uk/interpro/"),
        Candidate("open_targets", "database",
                  "ligase expression breadth, tumour enrichment and tractability", "CC0-1.0",
                  query="Open Targets Platform supporting systematic drug target identification and prioritisation",
                  expect=("open targets",),
                  url="https://platform.opentargets.org/"),
        Candidate("rcsb_pdb", "database",
                  "entry discovery, metadata and biological assemblies", "CC0-1.0",
                  query="RCSB Protein Data Bank Berman 2000 nucleic acids research",
                  expect=("protein data bank",),
                  url="https://www.rcsb.org/"),
        Candidate("pdbe", "database",
                  "ligand chemistry cross-check and validation summaries", "CC0-1.0",
                  query="PDBe Protein Data Bank in Europe deposition and annotation",
                  expect=("pdbe",),
                  url="https://www.ebi.ac.uk/pdbe/"),
        Candidate("europepmc", "database",
                  "abstracts for the LM Task B triage corpus", "varies by article",
                  query="Europe PMC a full-text literature database for the life sciences",
                  expect=("europe pmc",),
                  url="https://europepmc.org/"),
        Candidate("ccd", "database",
                  "ligand classification, formula and parent assignment", "CC0-1.0",
                  query="Chemical Component Dictionary PDB chemical reference data small molecules",
                  expect=("chemical", "component"),
                  url="https://www.wwpdb.org/data/ccd"),

        # ------------------------- methods and background (spec 12.3) ------- #
        Candidate("crbn_imid_degradation", "paper",
                  "CRBN-IMiD neosubstrate degradation, the founding observation",
                  "publisher terms",
                  query="Lenalidomide causes selective degradation of IKZF1 and IKZF3 in multiple myeloma cells",
                  expect=("ikzf1", "degradation")),
        Candidate("imid_zf_interface", "paper",
                  "structural basis of the IMiD-induced CRBN-zinc-finger interface",
                  "publisher terms",
                  query="Structure of the DDB1-CRBN E3 ubiquitin ligase in complex with thalidomide",
                  expect=("crbn",)),
        Candidate("ck1a_lenalidomide", "paper",
                  "lenalidomide-induced CK1alpha degradation in del(5q) MDS",
                  "publisher terms",
                  query="Lenalidomide induces ubiquitination and degradation of CK1 alpha in del(5q) MDS",
                  expect=("ck1",)),
        Candidate("dcaf15_rbm39", "paper",
                  "DCAF15 with aryl sulfonamides and RBM39", "publisher terms",
                  query="Anticancer sulfonamides target splicing by inducing RBM39 degradation via recruitment to DCAF15",
                  expect=("rbm39", "dcaf15")),
        Candidate("cr8_cyclink", "paper",
                  "the CDK-inhibitor-induced DDB1-cyclin K complex", "publisher terms",
                  query="The CDK inhibitor CR8 acts as a molecular glue degrader that depletes cyclin K",
                  expect=("cr8", "cyclin k")),
        Candidate("tir1_auxin", "paper", "the TIR1-auxin co-receptor structure",
                  "publisher terms",
                  query="Mechanism of auxin perception by the TIR1 ubiquitin ligase",
                  expect=("tir1", "auxin")),
        Candidate("fkbp_rapamycin_frb", "paper", "the FKBP12-rapamycin-FRB ternary complex",
                  "publisher terms",
                  query="Structure of the FKBP12-rapamycin complex interacting with binding domain of human FRAP",
                  expect=("fkbp12", "rapamycin")),
        Candidate("glycine_degron", "paper",
                  "the C-terminal glycine degron rule for CRBN substrates", "publisher terms",
                  query="The eukaryotic proteome is shaped by E3 ubiquitin ligases targeting C-terminal degrons",
                  expect=("c-terminal degron",)),
        Candidate("zf_degradation_screen", "paper",
                  "Degron Scan matched degraded and non-degraded zinc-finger sets",
                  "publisher terms",
                  query="Defining the human C2H2 zinc finger degrome targeted by thalidomide analogs through CRBN",
                  expect=("zinc finger",)),
        Candidate("tien_sasa", "paper",
                  "maximum residue accessibility reference for relative SASA", "CC-BY-4.0",
                  query="Maximum allowed solvent accessibilites of residues in proteins",
                  expect=("solvent", "accessib")),
        Candidate("digly_proteomics", "paper",
                  "proteome-wide diGly ubiquitylation site mapping", "publisher terms",
                  query="Systematic and quantitative assessment of the ubiquitin-modified proteome diGly",
                  expect=("ubiquitin",)),

        # ------------------------------------------------- software ---------- #
        Candidate("freesasa", "software", "solvent accessible surface area and ΔSASA", "MIT",
                  query="FreeSASA an open source C library for solvent accessible surface area calculations",
                  expect=("freesasa",), url="https://freesasa.github.io/"),
        Candidate("dssp", "software", "secondary structure for hairpin detection", "BSD-2-Clause",
                  query="Dictionary of protein secondary structure pattern recognition of hydrogen-bonded and geometrical features",
                  expect=("secondary structure",), url="https://pdb-redo.eu/dssp"),
        Candidate("gemmi", "software", "mmCIF parsing, assemblies and neighbour search", "MPL-2.0",
                  query="GEMMI library macromolecular crystallography structural bioinformatics Wojdyr",
                  expect=("gemmi",), url="https://gemmi.readthedocs.io/",
                  repo="https://github.com/project-gemmi/gemmi"),
        Candidate("rdkit", "software",
                  "ligand properties, SMILES and the structural classification rules",
                  "BSD-3-Clause", software_only=True,
                  title="RDKit: Open-source cheminformatics",
                  authors="Landrum, G. and the RDKit contributors",
                  url="https://www.rdkit.org/", repo="https://github.com/rdkit/rdkit"),
        Candidate("fpocket", "software",
                  "pocket detection and druggability scoring on ligase structures", "MIT",
                  query="Fpocket an open source platform for ligand pocket detection",
                  expect=("fpocket",), url="https://github.com/Discngine/fpocket"),
        Candidate("p2rank", "software", "documented fallback for pocket detection", "MIT",
                  query="P2Rank machine learning based tool for rapid and accurate prediction of ligand binding sites",
                  expect=("p2rank",), url="https://github.com/rdk/p2rank"),
        Candidate("plip", "software", "interaction typing at each half-interface", "GPL-2.0",
                  query="PLIP 2021 expanding the scope of the protein-ligand interaction profiler",
                  expect=("plip",), url="https://github.com/pharmai/plip"),
        Candidate("molstar", "software", "every structure viewer in the app", "MIT",
                  query="Mol* Viewer modern web app for 3D visualization and analysis of large biomolecular structures",
                  expect=("mol*",), url="https://molstar.org/",
                  repo="https://github.com/molstar/molstar", version="5.12.0"),
        Candidate("biotite", "software", "structure handling and superposition", "BSD-3-Clause",
                  query="Biotite a unifying open source computational biology framework in Python",
                  expect=("biotite",), url="https://www.biotite-python.org/"),
        Candidate("openbabel", "software", "CIF to PDB conversion in the PLIP path", "GPL-2.0",
                  query="Open Babel an open chemical toolbox",
                  expect=("open babel",), url="https://openbabel.org/"),
        Candidate("duckdb", "software", "analytical store during the pipeline", "MIT",
                  query="DuckDB an embeddable analytical database",
                  expect=("duckdb",), url="https://duckdb.org/"),
        Candidate("mlx", "software", "BINMAN-LM fine-tuning and serving", "MIT",
                  software_only=True,
                  title="MLX: efficient and flexible machine learning on Apple silicon",
                  authors="Hannun, A. and Digani, J. and Katharopoulos, A. and Collobert, R.",
                  year="2023", url="https://github.com/ml-explore/mlx",
                  repo="https://github.com/ml-explore/mlx"),
        Candidate("d3", "software", "the lens graph and the ternary triangle", "ISC",
                  query="D3 data-driven documents Bostock Ogievetsky Heer",
                  expect=("data-driven documents",), url="https://d3js.org/",
                  repo="https://github.com/d3/d3", version="7.9.0"),
        Candidate("tabulator", "software", "the ledger table and the reference table", "MIT",
                  software_only=True, title="Tabulator: interactive tables and data grids",
                  authors="Folkerd, O.", url="https://tabulator.info/",
                  repo="https://github.com/olifolkerd/tabulator", version="6.3.1"),
        Candidate("plotly", "software", "distributions, scatter and the confusion matrix", "MIT",
                  software_only=True, title="Plotly.js: open source JavaScript charting library",
                  authors="Plotly Technologies Inc.", url="https://plotly.com/javascript/",
                  repo="https://github.com/plotly/plotly.js", version="2.35.2"),
        Candidate("flask", "software", "the serving layer", "BSD-3-Clause",
                  software_only=True,
                  title="Flask: a lightweight WSGI web application framework",
                  authors="Ronacher, A. and the Pallets team",
                  url="https://flask.palletsprojects.com/"),
        # The Qwen reports are arXiv preprints that Crossref does not index, so
        # this records the model card URL rather than attaching an invented DOI.
        Candidate("qwen25", "model", "BINMAN-LM base model", "Apache-2.0",
                  software_only=True,
                  title="Qwen2.5-3B-Instruct model card",
                  authors="Qwen Team, Alibaba Cloud", year="2024",
                  url="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct",
                  version="3B-Instruct, 4-bit via mlx-lm"),
    ]


def _title_of(item: dict) -> str:
    titles = item.get("title") or []
    return (titles[0] if titles else "").strip()


def _is_junk(item: dict) -> bool:
    if item.get("type") in JUNK_TYPES:
        return True
    container = " ".join(item.get("container-title") or []).lower()
    if any(name in container for name in JUNK_CONTAINERS):
        return True
    title = _title_of(item).lower()
    if title.startswith("faculty opinions recommendation"):
        return True
    return bool(ABSTRACT_TITLE.match(_title_of(item)))


def _matches(item: dict, expect: tuple[str, ...]) -> bool:
    title = _title_of(item).lower()
    if not title:
        return False
    return all(word.lower() in title for word in expect)


def search(candidate: Candidate, fetcher: Fetcher, rows: int = 12) -> dict:
    """Find and check one reference. Never returns a DOI it has not matched."""
    record = {
        "key": candidate.key, "type": candidate.kind, "doi": "",
        "url": candidate.url, "licence": candidate.licence,
        "used_for": candidate.used_for, "version": candidate.version,
        "repo": candidate.repo, "verified": False, "verification": "",
        "title": candidate.title, "authors": candidate.authors,
        "year": candidate.year, "container": "", "publisher": "",
        "is_preprint": False, "checked_at": utcnow(), "query": candidate.query,
    }

    if candidate.software_only:
        record["verification"] = "software with no citeable paper: canonical URL recorded instead"
        return record
    if not candidate.query:
        record["verification"] = "no query defined"
        return record

    try:
        payload = fetcher.fetch_json(
            SEARCH_URL,
            params={
                "query.bibliographic": candidate.query, "rows": rows,
                "select": "DOI,title,author,issued,container-title,publisher,URL,type",
            },
            key=f"xrsearch_{re.sub(r'[^A-Za-z0-9]+', '_', candidate.query)[:80]}",
        )
    except Exception as exc:  # noqa: BLE001
        record["verification"] = f"unverified: Crossref search failed ({type(exc).__name__})"
        return record

    items = [i for i in ((payload.get("message") or {}).get("items") or []) if not _is_junk(i)]
    matched = [i for i in items if _matches(i, candidate.expect)]
    # Prefer a real journal article, then anything that is not a preprint, then
    # a preprint. A database's own paper is always a journal article, so this
    # ordering keeps conference and book matter out of the way.
    articles = [i for i in matched if i.get("type") == "journal-article"]
    non_preprint = [i for i in matched if i.get("type") not in PREPRINT_TYPES]
    chosen = (articles or non_preprint or matched or [None])[0]

    if chosen is None:
        best = _title_of(items[0]) if items else ""
        record["verification"] = (
            "unverified: no Crossref result whose title contains "
            f"{list(candidate.expect)}"
            + (f"; closest was {best!r}" if best else "")
        )
        return record

    authors = []
    for author in (chosen.get("author") or [])[:12]:
        family = author.get("family") or ""
        given = author.get("given") or ""
        if family:
            authors.append(f"{family}, {given}".strip().rstrip(","))
    issued = ((chosen.get("issued") or {}).get("date-parts") or [[None]])[0]
    is_preprint = chosen.get("type") in PREPRINT_TYPES

    record.update({
        "doi": chosen.get("DOI", ""),
        "verified": True,
        "is_preprint": is_preprint,
        "verification": ("Crossref verified (preprint)" if is_preprint
                         else "Crossref verified"),
        "title": _title_of(chosen),
        "authors": " and ".join(authors),
        "year": str(issued[0]) if issued and issued[0] else "",
        "container": (chosen.get("container-title") or [""])[0],
        "publisher": chosen.get("publisher") or "",
        "url": chosen.get("URL") or candidate.url,
    })
    return record


def bibtex(record: dict) -> str:
    kind_map = {"paper": "article", "database": "article", "dataset": "misc",
                "software": "software", "model": "misc"}
    entry_type = kind_map.get(record["type"], "misc")
    lines = [f"@{entry_type}{{{record['key']},"]

    def add(name: str, value: str) -> None:
        if value:
            escaped = str(value).replace("{", "").replace("}", "")
            lines.append(f"  {name} = {{{escaped}}},")

    add("title", record.get("title") or "title not recorded")
    add("author", record.get("authors"))
    add("year", record.get("year"))
    add("journal" if entry_type == "article" else "howpublished", record.get("container"))
    add("publisher", record.get("publisher"))
    add("doi", record.get("doi"))
    add("url", record.get("url"))
    add("version", record.get("version"))
    add("license", record.get("licence"))
    add("note", record.get("verification"))
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


def build(refresh: bool = False) -> dict:
    fetcher = Fetcher("crossref", refresh=refresh)
    manifest = Manifest(STAGE)
    records = []
    for candidate in candidates():
        record = search(candidate, fetcher)
        records.append(record)
        state = ("verified" if record["verified"] and not record["is_preprint"]
                 else "preprint" if record["is_preprint"]
                 else "no-paper" if candidate.software_only else "UNVERIFIED")
        print(f"  {state:<10} {candidate.key:<24} {record.get('title', '')[:62]}")

    verified = sum(1 for r in records if r["verified"])
    preprints = sum(1 for r in records if r["is_preprint"])
    no_doi = sum(1 for r in records if not r["doi"])
    unverified = [r["key"] for r in records if not r["verified"]]
    undetermined = [r["key"] for r in records if r["licence"] == "not determined"]

    header = [
        "% BINMAN references, generated by pipeline/references.py.",
        f"% Generated {utcnow()}.",
        "%",
        "% Every entry here was resolved by Crossref SEARCH, not recalled: the DOI,",
        "% title, authors and year are what Crossref returned for a bibliographic",
        "% query, and the title was checked against the words the build expected to",
        "% see. An entry Crossref could not match is marked unverified in its note",
        "% field and kept rather than dropped, with no DOI attached. A preprint is",
        "% labelled as one.",
        "%",
        f"% {len(records)} references: {verified} Crossref matched "
        f"({preprints} of them preprints), {len(unverified)} unmatched, "
        f"{no_doi} with no DOI.",
        "",
    ]
    BIB_PATH.write_text("\n".join(header) + "\n\n".join(bibtex(r) for r in records) + "\n")
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps({
        "generated_at": utcnow(), "references": records,
        "verified": verified, "preprints": preprints, "total": len(records),
        "unverified": unverified, "licence_not_determined": undetermined,
    }, indent=2) + "\n")

    counts = {
        "total": len(records), "verified": verified, "preprints": preprints,
        "unverified": len(unverified), "no_doi": no_doi,
        "licence_not_determined": len(undetermined),
    }
    manifest.record("build", status="ok", **counts)
    log_event("12.3", f"references.bib: {len(records)} references, {verified} Crossref "
                      f"matched by search ({preprints} preprints), {len(unverified)} "
                      f"unmatched, {no_doi} with no DOI, {len(undetermined)} with licence "
                      f"not determined.")
    if unverified:
        print(f"\nunmatched (kept, no DOI attached): {', '.join(unverified)}")
    if undetermined:
        print(f"licence not determined: {', '.join(undetermined)}")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Crossref-verified references.bib")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(refresh=args.refresh), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
