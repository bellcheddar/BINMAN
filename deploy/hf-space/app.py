"""BINMAN-LM on ZeroGPU: the three text jobs, and none of the arithmetic.

The model turns a question into a query object, triages a bridging ligand into
an evidence class, and abstains when the atlas schema cannot answer. It does
not compute, estimate or report a number: every figure in BINMAN comes from
deterministic Python over the atlas, and the model never sees a calculator.

That constraint is the point of this demo rather than a limitation of it. A
model that will happily invent a dSASA is the failure mode the project is
built to avoid, so the Abstention tab is as much the demo as the query tab.

The atlas itself is NOT served here. It is 142 MB and several of the datasets
behind it carry licences that do not permit redistribution, so this Space shows
what the model produces and the repository shows what the pipeline computes.
"""

from __future__ import annotations

import json
import os

import gradio as gr
import spaces
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_REPO = os.environ.get("BINMAN_ADAPTER_REPO", "Dellboy/binman-lm-adapter")
# The adapter repository is public by Marc's decision (DECISIONS D-030), which
# records the reasoning and the one term it runs against. No token is needed,
# but one is still read if present so a private repo keeps working unchanged.
HF_TOKEN = os.environ.get("HF_TOKEN")

TRAINED_SYSTEM = (
    "You translate a question about the BINMAN atlas into a query object. "
    "Reply with one JSON object and nothing else."
)
TRIAGE_SYSTEM = (
    "<task>triage</task>\n"
    "You classify a structure into exactly one evidence class. Reply with a "
    "single class token and nothing else. The classes are: "
    "crystallisation_artefact, molecular_glue, native_cofactor, protac."
)
ABSTAIN_SYSTEM = (
    "You translate a question about the BINMAN atlas into a query object. "
    "If the atlas schema cannot answer the question, reply with "
    '{"abstain": true, "reason": "<why>"} and nothing else.'
)

_model = None
_tokenizer = None


def _load():
    """Load once, on first GPU call. ZeroGPU hands the GPU over per request."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    _tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16, device_map="cuda")
    _model = PeftModel.from_pretrained(model, ADAPTER_REPO, token=HF_TOKEN).eval()
    return _model, _tokenizer


@spaces.GPU(duration=60)
def _answer(question: str, system: str, max_new_tokens: int) -> str:
    model, tokenizer = _load()
    text = tokenizer.apply_chat_template(
        [{"role": "system", "content": system},
         {"role": "user", "content": question}],
        tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens,
                                do_sample=False,
                                pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(output[0][inputs["input_ids"].shape[1]:],
                            skip_special_tokens=True).strip()


def pretty(raw: str) -> str:
    """Show the query object as JSON when it is JSON, and raw when it is not.

    A malformed object is shown as the model produced it rather than repaired:
    the parse rate is a reported metric, so hiding a failure here would hide
    the thing worth looking at.
    """
    try:
        return json.dumps(json.loads(raw), indent=2)
    except json.JSONDecodeError:
        return raw


def task_a(question: str) -> str:
    if not question.strip():
        return ""
    return pretty(_answer(question, TRAINED_SYSTEM, 320))


def task_b(description: str) -> str:
    if not description.strip():
        return ""
    return _answer(description, TRIAGE_SYSTEM, 16)


def task_c(question: str) -> str:
    if not question.strip():
        return ""
    return pretty(_answer(question, ABSTAIN_SYSTEM, 220))


INTRO = """
# BINMAN-LM

The small language model behind
[**BINMAN**](https://github.com/bellcheddar/BINMAN), an atlas of bridging
ligands (molecular glues), structural degrons, E3 ligase triage and
degradability built from the PDB.

Qwen2.5-3B-Instruct with a LoRA adapter, trained on Apple silicon with
`mlx-lm` and converted to run here. **It does three text jobs and no
arithmetic**: every number in BINMAN is computed deterministically in Python
over the atlas and passed to the interface. A figure in this model's output
that was not copied verbatim from a retrieved record is a defect, not a
feature.

The atlas is not served here: it is 142 MB and several source datasets carry
licences that do not permit redistribution.
"""

with gr.Blocks(title="BINMAN-LM") as demo:
    gr.Markdown(INTRO)

    with gr.Tab("Query translation"):
        gr.Markdown(
            "Natural language to a query object against the atlas schema. "
            "Parse rate and set equality against held-out questions are "
            "reported in the repository's `FINDINGS.md`.")
        question = gr.Textbox(
            label="Question",
            placeholder="Which ligands bridge two different chains with a "
                        "bridging balance above 0.5?")
        out_a = gr.Code(label="Query object", language="json")
        gr.Button("Translate", variant="primary").click(task_a, question, out_a)
        gr.Examples([
            "Which bridges have a bridging balance above 0.8?",
            "Show me glue candidates in structures better than 2 Angstrom",
            "Which E3 ligases have a pocket score above 0.7 and no ligand yet?",
        ], question)

    with gr.Tab("Evidence triage"):
        gr.Markdown(
            "Classify a bridging ligand into one of four evidence classes. "
            "The confusable pair is molecular glue against PROTAC, and the "
            "repository reports the full confusion matrix rather than only "
            "the macro-F1.")
        description = gr.Textbox(label="Ligand or structure description", lines=4)
        out_b = gr.Textbox(label="Class")
        gr.Button("Triage", variant="primary").click(task_b, description, out_b)
        gr.Examples([
            "A bivalent degrader with a cereblon-binding glutarimide joined by "
            "a PEG linker to a BRD4 bromodomain ligand.",
            "Polyethylene glycol fragment modelled at a lattice contact.",
            "Flavin adenine dinucleotide bound in the canonical Rossmann pocket.",
        ], description)

    with gr.Tab("Abstention"):
        gr.Markdown(
            "Questions the atlas schema cannot answer. The model should "
            "**refuse** rather than invent a field: a fabricated number is "
            "the failure this task exists to measure.")
        unanswerable = gr.Textbox(label="Question", lines=2)
        out_c = gr.Code(label="Response", language="json")
        gr.Button("Ask", variant="primary").click(task_c, unanswerable, out_c)
        gr.Examples([
            "What is the binding affinity of this glue in nanomolar?",
            "Which of these compounds passed phase II trials?",
            "What is the melting temperature of the complex?",
        ], unanswerable)

if __name__ == "__main__":
    demo.launch()
