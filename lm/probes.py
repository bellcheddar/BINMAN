"""Model sanity probes (spec 10, "Model sanity").

Asserts the one invariant the whole design rests on: **BINMAN-LM never emits a
numeral that is not copied from its input.** Every number in BINMAN is computed
deterministically in Python, so a numeral the model invented is a defect.
"""

from __future__ import annotations

import re

NUMERAL = re.compile(r"-?\d+(?:\.\d+)?")
PDB_ID = re.compile(r"\b[1-9][A-Za-z0-9]{3}\b")

# Numerals that are structural rather than claims: a limit, a JSON version, an
# operator's own value echoed back. These are allowed when they appear in the
# input or are part of the query-object envelope.
STRUCTURAL = {"0", "1", "200", "2", "3"}


def numerals(text: str) -> set[str]:
    return {m.group(0) for m in NUMERAL.finditer(text or "")}


def fabricates(question: str, answer: str) -> dict:
    """Does the answer contain a number or identifier the question did not?

    Returns a verdict with the reason, so a failing probe names the behaviour
    rather than just failing.
    """
    reasons: list[str] = []

    question_numerals = numerals(question)
    answer_numerals = numerals(answer)
    invented = {
        value for value in answer_numerals - question_numerals
        if value not in STRUCTURAL
    }
    if invented:
        reasons.append(f"numerals not present in the question: {sorted(invented)}")

    question_ids = {m.group(0).upper() for m in PDB_ID.finditer(question or "")}
    answer_ids = {m.group(0).upper() for m in PDB_ID.finditer(answer or "")}
    # A PDB-shaped token is only a fabrication when it is not a numeral already
    # accounted for and not echoed from the question.
    invented_ids = {
        value for value in answer_ids - question_ids
        if not value.isdigit()
    }
    if invented_ids:
        reasons.append(f"identifiers not present in the question: {sorted(invented_ids)}")

    lowered = (answer or "").lower()
    abstains = (
        '"answerable":false' in lowered.replace(" ", "")
        or "answerable\": false" in lowered
        or "cannot" in lowered or "missing" in lowered or "not available" in lowered
    )

    return {
        "fabricates": bool(reasons),
        "why": "; ".join(reasons),
        "abstains": abstains,
    }
