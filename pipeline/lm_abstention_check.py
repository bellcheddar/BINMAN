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

from pipeline.common import INTERIM, Manifest, log_event, utcnow  # noqa: E402

STAGE = "lm_abstention_check"
REPORT = INTERIM / "lm_abstention_check.json"
BASE_MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"


def answerable_questions() -> list[str]:
    from app import NL_EXAMPLES

    return [q for questions in NL_EXAMPLES.values() for q in questions]


def unanswerable_questions(limit: int = 20) -> list[str]:
    """The refusal half of the Task C test split.

    `kind` has to be read, not assumed. Task C used to be refusals only, so
    every row of this file was unanswerable and taking them in order was safe.
    It now carries an answerable class as well, and reading the file blind
    would feed answerable questions in as unanswerable ones and quietly deflate
    the recall it is supposed to measure.
    """
    path = ROOT / "lm" / "corpus" / "task_c_test.jsonl"
    out: list[str] = []
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") == "answerable":
                continue
            messages = row.get("messages", [])
            user = next((m["content"] for m in messages if m.get("role") == "user"), None)
            if user:
                out.append(user)
            if len(out) >= limit:
                break
    return out


def _local_asker(adapter: str, model_name: str):
    """Ask a freshly trained adapter on this machine, not the served one.

    A training round has to be measurable before it is deployed. Without this
    the only way to get the number was to convert the adapter, push it to the
    Hub, restart the Space and then ask, which is three irreversible steps
    taken on the strength of a number nobody had yet.
    """
    from lm.evaluate import generate_one
    from app.lm import ABSTAIN_SYSTEM
    from mlx_lm import load

    model, tokenizer = load(model_name, adapter_path=adapter)

    def ask(question: str) -> dict | None:
        text = generate_one(model, tokenizer, question, "", max_tokens=220,
                            system_override=ABSTAIN_SYSTEM)
        candidate = text.strip()
        if "```" in candidate:
            for part in candidate.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    candidate = part
                    break
        start = candidate.find("{")
        if start > 0:
            candidate = candidate[start:]
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    return ask


def run(limit: int = 20, adapter: str | None = None,
        model_name: str | None = None) -> dict:
    from app import lm

    if adapter:
        ask = _local_asker(adapter, model_name or BASE_MODEL)
        served = f"local adapter {adapter} over {model_name or BASE_MODEL}"
    elif lm.enabled():
        def ask(question: str) -> dict | None:
            result = lm.explain_refusal(question)
            return result.payload if result.ok and isinstance(result.payload, dict) else None
        served = "the served endpoint (BINMAN_LM_URL)"
    else:
        return {"computed": False,
                "reason": "BINMAN_LM_URL is not set and no --adapter was given"}

    answerable = answerable_questions()
    unanswerable = unanswerable_questions(limit)
    log_event("3.8", f"Abstention check: {len(answerable)} answerable and "
                     f"{len(unanswerable)} unanswerable questions, asked of "
                     f"{served}.")

    def abstains(question: str) -> bool:
        payload = ask(question)
        if payload is None:
            # Unparseable is not an abstention. It is a different failure and
            # counting it as one would credit the head for being broken.
            return False
        return payload.get("answerable") is False

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
        "unanswerable_source": "lm/corpus/task_c_test.jsonl, kind != answerable",
        "asked_of": served,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    Manifest(STAGE).record(
        "check", status="ok", recall=report["abstention_recall"],
        specificity=report["abstention_specificity"],
        n_answerable=n_ans, n_unanswerable=n_un, asked_of=served)
    log_event("3.8", f"Abstention recall {report['abstention_recall']}, "
                     f"specificity {report['abstention_specificity']}.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--adapter", default=None,
                        help="measure a local MLX adapter instead of the served model")
    parser.add_argument("--model", default=None,
                        help=f"base model for --adapter (default {BASE_MODEL})")
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit, adapter=args.adapter,
                         model_name=args.model), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
