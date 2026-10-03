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

SYSTEM_PROMPTS = {
    "query": (
        "<task>query</task>\n"
        "You translate a natural language question into a BINMAN query object. "
        "Reply with JSON only. Use only the fields, operators and values given "
        "in the schema. Never invent a field, a ligase or a PDB identifier. "
        "Never compute or estimate a numeric value."
    ),
    "triage": (
        "<task>triage</task>\n"
        "You classify a structure or abstract into exactly one evidence class. "
        "Reply with a single class token and nothing else."
    ),
    "abstain": (
        "<task>abstain</task>\n"
        "You state precisely what is missing when a question cannot be answered "
        "from the atlas. Never fabricate a ligase, a PDB identifier or a number."
    ),
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


def propose_query(question: str, schema: dict, timeout: float = 20.0) -> LmResult:
    """Ask the model for a query object. Never raises: the UI degrades instead."""
    url = endpoint()
    if not url:
        return LmResult(ok=False, error="BINMAN_LM_URL is not set")

    import httpx

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
