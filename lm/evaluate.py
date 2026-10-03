"""Evaluate BINMAN-LM, and run the mandatory Phase 3.0 baseline (spec 3.0, 3.8).

Three numbers, per spec 3.8:

* **Parse rate.** Fraction of outputs that parse. If this is not ~1.0 after
  stage 1, the corpus is wrong and stage 2 must not be started.
* **Set equality.** Execute both the gold query and the predicted query against
  the real SQLite and compare the **returned row sets**. Two syntactically
  different queries that select the same rows are both correct. This is the
  primary metric for Task A.
* **Per-mode win rate.** For each corruption mode, how often the model prefers
  the correct form. A failing mode names the behaviour that did not take.

Spec 3.0 is mandatory: the base model is measured zero-shot *before* any
training, and if it already reaches the configured set-equality threshold then
Task A is not fine-tuned at all.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.queries import (  # noqa: E402
    OPERATORS, RECORD_TYPES, QueryError, parse, row_identity_set,
)
from pipeline.common import INTERIM, Manifest, load_config, log_event, utcnow  # noqa: E402

CORPUS = ROOT / "lm" / "corpus"
DB_PATH = ROOT / "data" / "atlas" / "binman.sqlite"
REPORT = INTERIM / "lm_eval.json"
STAGE = "lm_eval"

BASE_MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"


def compact_schema() -> dict:
    """The schema, trimmed to what a prompt needs.

    The full `schema_summary` carries descriptions that would dominate the
    context window. This keeps the field names, kinds, units and closed
    vocabularies, which is everything needed to write a valid query.
    """
    out: dict = {"operators": list(OPERATORS), "record_types": {}}
    for name, spec in RECORD_TYPES.items():
        fields = {}
        for field_name, field_spec in spec.fields.items():
            entry: dict = {"kind": field_spec.kind}
            if field_spec.unit:
                entry["unit"] = field_spec.unit
            if field_spec.enum:
                entry["values"] = list(field_spec.enum)
            fields[field_name] = entry
        out["record_types"][name] = {"fields": fields}
    return out


SYSTEM = (
    "<task>query</task>\n"
    "You translate a natural language question into a BINMAN query object. "
    "Reply with JSON only, no prose and no code fence. Use only the fields, "
    "operators and values in the schema. Never invent a field, a ligase or a PDB "
    "identifier. Never compute or estimate a numeric value.\n\n"
    "The object has the shape:\n"
    '{"record_type": "<one of the record types>", '
    '"filters": [{"field": "<field>", "op": "<operator>", "value": <value>}], '
    '"sort": {"field": "<field>", "direction": "asc|desc"}, "limit": <integer>}\n\n'
    "Schema:\n"
)

JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def extract_json(text: str) -> str:
    """Pull the first JSON object out of a response, tolerating a code fence."""
    cleaned = text.strip()
    if "```" in cleaned:
        for part in cleaned.split("```"):
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                return stripped
    match = JSON_BLOCK.search(cleaned)
    return match.group(0) if match else cleaned


# --------------------------------------------------------------------------- #
# generation
# --------------------------------------------------------------------------- #

def load_model(model_path: str, adapter_path: str | None = None):
    from mlx_lm import load

    if adapter_path:
        return load(model_path, adapter_path=adapter_path)
    return load(model_path)


# The fine-tuned model has internalised the schema, so it is prompted exactly as
# it was trained: a short system turn with no schema. Handing it the 6 KB schema
# it never saw during training measurably degrades it (it starts omitting
# `record_type`, which the parser then rejects). The baseline needs the schema
# because it has no other way to know the fields exist.
TRAINED_SYSTEM = (
    "<task>query</task>\n"
    "You translate a natural language question into a BINMAN query object. "
    "Reply with JSON only. Use only the fields, operators and values in the "
    "schema. Never invent a field, a ligase or a PDB identifier. Never compute "
    "or estimate a numeric value."
)


def generate_one(model, tokenizer, question: str, schema_text: str,
                 max_tokens: int = 320) -> str:
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler

    # An empty schema_text means "use the prompt the model was trained with".
    system = (SYSTEM + schema_text) if schema_text else TRAINED_SYSTEM
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False
    )
    # Greedy: this is a structured-output task, so sampling only adds variance.
    sampler = make_sampler(temp=0.0)
    return generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens,
                    sampler=sampler, verbose=False)


# --------------------------------------------------------------------------- #
# metrics
# --------------------------------------------------------------------------- #

def evaluate_task_a(model, tokenizer, samples: list[dict],
                    connection: sqlite3.Connection, schema_text: str,
                    label: str) -> dict:
    """Parse rate and set equality over a query set."""
    parsed_ok = 0
    set_equal = 0
    exact = 0
    failures: list[dict] = []
    started = time.monotonic()

    for index, sample in enumerate(samples, start=1):
        question = sample["question"]
        gold = sample["gold"]
        raw = generate_one(model, tokenizer, question, schema_text)
        text = extract_json(raw)

        try:
            predicted = parse(text)
        except QueryError as exc:
            failures.append({"question": question, "raw": raw[:300],
                             "error": str(exc)[:200], "stage": "parse"})
            continue
        parsed_ok += 1

        try:
            gold_query = parse(gold)
        except QueryError as exc:
            # A bad gold is a corpus bug, not a model failure.
            failures.append({"question": question, "error": f"gold invalid: {exc}",
                             "stage": "gold"})
            continue

        if predicted.as_dict() == gold_query.as_dict():
            exact += 1

        # Set equality is the primary metric: two different queries that select
        # the same rows are both correct.
        try:
            if row_identity_set(connection, predicted) == \
                    row_identity_set(connection, gold_query):
                set_equal += 1
            else:
                failures.append({
                    "question": question, "stage": "set_equality",
                    "predicted": predicted.as_dict(), "gold": gold_query.as_dict(),
                })
        except sqlite3.Error as exc:
            failures.append({"question": question, "stage": "execute",
                             "error": str(exc)[:160]})

        if index % 25 == 0:
            rate = index / max(1e-9, time.monotonic() - started)
            log_event("3.8", f"{label}: {index}/{len(samples)} evaluated "
                             f"({rate:.2f}/s), parse {parsed_ok / index:.3f}, "
                             f"set equality {set_equal / index:.3f}.")

    total = len(samples)
    return {
        "n": total,
        "parse_rate": round(parsed_ok / total, 4) if total else None,
        "set_equality": round(set_equal / total, 4) if total else None,
        "exact_match": round(exact / total, 4) if total else None,
        "failures": failures[:60],
        "seconds": round(time.monotonic() - started, 1),
    }


def evaluate_preference(model, tokenizer, pairs: list[dict],
                        schema_text: str) -> dict:
    """Per-mode win rate by comparing sequence log-likelihoods.

    A preference is a win when the model assigns the chosen completion a higher
    average log-likelihood than the rejected one. This measures the behaviour the
    preference stage is meant to install without needing a second model.
    """
    import mlx.core as mx

    def score(question: str, system: str, completion: str) -> float:
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": question}]
        prefix = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        prefix_ids = tokenizer.encode(prefix)
        full_ids = tokenizer.encode(prefix + completion)
        if len(full_ids) <= len(prefix_ids):
            return float("-inf")
        tokens = mx.array([full_ids])
        logits = model(tokens[:, :-1])
        targets = tokens[:, 1:]
        logprobs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        picked = mx.take_along_axis(logprobs, targets[..., None], axis=-1)[..., 0]
        start = len(prefix_ids) - 1
        completion_logprobs = picked[0, start:]
        mx.eval(completion_logprobs)
        return float(completion_logprobs.mean().item())

    by_mode: dict[str, dict[str, int]] = {}
    for pair in pairs:
        mode = pair["mode"]
        tally = by_mode.setdefault(mode, {"wins": 0, "n": 0})
        try:
            chosen = score(pair["prompt"], pair.get("system", SYSTEM), pair["chosen"])
            rejected = score(pair["prompt"], pair.get("system", SYSTEM), pair["rejected"])
        except Exception:  # noqa: BLE001
            continue
        tally["n"] += 1
        if chosen > rejected:
            tally["wins"] += 1

    return {
        mode: {
            "win_rate": round(tally["wins"] / tally["n"], 4) if tally["n"] else None,
            "n": tally["n"],
        }
        for mode, tally in sorted(by_mode.items())
    }


def evaluate_abstention(model, tokenizer, samples: list[dict],
                        schema_text: str) -> dict:
    """Fabrication rate, which spec 9.5 requires to be exactly 0.

    A fabrication is any numeral in the output that is not present in the input,
    or an invented PDB identifier, or claiming the question is answerable when the
    gold says it is not.
    """
    from lm.probes import fabricates

    fabrications: list[dict] = []
    abstained = 0
    for sample in samples:
        question = sample["messages"][1]["content"]
        raw = generate_one(model, tokenizer, question, schema_text, max_tokens=220)
        verdict = fabricates(question, raw)
        if verdict["fabricates"]:
            fabrications.append({"question": question, "raw": raw[:260],
                                 "why": verdict["why"]})
        if verdict["abstains"]:
            abstained += 1
    total = len(samples)
    return {
        "n": total,
        "fabrication_rate": round(len(fabrications) / total, 4) if total else None,
        "abstention_rate": round(abstained / total, 4) if total else None,
        "fabrications": fabrications[:40],
    }


# --------------------------------------------------------------------------- #
# query-set loading
# --------------------------------------------------------------------------- #

def load_query_set(path: Path, limit: int | None = None) -> list[dict]:
    """Load a chat-format corpus file into (question, gold) pairs."""
    samples: list[dict] = []
    if not path.exists():
        return samples
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "messages" in row:
                samples.append({
                    "question": row["messages"][1]["content"],
                    "gold": json.loads(row["messages"][2]["content"]),
                })
            elif "normalised_query" in row:
                samples.append({
                    "question": row["normalised_query"],
                    "gold": row["gold_object"],
                    "source_doi": row.get("source_doi"),
                    "original_sentence": row.get("original_sentence"),
                })
    if limit is not None:
        samples = samples[:limit]
    return samples


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def run(model_path: str = BASE_MODEL, adapter_path: str | None = None,
        limit: int | None = 120, stage_label: str = "baseline",
        skip_preference: bool = False) -> dict:
    config = load_config()
    if not DB_PATH.exists():
        raise SystemExit("the atlas must be built before set equality can be measured")

    # Zero-shot needs the schema in context; a fine-tuned run must not have it.
    schema_text = "" if adapter_path else json.dumps(
        compact_schema(), separators=(",", ":"))
    log_event("3.0" if stage_label == "baseline" else "3.8",
              f"{stage_label}: loading {model_path}"
              + (f" with adapters at {adapter_path}" if adapter_path else " zero-shot"))
    model, tokenizer = load_model(model_path, adapter_path)

    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        synthetic = load_query_set(CORPUS / "task_a_test.jsonl", limit)
        external = load_query_set(CORPUS / "external_queries.jsonl")

        results: dict = {
            "stage": stage_label,
            "generated_at": utcnow(),
            "model": model_path,
            "adapter": adapter_path or "",
            "atlas": str(DB_PATH),
            "prompt_style": (
                "trained system turn, no schema in context"
                if adapter_path else "zero-shot with the full schema in context"
            ),
            "prompt_tokens_approx": 83 if adapter_path else 841,
        }

        results["task_a_synthetic"] = evaluate_task_a(
            model, tokenizer, synthetic, connection, schema_text,
            f"{stage_label} synthetic")

        if external:
            results["task_a_external"] = evaluate_task_a(
                model, tokenizer, external, connection, schema_text,
                f"{stage_label} external")
            # The gap between the two is the register-mismatch signal (spec 3.6).
            synthetic_score = results["task_a_synthetic"]["set_equality"]
            external_score = results["task_a_external"]["set_equality"]
            if synthetic_score is not None and external_score is not None:
                results["register_mismatch_gap"] = round(
                    synthetic_score - external_score, 4)
        else:
            results["task_a_external"] = {
                "computed": False,
                "reason": ("external_queries.jsonl has not been built. Run "
                           "lm/harvest_external_queries.py (spec 3.6)."),
            }

        if not skip_preference:
            pairs = []
            path = CORPUS / "task_a_preference.jsonl"
            if path.exists():
                with path.open(encoding="utf-8") as handle:
                    all_pairs = [json.loads(line) for line in handle if line.strip()]
                # Sample evenly per mode so every mode is reported.
                per_mode: dict[str, list[dict]] = {}
                for pair in all_pairs:
                    per_mode.setdefault(pair["mode"], []).append(pair)
                for mode_pairs in per_mode.values():
                    pairs.extend(mode_pairs[:20])
            if pairs:
                results["preference_win_rates"] = evaluate_preference(
                    model, tokenizer, pairs, schema_text)

        abstention = load_query_set(CORPUS / "task_c_test.jsonl")
        if (CORPUS / "task_c_test.jsonl").exists():
            with (CORPUS / "task_c_test.jsonl").open(encoding="utf-8") as handle:
                task_c = [json.loads(line) for line in handle if line.strip()][:40]
            if task_c:
                results["task_c"] = evaluate_abstention(
                    model, tokenizer, task_c, schema_text)

        # Spec 3.0: the decision this run exists to make.
        # Spec 3.0's decision is about the BASE model, so it is only recorded on
        # a baseline run. Emitting it on a fine-tuned run would read as "the
        # fine-tune was unnecessary" when it is simply measuring the fine-tune.
        if not adapter_path:
            threshold = float(config.t("validation.lm_baseline_skip_finetune_at"))
            score = results["task_a_synthetic"]["set_equality"] or 0.0
            results["baseline_decision"] = {
                "threshold": threshold,
                "set_equality": score,
                "skip_task_a_finetune": bool(score >= threshold),
                "note": (
                    "Spec 3.0: if the base model already reaches the threshold "
                    "zero-shot, Task A is not fine-tuned and grammar-constrained "
                    "decoding ships instead."
                ),
            }
    finally:
        connection.close()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    previous = {}
    if REPORT.exists():
        try:
            previous = json.loads(REPORT.read_text())
        except json.JSONDecodeError:
            previous = {}
    previous[stage_label] = results
    REPORT.write_text(json.dumps(previous, indent=2, default=str) + "\n")

    Manifest(STAGE).record(
        stage_label, status="ok",
        parse_rate=results["task_a_synthetic"]["parse_rate"],
        set_equality=results["task_a_synthetic"]["set_equality"],
    )
    log_event("3.0" if stage_label == "baseline" else "3.8",
              f"{stage_label}: parse rate "
              f"{results['task_a_synthetic']['parse_rate']}, set equality "
              f"{results['task_a_synthetic']['set_equality']} on "
              f"{results['task_a_synthetic']['n']} synthetic queries.")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate BINMAN-LM")
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--skip-preference", action="store_true")
    args = parser.parse_args()
    results = run(model_path=args.model, adapter_path=args.adapter,
                  limit=args.limit, stage_label=args.label,
                  skip_preference=args.skip_preference)
    print(json.dumps({k: v for k, v in results.items() if k != "task_a_synthetic"},
                     indent=2, default=str))
    summary = results["task_a_synthetic"]
    print(f"\nsynthetic: n={summary['n']} parse={summary['parse_rate']} "
          f"set_equality={summary['set_equality']} exact={summary['exact_match']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
