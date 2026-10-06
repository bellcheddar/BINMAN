"""The prompt the model was trained on is the prompt it is asked.

A system prompt that drifts between the corpus builder, the build-time
inference stage and the serving app is the quietest failure in the project:
every metric still computes, the model still answers, and the number quoted on
the About page describes a prompt nobody sends any more.

It had already happened twice. The abstain prompt was written out in three
files, and the one in app/lm.py presupposed the answer it was asking for. The
triage prompt in app/lm.py omitted the class list entirely, and was dead code,
which is the only reason it did no harm.

Each prompt has one definition now, in the module that serves it, and these
assert that rather than trusting it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_the_abstain_prompt_has_one_definition():
    from app.lm import ABSTAIN_SYSTEM, SYSTEM_PROMPTS
    from lm.build_corpus import SYSTEM_ABSTAIN
    from lm.evaluate import ABSTAIN_SYSTEM as EVALUATED

    assert SYSTEM_PROMPTS["abstain"] == ABSTAIN_SYSTEM
    assert SYSTEM_ABSTAIN == ABSTAIN_SYSTEM, "the corpus trains a different prompt"
    assert EVALUATED == ABSTAIN_SYSTEM, "the evaluator scores a different prompt"


def test_the_triage_prompt_has_one_definition():
    from app.lm import TRIAGE_SYSTEM, SYSTEM_PROMPTS
    from lm.build_task_b import SYSTEM_TRIAGE as TRAINED
    from pipeline.triage_predict import SYSTEM_TRIAGE as INFERRED

    assert SYSTEM_PROMPTS["triage"] == TRIAGE_SYSTEM
    assert TRAINED == TRIAGE_SYSTEM, "the corpus trains a different prompt"
    assert INFERRED == TRIAGE_SYSTEM, "the atlas was filled with a different prompt"


def test_the_triage_prompt_names_every_class_it_may_be_answered_with():
    """The shorter copy omitted the class list, which is the whole instruction
    for a single-token classifier."""
    from app.lm import TRIAGE_CLASSES, TRIAGE_SYSTEM
    from lm.build_task_b import CLASSES

    assert tuple(CLASSES) == TRIAGE_CLASSES
    for name in TRIAGE_CLASSES:
        assert name in TRIAGE_SYSTEM


def test_the_abstain_prompt_asks_for_a_decision_rather_than_assuming_one():
    """It used to open "you state precisely what is missing when a question
    cannot be answered", which answers the question inside the prompt. Trained
    on refusals and prompted that way, the head refused everything."""
    from app.lm import ABSTAIN_SYSTEM

    assert "cannot be answered" not in ABSTAIN_SYSTEM
    assert "decide whether" in ABSTAIN_SYSTEM.lower()
    assert "answerable" in ABSTAIN_SYSTEM


def test_every_head_the_model_card_lists_is_wired_to_something():
    """Three tasks were trained and one of them was called by nothing for most
    of this build. A head with no caller is a head whose metric describes
    nothing that ships."""
    import app.routes.api as api
    import pipeline.triage_predict as triage
    from app import lm

    source = Path(api.__file__).read_text(encoding="utf-8")
    assert "lm.propose_query" in source, "the query head has no caller"
    assert "lm.explain_refusal" in source, "the abstain head has no caller"
    assert hasattr(triage, "load_into_atlas"), "the triage head has no caller"
    assert set(lm.SYSTEM_PROMPTS) == {"query", "triage", "abstain"}
