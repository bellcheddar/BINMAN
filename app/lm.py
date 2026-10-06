"""BINMAN-LM client, feature-flagged (spec 3.9).

The language model is optional. When `BINMAN_LM_URL` is unset or unreachable the
UI falls back to the manual query builder with no error and no degraded
functionality beyond losing the natural-language box.

**The model never produces a number that reaches the user.** It returns a query
object, which `app.queries` validates and executes deterministically. Any
numeric value in a response is either a filter threshold the user will see in
the query stack, or it is rejected by the parser.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

# The four classes Task B ships. `bivalent_inhibitor` is a fifth in the spec and
# is not built, because its label cannot be derived from what the pipeline
# produces and inventing it would be this project's judgement.
TRIAGE_CLASSES = ("molecular_glue", "protac", "native_cofactor",
                  "crystallisation_artefact")

# The canonical triage prompt, and the reason it is here rather than copied.
# app/lm.py carried a SHORTER version of this that omitted the class list. It
# was dead code, which is the only reason it did no harm: anything wired to it
# would have asked the model a prompt it was never trained on and been scored
# against a 0.9336 macro F1 measured on a different one.
TRIAGE_SYSTEM = (
    "<task>triage</task>\n"
    "You classify a structure into exactly one evidence class. Reply with a "
    "single class token and nothing else. The classes are: "
    + ", ".join(TRIAGE_CLASSES) + "."
)

# The canonical abstain prompt. Imported by lm/build_corpus.py and
# lm/evaluate.py rather than copied: it was written out three times, and a
# training corpus whose system message has drifted from the serving one is a
# model evaluated on a prompt it was never trained for.
ABSTAIN_SYSTEM = (
    "<task>abstain</task>\n"
    "You decide whether a question can be answered from the BINMAN atlas. "
    "Reply with JSON only: `answerable` true or false, `missing` listing what "
    "is absent, and a one sentence `explanation`. Answer true when the atlas "
    "holds the records the question asks about. Never fabricate a ligase, a PDB "
    "identifier or a number."
)

SYSTEM_PROMPTS = {
    "query": (
        "<task>query</task>\n"
        "You translate a natural language question into a BINMAN query object. "
        "Reply with JSON only. Use only the fields, operators and values given "
        "in the schema. Never invent a field, a ligase or a PDB identifier. "
        "Never compute or estimate a numeric value."
    ),
    "triage": TRIAGE_SYSTEM,
    # The old wording was "you state precisely what is missing when a question
    # cannot be answered", which presupposes the answer. Trained on refusals
    # only and prompted as though refusing were the job, the head refused every
    # answerable question put to it: specificity 0.000 (D-086, D-091). This asks
    # for the decision first and the explanation second.
    "abstain": ABSTAIN_SYSTEM,
}


@dataclass
class LmResult:
    ok: bool
    payload: dict | None = None
    text: str = ""
    error: str = ""


def endpoint() -> str:
    return os.environ.get("BINMAN_LM_URL", "").strip()


def enabled() -> bool:
    return bool(endpoint())


def _ask(system: str, user: str, timeout: float, max_tokens: int = 512) -> LmResult:
    """One call to the model. Never raises: an unreachable LM is a normal state."""
    url = endpoint()
    if not url:
        return LmResult(ok=False, error="BINMAN_LM_URL is not set")
    try:
        import httpx
    except ImportError as exc:
        return LmResult(ok=False, error=f"the LM client is not installed: {exc}")
    body = {"messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": max_tokens, "temperature": 0.0}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url.rstrip("/") + "/v1/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
        return LmResult(ok=True, text=(data["choices"][0]["message"]["content"] or "").strip())
    except Exception as exc:  # noqa: BLE001
        return LmResult(ok=False, error=f"{type(exc).__name__}: {exc}"[:200])


def explain_refusal(question: str, timeout: float = 20.0) -> LmResult:
    """Why a question cannot be answered from the atlas, in the model's words.

    The abstain head was trained, scored at a 0.0 fabrication rate over 40
    unanswerable questions, and then called by nothing. A question the schema
    cannot answer went to the query head, came back as a query object naming a
    field that does not exist, and reached the user as "the model proposed an
    invalid query: field 'binding_affinity' is not a field of bridge". That is
    the parser's complaint about the model, not an answer to the person.

    This asks the head that was trained for the job. It returns
    {"answerable": false, "missing": [...], "explanation": "..."} and the
    explanation is what the user sees.
    """
    result = _ask(SYSTEM_PROMPTS["abstain"], question, timeout, max_tokens=220)
    if not result.ok:
        return result
    candidate = result.text
    if "```" in candidate:
        for part in candidate.split("```"):
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                candidate = stripped
                break
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return LmResult(ok=False, text=result.text,
                        error="the model did not explain in JSON")
    return LmResult(ok=True, payload=payload, text=result.text)


def propose_query(question: str, schema: dict, timeout: float = 20.0) -> LmResult:
    """Ask the model for a query object. Never raises: the UI degrades instead."""
    url = endpoint()
    if not url:
        return LmResult(ok=False, error="BINMAN_LM_URL is not set")

    try:
        import httpx
    except ImportError as exc:  # a host without the transport is a normal state
        return LmResult(ok=False, error=f"the LM client is not installed: {exc}")

    body = {
        "messages": [
            {"role": "system",
             "content": SYSTEM_PROMPTS["query"] + "\n\nSchema:\n"
                        + json.dumps(schema, separators=(",", ":"))},
            {"role": "user", "content": question},
        ],
        "max_tokens": 512,
        "temperature": 0.0,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url.rstrip("/") + "/v1/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
        text = (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001 - unreachable LM is a normal state
        return LmResult(ok=False, error=f"{type(exc).__name__}: {exc}"[:200])

    # The model is asked for JSON only; tolerate a fenced block around it.
    candidate = text
    if "```" in candidate:
        parts = candidate.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                candidate = stripped
                break
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return LmResult(ok=False, text=text, error="the model did not return JSON")
    return LmResult(ok=True, payload=payload, text=text)
