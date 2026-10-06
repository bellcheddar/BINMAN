"""Does the abstain head know when a question CAN be answered?

Spec 9.5 measures Task C on unanswerable questions alone: abstention rate and
fabrication rate, over 40 questions the atlas cannot answer. A head that refuses
every question scores 1.0 and 0.0 on those, perfectly, while being useless. The
metric has no way to fail, which is the same hole the DPO rounds fell through
until a generation guard was added (FINDINGS, Training).

D-086 found that it does refuse everything. This measures it rather than
asserting it: the same head, asked questions the atlas demonstrably can answer,
and the rate at which it correctly declines to abstain.

The answerable set is BINMAN's own shipped presets. Each was verified end to
end against the live model and the atlas: it parses, it returns the record type
of the page it sits on, and it returns rows. If the abstain head calls those
unanswerable, it is wrong, and the atlas rather than an opinion says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, log_event, utcnow  # noqa: E402

STAGE = "lm_abstention_check"
REPORT = INTERIM / "lm_abstention_check.json"


def answerable_questions() -> list[str]:
    from app import NL_EXAMPLES

    return [q for questions in NL_EXAMPLES.values() for q in questions]


def unanswerable_questions(limit: int = 20) -> list[str]:
    path = ROOT / "lm" / "corpus" / "task_c_test.jsonl"
    out: list[str] = []
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                messages = json.loads(line).get("messages", [])
            except json.JSONDecodeError:
                continue
            user = next((m["content"] for m in messages if m.get("role") == "user"), None)
            if user:
                out.append(user)
            if len(out) >= limit:
                break
    return out


def run(limit: int = 20) -> dict:
    from app import lm

    if not lm.enabled():
        return {"computed": False, "reason": "BINMAN_LM_URL is not set"}

    answerable = answerable_questions()
    unanswerable = unanswerable_questions(limit)
    log_event("3.8", f"Abstention check: {len(answerable)} answerable and "
                     f"{len(unanswerable)} unanswerable questions.")

    def abstains(question: str) -> bool:
        result = lm.explain_refusal(question)
        if not result.ok or not isinstance(result.payload, dict):
            return False
        return result.payload.get("answerable") is False

    false_abstentions = [q for q in answerable if abstains(q)]
    true_abstentions = [q for q in unanswerable if abstains(q)]

    n_ans, n_un = len(answerable), len(unanswerable)
    report = {
        "generated_at": utcnow(),
        "n_answerable": n_ans,
        "n_unanswerable": n_un,
        # Recall: of the questions that truly cannot be answered, how many does
        # it catch. This is what spec 9.5 already measures.
        "abstention_recall": round(len(true_abstentions) / n_un, 4) if n_un else None,
        # Specificity: of the questions that CAN be answered, how many does it
        # correctly let through. This is the number spec 9.5 cannot see, and
        # the one that separates a useful head from one that refuses everything.
        "abstention_specificity": round(
            (n_ans - len(false_abstentions)) / n_ans, 4) if n_ans else None,
        "false_abstentions": false_abstentions,
        "answerable_source": "app.NL_EXAMPLES, each verified against the atlas",
        "unanswerable_source": "lm/corpus/task_c_test.jsonl",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    log_event("3.8", f"Abstention recall {report['abstention_recall']}, "
                     f"specificity {report['abstention_specificity']}.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
