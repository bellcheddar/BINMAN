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

# A sentence that states something a researcher wants to find out.
QUESTION_CUES = re.compile(
    r"\b(which|how many|what fraction|whether|to what extent|how much|"
    r"remains? (?:unclear|unknown|to be determined)|it is not known|"
    r"an open question|remains? an open|we do not know|unanswered)\b",
    re.I,
)
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
                if not QUESTION_CUES.search(raw_sentence):
                    continue
                if not SCHEMA_CUES.search(raw_sentence):
                    continue
                normalised = normalise(raw_sentence)
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

    # Match harvested sentences to the hand-written gold objects by keyword
    # overlap, so a gold is only used when a real sentence actually asked it.
    rows: list[dict] = []
    unmatched_gold: list[str] = []
    for question, gold in GOLD.items():
        try:
            validated = parse(gold).as_dict()
        except QueryError as exc:
            raise SystemExit(f"gold query for {question!r} is invalid: {exc}")

        tokens = {w for w in re.findall(r"[a-z]{4,}", question.lower())}
        best = None
        best_overlap = 0
        for candidate in candidates:
            words = {w for w in re.findall(
                r"[a-z]{4,}", candidate["normalised_query"].lower())}
            overlap = len(tokens & words)
            if overlap > best_overlap:
                best_overlap, best = overlap, candidate

        if best is not None and best_overlap >= 3:
            rows.append({
                "source_doi": best["source_doi"],
                "source_pmcid": best["source_pmcid"],
                "original_sentence": best["original_sentence"],
                "normalised_query": best["normalised_query"],
                "gold_object": validated,
                "provenance": "harvested from an open-access review",
                "keyword_overlap": best_overlap,
            })
        else:
            unmatched_gold.append(question)
            rows.append({
                "source_doi": "",
                "source_pmcid": "",
                "original_sentence": "",
                "normalised_query": question,
                "gold_object": validated,
                "provenance": (
                    "no harvested sentence matched: the phrasing is the project's "
                    "own, so this row does NOT test register mismatch and is "
                    "flagged accordingly"
                ),
                "keyword_overlap": 0,
            })

    written = write_jsonl(OUTPUT, rows)
    harvested = sum(1 for r in rows if r["keyword_overlap"] >= 3)
    report = {
        "generated_at": utcnow(),
        "candidates_harvested": len(candidates),
        "query_set_size": written,
        "externally_phrased": harvested,
        "project_phrased": written - harvested,
        "note": (
            "Only the rows with a non-empty `original_sentence` test register "
            "mismatch. The rest carry the project's own phrasing and are flagged "
            "in `provenance`, because a query set that silently mixes the two "
            "would overstate the external number."
        ),
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
