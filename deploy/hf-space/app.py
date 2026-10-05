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

# ZeroGPU rules, learned the hard way, both failure modes recorded in D-037:
#
#   * The main process must NOT initialise CUDA. Building the model at import
#     time raised "RuntimeError: No CUDA GPUs are available" from inside
#     spaces' torch patching, because PEFT touches CUDA while attaching.
#   * The GPU is granted per request with a time limit, so downloading six
#     gigabytes of base model inside that window fails with an error carrying
#     no traceback.
#
# So: download at import (pure HTTP, no torch), build the model on first GPU
# call, and keep it for later calls.
_model = None
_tokenizer = None


def _prefetch() -> None:
    """Pull weights to local disk at startup, outside the GPU budget."""
    from huggingface_hub import snapshot_download

    snapshot_download(BASE_MODEL,
                      allow_patterns=["*.json", "*.safetensors", "*.txt"])
    snapshot_download(ADAPTER_REPO, token=HF_TOKEN)


def _device_and_dtype():
    """Run on the GPU, and stay usable on CPU hardware if it is ever moved.

    Kept because it costs nothing and makes the Space independent of the
    hardware setting: bfloat16 fits a 3B model in 16 GB where float32 would
    not. The Space runs on ZeroGPU.
    """
    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.bfloat16


def _load():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    device, dtype = _device_and_dtype()
    _tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    try:
        base = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, dtype=dtype, device_map=device)
    except TypeError:
        base = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, torch_dtype=dtype, device_map=device)
    try:
        _model = PeftModel.from_pretrained(base, ADAPTER_REPO,
                                           token=HF_TOKEN).eval()
    except Exception as error:  # noqa: BLE001
        _model = None
        raise gr.Error(
            f"The adapter at {ADAPTER_REPO} could not be loaded. "
            f"{type(error).__name__}: {error}") from error
    return _model, _tokenizer


@spaces.GPU(duration=120)
def _answer(question: str, system: str, max_new_tokens: int) -> str:
    # The GPU worker's exceptions do not reach the Space log: a failure here
    # surfaces to the caller as `event: error, data: null` and nothing else.
    # Returning the traceback as the answer is ugly and is the only way to see
    # it from outside, so it stays until the Space is known good.
    try:
        return _generate(question, system, max_new_tokens)
    except Exception as error:  # noqa: BLE001
        import traceback
        return ("DIAGNOSTIC, not an answer:\n"
                + "".join(traceback.format_exception(error))[-1500:])


def _generate(question: str, system: str, max_new_tokens: int) -> str:
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


@spaces.GPU(duration=30)
def _gpu_smoke() -> str:  # noqa: D401
    """Does ZeroGPU hand this Space a GPU at all?

    If the model-serving endpoints fail while this one does too, the fault is
    the allocation rather than anything in the model path.
    """
    import torch as _t
    return (f"cuda available={_t.cuda.is_available()} "
            f"device_count={_t.cuda.device_count()} "
            f"name={_t.cuda.get_device_name(0) if _t.cuda.is_available() else 'none'}")


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

    with gr.Tab("Diagnostics"):
        gr.Markdown("Checks whether ZeroGPU grants this Space a GPU at all.")
        out_d = gr.Textbox(label="GPU")
        gr.Button("Check GPU").click(_gpu_smoke, None, out_d)

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

# --------------------------------------------------------------------------- #
# OpenAI-compatible route
#
# BINMAN's web app speaks one protocol for the language model: POST
# <BINMAN_LM_URL>/v1/chat/completions with the usual messages array. The Space
# speaks Gradio, which is a different thing entirely, so the natural-language
# box has been hidden on the live site with "the language model is not enabled
# for this deployment" even though the model has been up and serving this whole
# time.
#
# The adapter belongs here rather than in the web app. The app's client is a
# standard one and should stay that way; the Space is the component with the
# unusual interface, so the Space carries the translation. It also means a
# future move to any OpenAI-compatible host needs no change on the app side at
# all, just a different URL.
# --------------------------------------------------------------------------- #

import threading
import time
import uuid

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


async def _chat_completions(body: dict) -> JSONResponse:
    """Translate one OpenAI chat request into one call to the trained model.

    Deliberately minimal: no streaming, no tools, no n>1. BINMAN asks a single
    question and reads a single string back, and anything else here would be
    surface area nothing calls.
    """
    messages = body.get("messages") or []
    system = next((m.get("content", "") for m in messages
                   if m.get("role") == "system"), TRAINED_SYSTEM)
    user = next((m.get("content", "") for m in reversed(messages)
                 if m.get("role") == "user"), "")
    if not str(user).strip():
        return JSONResponse(status_code=400,
                            content={"error": {"message": "no user message"}})

    # Clamped: the GPU allocation is time-boxed, and an unbounded max_tokens
    # from a caller would spend it on a runaway generation.
    try:
        budget = int(body.get("max_tokens") or 320)
    except (TypeError, ValueError):
        budget = 320
    budget = max(16, min(budget, 512))

    try:
        text = _answer(str(user), str(system), budget)
    except Exception as error:  # noqa: BLE001
        return JSONResponse(status_code=503, content={
            "error": {"message": f"{type(error).__name__}: {error}"[:300]}})

    return JSONResponse(content={
        "id": "chatcmpl-" + uuid.uuid4().hex[:24],
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "binman-lm",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    })


def _install_openai_routes(app) -> None:
    """Add the machine routes to Gradio's own FastAPI app.

    Not `gr.mount_gradio_app` into a FastAPI app of our own, which was tried
    and failed: Spaces waits for Gradio's `launch()` to report the app ready,
    and a bare `uvicorn.run` never does, so the container started cleanly and
    was killed one second later. `launch(prevent_thread_lock=True)` performs
    that handshake and hands back the running app, which is what gets the
    routes.

    The route goes at the front of the router. Only the POST is served: a
    companion GET /v1/models was tried and returned the Gradio page, because
    Gradio serves the single-page app for GET on any path and does so ahead of
    anything added here. BINMAN never calls it, so it is gone rather than
    shipped broken.
    """
    app.router.routes.insert(0, APIRoute(
        "/v1/chat/completions", _chat_completions, methods=["POST"]))


# Spaces runs this file as __main__, so launch() is called either way. It is
# unguarded because the Space is the only place this app runs.
_prefetch()
demo.launch(prevent_thread_lock=True)
_install_openai_routes(demo.app)
# launch() no longer blocks, so the process has to be held open itself.
threading.Event().wait()
