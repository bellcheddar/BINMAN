"""The abstention check, exercised without a model.

A training round calls this at the end of four hours. If the `--adapter` path
is broken, the measurement the round exists for is lost after the expensive
part is already done, and the only way to find out is to spend the four hours.

So the model is stubbed and the plumbing is tested: that `mlx_lm.load` is
handed the adapter and the base model, that the generator is asked with the
abstain system prompt, that a fenced JSON reply is unwrapped, and that a head
which answers correctly scores 1.0 on both halves. That last one matters on its
own: a metric reading 0.000 should be a fact about the model, and this shows the
measurement can read something else.

Nothing here touches the network, the GPU or a checkpoint.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def stubbed(monkeypatch):
    """A perfect head, and a record of how it was called."""
    import lm.evaluate as evaluate
    import pipeline.lm_abstention_check as check

    calls: dict = {"load": None, "systems": [], "questions": []}

    fake_mlx = types.ModuleType("mlx_lm")

    def fake_load(model_name, adapter_path=None):
        calls["load"] = (model_name, adapter_path)
        return ("MODEL", "TOKENIZER")

    fake_mlx.load = fake_load
    monkeypatch.setitem(sys.modules, "mlx_lm", fake_mlx)

    answerable = set(check.answerable_questions())

    def fake_generate_one(model, tokenizer, question, schema_text,
                          max_tokens=320, system_override=None):
        calls["systems"].append(system_override)
        calls["questions"].append(question)
        # Fenced, because the served model fences and the unwrapping is part of
        # what is being tested.
        return "```json\n" + json.dumps({
            "answerable": question in answerable,
            "missing": [],
            "explanation": "stub",
        }) + "\n```"

    monkeypatch.setattr(evaluate, "generate_one", fake_generate_one)
    return check, calls


def test_the_adapter_path_loads_the_adapter_over_the_base_model(stubbed, tmp_path, monkeypatch):
    check, calls = stubbed
    monkeypatch.setattr(check, "REPORT", tmp_path / "report.json")
    check.run(limit=5, adapter="models/binman-lm/adapters",
              model_name="mlx-community/Qwen2.5-3B-Instruct-4bit")
    assert calls["load"] == ("mlx-community/Qwen2.5-3B-Instruct-4bit",
                             "models/binman-lm/adapters")


def test_every_question_is_asked_with_the_abstain_prompt(stubbed, tmp_path, monkeypatch):
    from app.lm import ABSTAIN_SYSTEM

    check, calls = stubbed
    monkeypatch.setattr(check, "REPORT", tmp_path / "report.json")
    check.run(limit=5, adapter="adapters", model_name="base")
    assert calls["systems"], "nothing was asked"
    assert all(system == ABSTAIN_SYSTEM for system in calls["systems"])


def test_a_head_that_answers_correctly_scores_one_on_both_halves(stubbed, tmp_path, monkeypatch):
    """The point of the specificity metric is that it can read something other
    than zero. A measurement that cannot register success is not a check."""
    check, calls = stubbed
    monkeypatch.setattr(check, "REPORT", tmp_path / "report.json")
    report = check.run(limit=20, adapter="adapters", model_name="base")
    assert report["abstention_recall"] == 1.0
    assert report["abstention_specificity"] == 1.0
    assert report["false_abstentions"] == []
    assert report["n_answerable"] == 12
    assert report["asked_of"].startswith("local adapter")


def test_the_unanswerable_set_excludes_the_answerable_rows(stubbed, tmp_path, monkeypatch):
    """Task C used to be refusals only, so taking test rows in order was safe.
    It carries an answerable class now, and reading the file blind would feed
    answerable questions in as unanswerable ones."""
    check, _ = stubbed
    questions = check.unanswerable_questions(50)
    corpus = ROOT / "lm" / "corpus" / "task_c_test.jsonl"
    if not corpus.exists():
        pytest.skip("Task C test split not built")
    answerable_prompts = set()
    for line in corpus.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("kind") == "answerable":
            user = next((m["content"] for m in row["messages"]
                         if m.get("role") == "user"), None)
            if user:
                answerable_prompts.add(user)
    assert answerable_prompts, "the corpus has no answerable rows to confuse it with"
    assert not (set(questions) & answerable_prompts)
