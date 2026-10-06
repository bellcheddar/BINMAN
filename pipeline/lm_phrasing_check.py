"""What the project-phrased query metric is actually measuring.

`set_equality_project_phrased` reads 0.0667, one of fifteen, against a floor of
0.80. The floor is borrowed: spec 9.5 sets 0.80 for externally phrased
questions, the external harvest produced nothing usable, and D-087 attached the
floor to this proxy set so that the metric could fail at all.

It can fail. What it cannot do is pass, and that is worth stating as plainly as
D-087 stated the opposite problem.

**Seven of the fifteen gold objects carry a numeric threshold that the question
never states.** "Which ligases have the most reported substrates" is scored
against `substrate_count >= 10`. "A handful of tissues" is scored against
`expression_breadth <= 10`. "Close to the binding site" is scored against
`nz_centroid_distance <= 15` and `nz_rel_sasa >= 0.3`. No reading of the
question yields those numbers: they come from the project's own thresholds and
from whoever wrote the gold object. A model that understood every question
perfectly would still have to guess them, so exact set equality over this set
has a ceiling well below its floor.

So this reports the decomposition instead of the single number:

    record_type_accuracy   did it understand what is being asked about
    field_set_accuracy     did it choose the right columns, whatever cutoff
    set_equality           the specified metric, kept for continuity

The first two are not floors and are not proposed as replacements for the spec's
metric. They say which part of the task the head is failing, which the single
number cannot.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, log_event, utcnow  # noqa: E402

STAGE = "lm_phrasing_check"
REPORT = INTERIM / "lm_phrasing_check.json"
QUESTIONS = ROOT / "lm" / "corpus" / "external_queries.jsonl"
COMPARATIVE_OPS = ("gt", "gte", "lt", "lte")


def _numbers(text: str) -> set[str]:
    return {value.rstrip("0").rstrip(".")
            for value in re.findall(r"\d+(?:\.\d+)?", text)}


def unstated_thresholds(question: str, gold: dict) -> list[dict]:
    """Numeric filters whose threshold does not appear in the question text.

    Mechanical, not a judgement: the value is simply not in the sentence, so no
    reading of the sentence recovers it.
    """
    stated = _numbers(question)
    out = []
    for filter_ in gold.get("filters") or []:
        value = filter_.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if filter_.get("op") not in COMPARATIVE_OPS:
            continue
        if str(value).rstrip("0").rstrip(".") in stated:
            continue
        out.append({"field": filter_["field"], "op": filter_["op"], "value": value})
    return out


def _fields(query: dict) -> set:
    return {f.get("field") for f in query.get("filters") or []}


def _triples(query: dict) -> frozenset:
    return frozenset((f.get("field"), f.get("op"), str(f.get("value")))
                     for f in query.get("filters") or [])


def run() -> dict:
    from app import lm
    from app.queries import QueryError, parse, schema_summary

    if not QUESTIONS.exists():
        return {"computed": False, "reason": "lm/corpus/external_queries.jsonl is absent"}

    rows = [json.loads(line) for line in QUESTIONS.open(encoding="utf-8") if line.strip()]
    project = [row for row in rows if not row.get("externally_phrased")]
    if not project:
        return {"computed": False, "reason": "no project-phrased questions"}

    ceiling_blocked = [
        {"question": row["normalised_query"],
         "unstated": unstated_thresholds(row["normalised_query"], row["gold_object"])}
        for row in project
        if unstated_thresholds(row["normalised_query"], row["gold_object"])
    ]

    if not lm.enabled():
        # The ceiling is a property of the question set and needs no model, so
        # it is reported even when nothing can be asked.
        report = {
            "generated_at": utcnow(),
            "computed": False,
            "reason": "BINMAN_LM_URL is not set, so only the question set was analysed",
            "n_questions": len(project),
            "n_with_unstated_threshold": len(ceiling_blocked),
            "unstated_thresholds": ceiling_blocked,
        }
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
        return report

    schema = schema_summary()
    record_type_ok = field_set_ok = exact_ok = 0
    failures = []
    for row in project:
        gold, question = row["gold_object"], row["normalised_query"]
        result = lm.propose_query(question, schema)
        proposed = None
        verdict = "model error"
        if result.ok and isinstance(result.payload, dict):
            try:
                proposed = parse(result.payload).as_dict()
            except QueryError as exc:
                # The raw proposal still carries a record type and fields, and
                # those are what the first two measurements are about. A query
                # the parser rejects is a failure of the third measurement, not
                # evidence that the head misunderstood the question.
                proposed = result.payload
                verdict = f"rejected by the parser: {exc}"
        if not isinstance(proposed, dict):
            failures.append({"question": question, "verdict": verdict})
            continue

        same_type = proposed.get("record_type") == gold["record_type"]
        same_fields = same_type and _fields(proposed) == _fields(gold)
        same_set = same_fields and _triples(proposed) == _triples(gold)
        record_type_ok += int(same_type)
        field_set_ok += int(same_fields)
        exact_ok += int(same_set)
        if not same_set:
            failures.append({
                "question": question,
                "verdict": verdict if verdict != "model error" else (
                    "wrong record type" if not same_type else
                    "right record type, wrong fields" if not same_fields else
                    "right fields, different cutoff"),
                "gold_filters": gold.get("filters") or [],
                "proposed_filters": proposed.get("filters") or [],
            })

    n = len(project)
    report = {
        "generated_at": utcnow(),
        "computed": True,
        "n_questions": n,
        "record_type_accuracy": round(record_type_ok / n, 4),
        "field_set_accuracy": round(field_set_ok / n, 4),
        "set_equality": round(exact_ok / n, 4),
        "n_with_unstated_threshold": len(ceiling_blocked),
        # The best score exact set equality could reach if every other question
        # were answered perfectly and no unstated threshold were ever guessed.
        "set_equality_ceiling": round((n - len(ceiling_blocked)) / n, 4),
        "unstated_thresholds": ceiling_blocked,
        "failures": failures,
        "source": ("lm/corpus/external_queries.jsonl, the rows the harvest "
                   "marks as the project's own phrasing"),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    log_event("3.8", f"Project-phrased queries: record type "
                     f"{report['record_type_accuracy']}, fields "
                     f"{report['field_set_accuracy']}, set equality "
                     f"{report['set_equality']} against a ceiling of "
                     f"{report['set_equality_ceiling']}.")
    return report


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
