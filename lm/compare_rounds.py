"""Compare training rounds side by side, so the morning is one table.

Reads `models/binman-lm/overnight/results.jsonl`, which the overnight sweep
appends to as each round finishes, plus any earlier evaluation on disk. Prints
the metrics that decide which adapter ships and nothing else.

**It names a winner only where one metric dominates.** Task A set equality,
Task B macro-F1 and Task C abstention do not have to agree, and a round that
wins on one while losing another is reported as exactly that rather than
collapsed into a single score this project never defined.

**Task C is two numbers, not one.** Abstention recall is measured on
unanswerable questions alone, so a head that refuses every question scores 1.0
on it. One did. Specificity, the rate at which it correctly declines to abstain
on questions the atlas can answer, is the number that separates a useful head
from a broken one, and this table read without it would have named a winner on
a metric that cannot fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "models" / "binman-lm" / "overnight" / "results.jsonl"

# The three numbers that decide the shipped adapter, with the direction that
# counts as better and the floor spec 9.5 sets where it sets one.
METRICS = [
    ("task_a_synthetic", "set_equality", "Task A set equality", 0.90),
    ("task_a_synthetic", "parse_rate", "Task A parse rate", 0.99),
    ("task_b", "macro_f1", "Task B macro-F1", 0.85),
    ("task_c", "abstention_rate", "Task C recall", None),
    ("task_c", "fabrication_rate", "Task C fabrication", None),
    # The metric this comparison existed without. Abstention recall is measured
    # on unanswerable questions alone, so a head that refuses everything scores
    # 1.0 on it, and one did: the table named a winner on a number that could
    # not fail. Specificity is the complement, measured on questions the atlas
    # demonstrably answers, and it is read from the row's own `specificity`
    # blob rather than from the evaluation (D-086, D-087).
    ("specificity", "abstention_specificity", "Task C specificity", 0.90),
]
# Lower is better for exactly one of them.
LOWER_IS_BETTER = {"fabrication_rate"}


def dig(blob: dict, task: str, metric: str):
    section = blob.get(task)
    if not isinstance(section, dict):
        return None
    value = section.get(metric)
    return value if isinstance(value, (int, float)) else None


def load(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args()

    rows = load(args.results)
    if not rows:
        print(f"No results yet at {args.results}")
        return 0

    rounds = []
    for row in rows:
        blob = row.get("eval")
        if not isinstance(blob, dict):
            continue
        # The specificity check is its own stage, so it arrives as a sibling of
        # `eval` rather than inside it. Folded in under its own key so `dig`
        # reaches it the same way as everything else, and a round measured
        # before the check existed simply shows a dash.
        merged = dict(blob)
        if isinstance(row.get("specificity"), dict):
            merged["specificity"] = row["specificity"]
        rounds.append((row.get("label", "?"), merged))

    if not rounds:
        print("Results file has no readable evaluations.")
        return 0

    width = max(len(label) for label, _ in rounds) + 2
    print(f"{'round'.ljust(width)}" + "".join(f"{name:>22}" for _t, _m, name, _f in METRICS))
    print("-" * (width + 22 * len(METRICS)))
    for label, blob in rounds:
        cells = []
        for task, metric, _name, _floor in METRICS:
            value = dig(blob, task, metric)
            cells.append("        -" if value is None else f"{value:>22.4f}")
        print(label.ljust(width) + "".join(cells))

    print()
    for task, metric, name, floor in METRICS:
        scored = [(label, dig(blob, task, metric)) for label, blob in rounds]
        scored = [(label, value) for label, value in scored if value is not None]
        if not scored:
            continue
        best = (min if metric in LOWER_IS_BETTER else max)(scored, key=lambda p: p[1])
        verdict = ""
        if floor is not None:
            verdict = "  (clears floor)" if best[1] >= floor else f"  (MISSES floor {floor})"
        print(f"{name:<24} best: {best[0]} at {best[1]:.4f}{verdict}")

    winners = set()
    for task, metric, _name, _floor in METRICS:
        scored = [(label, dig(blob, task, metric)) for label, blob in rounds]
        scored = [(label, value) for label, value in scored if value is not None]
        if scored:
            winners.add((min if metric in LOWER_IS_BETTER else max)(
                scored, key=lambda p: p[1])[0])
    print()
    if len(winners) == 1:
        print(f"One round wins every metric: {winners.pop()}")
    else:
        print("No round wins everything. Rounds taking at least one metric: "
              + ", ".join(sorted(winners)))
        print("Pick on Task B macro-F1 unless Task C fabrication rose above zero, "
              "which is disqualifying regardless of the rest.")

    # Recall and fabrication are both measured on unanswerable questions only,
    # so a head that refuses everything takes them both. Saying which rounds
    # did that is the difference between this table informing a decision and
    # rubber-stamping one.
    degenerate = [
        label for label, blob in rounds
        if dig(blob, "task_c", "abstention_rate") == 1.0
        and dig(blob, "specificity", "abstention_specificity") in (None, 0.0)
    ]
    if degenerate:
        print()
        print("Task C recall 1.0 with specificity 0.0 or unmeasured, which is what "
              "a head that refuses every question looks like: "
              + ", ".join(degenerate))
        print("Recall and fabrication are measured on unanswerable questions alone, "
              "so neither can fail that way. Specificity is the one that can.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
