"""Harvest an externally authored query set (spec 3.6).

The synthetic test set shares a generator with the training set, so it cannot
detect **register mismatch**: a model that only understands phrasing shaped like
its own generator's. The defence is a query set whose phrasing was written by
working scientists rather than by this project or its generator.

Method, per spec 3.6:

1. Pull the full text of recent molecular-glue and degrader discovery reviews
   from Europe PMC.
2. Extract the research questions they pose: sentences in the introduction,
   outlook and figure captions that state something a researcher wants to find
   out.
3. Keep those BINMAN's schema can actually answer.
4. Normalise lightly (strip citation markers, resolve pronouns) and record the
   source DOI and the **verbatim** original sentence for every one.
5. The gold query object is written against the schema by hand and validated by
   the parser.

This script does steps 1 to 4 and writes `candidates.jsonl` for selection. The
gold objects live in `GOLD` below, keyed by a stable hash of the normalised
question, so the mapping from a real sentence to its gold query is auditable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.queries import QueryError, parse  # noqa: E402
from pipeline.common import Fetcher, Manifest, log_event, utcnow, write_jsonl  # noqa: E402

CORPUS = ROOT / "lm" / "corpus"
CANDIDATES = CORPUS / "external_candidates.jsonl"
OUTPUT = CORPUS / "external_queries.jsonl"
STAGE = "external_queries"

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"

QUERIES = (
    'TITLE:"molecular glue" AND (PUB_TYPE:"review") AND OPEN_ACCESS:Y',
    'TITLE:"targeted protein degradation" AND (PUB_TYPE:"review") AND OPEN_ACCESS:Y',
    'TITLE:"degrader" AND (PUB_TYPE:"review") AND OPEN_ACCESS:Y',
    '(TITLE:"E3 ligase" AND TITLE:"ligand") AND OPEN_ACCESS:Y',
    'TITLE:"cereblon" AND OPEN_ACCESS:Y',
)

# A sentence that genuinely asks something, rather than one that merely contains
# the word "which" as a relative pronoun. The first revision used a loose keyword
# match and kept declarative prose such as "...expression levels vary across
# tissues, which affect the degradation activity...", which is a statement.
QUESTION_CUES = re.compile(
    r"^(which|what|how many|how much|whether|do |does |are |is |can )"
    r"|\b(remains? (?:unclear|unknown|to be determined)|it is not known|"
    r"an open question|remains? an open|we do not know|unanswered|"
    r"yet to be determined)\b",
    re.I,
)
# Figure captions, table captions and section headers are not research questions
# however they are worded.
STRUCTURAL_PREFIX = re.compile(
    r"^(figure|fig\.|table|others\s*:|box\s*\d|supplementary|scheme)", re.I)
# Vocabulary that suggests BINMAN's schema could actually answer it.
SCHEMA_CUES = re.compile(
    r"\b(ligase|ligases|E3|CRBN|cereblon|degron|glue|glues|ternary|"
    r"structure|structures|deposited|PDB|lysine|lysines|pocket|"
    r"expression|tissue|substrate|substrates|interface|buried|"
    r"chemotype|chemotypes|neosubstrate|zinc finger)\b",
    re.I,
)
CITATION = re.compile(r"\s*\[[\d,\s–-]+\]|\s*\(\d{4}\)|\s*\([A-Z][a-z]+ et al\.?[^)]*\)")
WHITESPACE = re.compile(r"\s+")


def question_id(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# gold query objects, written by hand against the schema
# --------------------------------------------------------------------------- #
#
# Each entry maps a harvested, normalised question to the query object BINMAN
# would need to answer it. The phrasing is NOT ours; the gold is. Validated by
# the parser at load time, so a gold that drifts from the schema fails loudly.

# Harvested sentences that a human confirmed ask exactly what a GOLD entry
# answers, keyed by the GOLD question. **Empty** after reading the 463 harvested
# candidates: see the note in `build()`.
ANSWERABLE: dict[str, str] = {}

GOLD: dict[str, dict] = {
    "which E3 ligases show tumour-restricted expression": {
        "record_type": "ligase",
        "filters": [{"field": "tumour_enriched", "op": "eq", "value": True}],
        "sort": {"field": "triage_rank", "direction": "asc"},
    },
    "how many deposited ternary structures involve a non-IMiD chemotype": {
        "record_type": "bridge",
        "filters": [{"field": "ccd_class", "op": "eq", "value": "glue_candidate"},
                    {"field": "symmetry_mediated", "op": "eq", "value": False}],
        "sort": {"field": "dsasa_total", "direction": "desc"},
    },
    "which E3 ligases have no ligand reported": {
        "record_type": "ligase",
        "filters": [{"field": "has_ligand", "op": "eq", "value": False}],
        "sort": {"field": "triage_rank", "direction": "asc"},
    },
    "which ligases remain structurally uncharacterised": {
        "record_type": "ligase",
        "filters": [{"field": "pdb_entries", "op": "eq", "value": 0}],
        "sort": {"field": "triage_rank", "direction": "asc"},
    },
    "how many glues bury a comparable surface against both partners": {
        "record_type": "bridge",
        "filters": [{"field": "bridging_balance", "op": "gte", "value": 0.5},
                    {"field": "ccd_class", "op": "eq", "value": "glue_candidate"}],
        "sort": {"field": "bridging_balance", "direction": "desc"},
    },
    "which ligases are druggable but have not been exploited": {
        "record_type": "ligase",
        "filters": [{"field": "exploitation_status", "op": "eq",
                     "value": "ligandable unproven"}],
        "sort": {"field": "pocket_score", "direction": "desc"},
    },
    "which degron candidates sit in high-confidence regions": {
        "record_type": "degron",
        "filters": [{"field": "mean_plddt", "op": "gte", "value": 90}],
        "sort": {"field": "degron_geometry_score", "direction": "desc"},
    },
    "how many bridging ligands are crystallisation additives rather than glues": {
        "record_type": "bridge",
        "filters": [{"field": "ccd_class", "op": "eq", "value": "cryoprotectant"}],
        "sort": {"field": "dsasa_total", "direction": "desc"},
    },
    "which ternary complexes were solved at high resolution": {
        "record_type": "bridge",
        "filters": [{"field": "resolution", "op": "lte", "value": 2.0},
                    {"field": "ccd_class", "op": "eq", "value": "glue_candidate"}],
        "sort": {"field": "resolution", "direction": "asc"},
    },
    "which ligases have the most reported substrates": {
        "record_type": "ligase",
        "filters": [{"field": "substrate_count", "op": "gte", "value": 10}],
        "sort": {"field": "substrate_count", "direction": "desc"},
    },
    "which surface lysines lie close to the binding site": {
        "record_type": "lysine",
        "filters": [{"field": "nz_centroid_distance", "op": "lte", "value": 15},
                    {"field": "nz_rel_sasa", "op": "gte", "value": 0.3}],
        "sort": {"field": "nz_centroid_distance", "direction": "asc"},
    },
    "which degrons carry an exposed glycine at the hairpin tip": {
        "record_type": "degron",
        "filters": [{"field": "tip_aa", "op": "eq", "value": "G"},
                    {"field": "tip_rel_sasa", "op": "gte", "value": 0.4}],
        "sort": {"field": "degron_geometry_score", "direction": "desc"},
    },
    "how many cullin-RING ligases are represented": {
        "record_type": "ligase",
        "filters": [{"field": "family", "op": "eq", "value": "Cullin"}],
        "sort": {"field": "triage_rank", "direction": "asc"},
    },
    "which glues were determined by cryo-electron microscopy": {
        "record_type": "bridge",
        "filters": [{"field": "method", "op": "eq", "value": "ELECTRON MICROSCOPY"},
                    {"field": "ccd_class", "op": "eq", "value": "glue_candidate"}],
        "sort": {"field": "dsasa_total", "direction": "desc"},
    },
    "which ligases are expressed in only a handful of tissues": {
        "record_type": "ligase",
        "filters": [{"field": "expression_breadth", "op": "lte", "value": 10}],
        "sort": {"field": "triage_rank", "direction": "asc"},
    },
}


def normalise(sentence: str) -> str:
    """Strip citation markers and collapse whitespace. Nothing else."""
    cleaned = CITATION.sub("", sentence)
    cleaned = WHITESPACE.sub(" ", cleaned).strip()
    cleaned = cleaned.strip(" .;:")
    return cleaned


def harvest(fetcher: Fetcher, per_query: int = 12) -> list[dict]:
    """Find candidate question sentences in open-access reviews."""
    candidates: list[dict] = []
    seen: set[str] = set()

    for query in QUERIES:
        try:
            payload = fetcher.fetch_json(
                SEARCH,
                params={"query": query, "format": "json", "pageSize": per_query,
                        "resultType": "core", "sort": "CITED desc"},
                key=f"epmc_search_{question_id(query)}",
            )
        except Exception as exc:  # noqa: BLE001
            log_event("3.6", f"Europe PMC search failed for {query[:48]}: "
                             f"{type(exc).__name__}")
            continue

        for record in (payload.get("resultList") or {}).get("result", []) or []:
            pmcid = record.get("pmcid")
            doi = record.get("doi") or ""
            title = record.get("title") or ""
            if not pmcid:
                continue
            try:
                xml = fetcher.fetch_bytes(
                    FULLTEXT.format(pmcid=pmcid), key=f"epmc_full_{pmcid}"
                ).decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue

            # Strip tags crudely: a full XML parse buys nothing here because the
            # target is sentences, not structure.
            text = re.sub(r"<[^>]+>", " ", xml)
            text = WHITESPACE.sub(" ", text)

            for raw_sentence in re.split(r"(?<=[.!?])\s+", text):
                if not (40 < len(raw_sentence) < 320):
                    continue
                normalised = normalise(raw_sentence)
                if not QUESTION_CUES.search(normalised):
                    continue
                if STRUCTURAL_PREFIX.match(normalised):
                    continue
                if not SCHEMA_CUES.search(normalised):
                    continue
                key = question_id(normalised)
                if key in seen or len(normalised) < 30:
                    continue
                seen.add(key)
                candidates.append({
                    "id": key,
                    "source_doi": doi,
                    "source_pmcid": pmcid,
                    "source_title": title,
                    "original_sentence": raw_sentence.strip(),
                    "normalised_query": normalised,
                })
    return candidates


def build(fetcher: Fetcher | None = None) -> dict:
    CORPUS.mkdir(parents=True, exist_ok=True)
    fetcher = fetcher or Fetcher("europepmc")

    candidates = harvest(fetcher)
    write_jsonl(CANDIDATES, candidates)
    log_event("3.6", f"Europe PMC harvest: {len(candidates):,} candidate question "
                     f"sentences from open-access reviews, written to "
                     f"lm/corpus/external_candidates.jsonl for selection.")

    # **Pairing is deliberate, never keyword-matched.** The first revision paired
    # a gold to whichever harvested sentence shared three or more words, which
    # produced pairs where the sentence did not ask what the gold answered, and
    # an external score that measured nothing.
    #
    # A gold is only attached to a harvested sentence when that sentence is
    # listed in ANSWERABLE below, which means a human read it and confirmed it
    # asks that question. Everything else is reported as project phrasing, which
    # tests schema coverage but NOT register mismatch.
    rows: list[dict] = []
    by_id = {c["id"]: c for c in candidates}
    interrogative = [
        c for c in candidates
        if QUESTION_CUES.search(c["normalised_query"])
        and not STRUCTURAL_PREFIX.match(c["normalised_query"])
    ]

    for question, gold in GOLD.items():
        try:
            validated = parse(gold).as_dict()
        except QueryError as exc:
            raise SystemExit(f"gold query for {question!r} is invalid: {exc}")
        source = ANSWERABLE.get(question)
        candidate = by_id.get(source) if source else None
        rows.append({
            "source_doi": candidate["source_doi"] if candidate else "",
            "source_pmcid": candidate["source_pmcid"] if candidate else "",
            "original_sentence": candidate["original_sentence"] if candidate else "",
            "normalised_query": candidate["normalised_query"] if candidate else question,
            "gold_object": validated,
            "externally_phrased": bool(candidate),
            "provenance": (
                "harvested from an open-access review and paired by hand"
                if candidate else
                "the project's own phrasing: this row tests schema coverage, "
                "NOT register mismatch, and is excluded from the external metric"
            ),
        })

    written = write_jsonl(OUTPUT, rows)
    harvested = sum(1 for r in rows if r["externally_phrased"])
    report = {
        "generated_at": utcnow(),
        "candidates_harvested": len(candidates),
        "genuinely_interrogative": len(interrogative),
        "query_set_size": written,
        "externally_phrased": harvested,
        "project_phrased": written - harvested,
        "finding": (
            f"{len(candidates)} candidate sentences were harvested from "
            f"open-access reviews, of which {len(interrogative)} are genuinely "
            "interrogative rather than declarative prose containing the word "
            "'which'. Reading those, NONE asks a question BINMAN's schema can "
            "answer: they ask about linker composition, ubiquitin chain "
            "architecture, alternative splicing of CRBN, and whether a specific "
            "metabolite mediates teratogenicity. Review articles pose mechanistic "
            "questions, not database queries.\n\n"
            "Spec 3.6 assumed 12 to 15 answerable externally-phrased questions "
            "could be harvested. They could not. The spec 9.5 external "
            "set-equality metric is therefore reported as NOT COMPUTED rather "
            "than as a number measured on mis-paired rows."
        ),
        "external_metric_computable": harvested >= 5,
    }
    (CORPUS / "external_report.json").write_text(json.dumps(report, indent=2) + "\n")
    Manifest(STAGE).record("build", status="ok", **{
        k: v for k, v in report.items() if isinstance(v, int)})
    log_event("3.6", f"External query set: {written} queries, {harvested} with real "
                     f"harvested phrasing, {written - harvested} flagged as the "
                     f"project's own phrasing.")
    return report


def main() -> int:
    argparse.ArgumentParser(description="Harvest the external query set").parse_args()
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
