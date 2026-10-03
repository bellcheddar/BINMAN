"""Train BINMAN-LM (spec 3.7).

Stage 1: LoRA supervised fine-tune on positives only, all tasks interleaved.
Stage 2: preference tuning on the corruption pairs, starting from the stage 1
         adapter.

**On the preference trainer.** Spec 3.7 says to use whichever preference trainer
the installed mlx-lm provides, then fall back to the mlx-examples DPO loop, then
ship stage 1 alone. mlx-lm 0.32.0 provides none: `mlx_lm.tuner.losses` exposes
only KL and JS divergences and its dataset loader has no notion of a chosen or
rejected completion. So the DPO loop here is the second rung of that ladder,
implemented directly against mlx-lm's LoRA machinery.

The reference log-probabilities are computed **once** from the frozen stage 1
model and cached, rather than keeping a second 3B model resident for the whole
run. DPO only needs the reference model's scores, not its gradients, so this is
exact rather than an approximation, and it halves peak memory.
"""

from __future__ import annotations

import argparse
import json
import os
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, Manifest, load_config, log_event, utcnow  # noqa: E402

CORPUS = ROOT / "lm" / "corpus"
MODELS = ROOT / "models" / "binman-lm"
ADAPTERS = MODELS / "adapters"
STAGE2_ADAPTERS = MODELS / "adapters-dpo"
FUSED = MODELS / "fused"
TRAIN_DATA = MODELS / "data"
TRAINING_JSON = MODELS / "training.json"
STAGE = "lm_train"

BASE_MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"

# Training runs are pushed to Weights & Biases. mlx-lm reports stage 1 natively
# through --report-to; the stage 2 DPO loop is this project's own code, so it
# logs to the same run explicitly. Credentials come from ~/.netrc or
# WANDB_API_KEY; when neither is present the run falls back to offline mode and
# training is unaffected.
WANDB_PROJECT = os.environ.get("BINMAN_WANDB_PROJECT", "binman-lm")

# Spec 3.7 hyperparameters.
LORA_RANK = 16
LORA_LAYERS = 16
LEARNING_RATE = 1e-5
MIN_ITERS = 600
MAX_ITERS = 1200
DPO_BETA = 0.1


# --------------------------------------------------------------------------- #
# data preparation
# --------------------------------------------------------------------------- #

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def prepare_sft_data() -> dict:
    """Interleave all available task corpora into mlx-lm's chat format."""
    TRAIN_DATA.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    for split, sources in (
        ("train", ("task_a_train.jsonl", "task_c_train.jsonl")),
        ("valid", ("task_a_valid.jsonl", "task_c_valid.jsonl")),
        ("test", ("task_a_test.jsonl", "task_c_test.jsonl")),
    ):
        rows: list[dict] = []
        for name in sources:
            for row in _read_jsonl(CORPUS / name):
                # mlx-lm wants only `messages`; the extra keys confuse its loader.
                rows.append({"messages": row["messages"]})
        # Interleave rather than concatenate, so a batch mixes tasks and the
        # model never sees a long run of one task tag.
        rows.sort(key=lambda r: hash(r["messages"][1]["content"]) % 1_000_003)
        path = TRAIN_DATA / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        counts[split] = len(rows)
    return counts


# --------------------------------------------------------------------------- #
# stage 1: LoRA SFT
# --------------------------------------------------------------------------- #

def wandb_available() -> bool:
    """Is Weights & Biases importable and credentialed?

    An uncredentialed run would block on an interactive login prompt, which
    would hang an unattended build, so this checks for a key before enabling it.
    """
    try:
        import wandb  # noqa: F401
    except ImportError:
        return False
    if os.environ.get("WANDB_API_KEY"):
        return True
    netrc = Path.home() / ".netrc"
    try:
        return netrc.exists() and "api.wandb.ai" in netrc.read_text(errors="replace")
    except OSError:
        return False


def stage_one(iters: int, batch_size: int, model: str = BASE_MODEL) -> dict:
    counts = prepare_sft_data()
    ADAPTERS.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--model", model,
        "--train",
        "--data", str(TRAIN_DATA),
        "--fine-tune-type", "lora",
        "--num-layers", str(LORA_LAYERS),
        "--batch-size", str(batch_size),
        "--iters", str(iters),
        "--learning-rate", str(LEARNING_RATE),
        "--adapter-path", str(ADAPTERS),
        "--steps-per-eval", "100",
        "--val-batches", "20",
        "--max-seq-length", "1024",
        "--mask-prompt",
        "--steps-per-report", "10",
    ]
    if wandb_available():
        command += ["--report-to", "wandb", "--project-name", WANDB_PROJECT]
    log_event("3.7", f"Stage 1 LoRA SFT starting: {counts['train']:,} train / "
                     f"{counts['valid']:,} valid examples, rank {LORA_RANK}, "
                     f"{LORA_LAYERS} layers, lr {LEARNING_RATE}, batch {batch_size}, "
                     f"{iters} iterations.")

    started = time.monotonic()
    log_path = INTERIM / "lm_stage1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT,
                                text=True)
    elapsed = time.monotonic() - started

    text = log_path.read_text(errors="replace")
    losses = _parse_losses(text)
    report = {
        "iterations_requested": iters,
        "batch_size": batch_size,
        "rank": LORA_RANK,
        "layers": LORA_LAYERS,
        "learning_rate": LEARNING_RATE,
        "wall_clock_seconds": round(elapsed, 1),
        "train_examples": counts["train"],
        "valid_examples": counts["valid"],
        "exit_code": result.returncode,
        "validation_losses": losses["validation"],
        "final_train_loss": losses["final_train"],
        "best_validation_loss": losses["best_validation"],
        "early_stopping_point": losses["best_validation_iter"],
        "log": str(log_path.relative_to(ROOT)),
        "wandb_project": WANDB_PROJECT if wandb_available() else "",
        "reported_to_wandb": wandb_available(),
    }
    if result.returncode != 0:
        log_event("3.7", f"Stage 1 FAILED with exit {result.returncode}. "
                         f"See {log_path.relative_to(ROOT)}.")
    else:
        log_event("3.7", f"Stage 1 complete in {elapsed / 60:.1f} min. "
                         f"Best validation loss {losses['best_validation']} at "
                         f"iteration {losses['best_validation_iter']}.")
    return report


def _parse_losses(text: str) -> dict:
    """Pull the loss trace out of the trainer's stdout."""
    import re

    # mlx-lm 0.32 prints an ANSI-coloured table: "   100    val 0.023    7.82s"
    # for validation and "   110    0.008 /\ ..." for training steps.
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    val_line = re.compile(r"^\s*(\d+)\s+val\s+([0-9.]+)")
    train_line = re.compile(r"^\s*(\d+)\s+([0-9.]+)\s")

    validation: list[dict] = []
    final_train = None
    for raw in text.splitlines():
        line = ansi.sub("", raw)
        match = val_line.match(line)
        if match:
            validation.append({"iter": int(match.group(1)),
                               "loss": float(match.group(2))})
            continue
        match = train_line.match(line)
        if match and "val" not in line:
            try:
                final_train = float(match.group(2))
            except ValueError:
                pass
    best = min(validation, key=lambda r: r["loss"]) if validation else None
    return {
        "validation": validation,
        "final_train": final_train,
        "best_validation": best["loss"] if best else None,
        "best_validation_iter": best["iter"] if best else None,
    }


# --------------------------------------------------------------------------- #
# stage 2: DPO on the corruption pairs
# --------------------------------------------------------------------------- #

def _sequence_logprob(model, tokenizer, prompt: str, completion: str):
    """Mean log-probability of `completion` given `prompt`, as an MLX scalar."""
    import mlx.core as mx

    prefix_ids = tokenizer.encode(prompt)
    full_ids = tokenizer.encode(prompt + completion)
    if len(full_ids) <= len(prefix_ids):
        return None
    tokens = mx.array([full_ids])
    logits = model(tokens[:, :-1]).astype(mx.float32)
    targets = tokens[:, 1:]
    logprobs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    picked = mx.take_along_axis(logprobs, targets[..., None], axis=-1)[..., 0]
    start = len(prefix_ids) - 1
    return picked[0, start:].mean()


def stage_two(batch_size: int, epochs: int = 1, limit: int | None = None) -> dict:
    """DPO against the stage 1 adapter (spec 3.7, fallback rung 2).

    Returns a report. Where anything in the loop fails the caller ships stage 1
    alone, which is the third rung of the ladder.
    """
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx.utils import tree_flatten
    from mlx_lm import load

    pairs = _read_jsonl(CORPUS / "task_a_preference.jsonl") + \
        _read_jsonl(CORPUS / "task_c_preference.jsonl")
    if not pairs:
        return {"ran": False, "reason": "no preference pairs found"}
    if limit is not None:
        pairs = pairs[:limit]

    log_event("3.7", f"Stage 2 DPO starting on {len(pairs):,} preference pairs, "
                     f"beta {DPO_BETA}. mlx-lm 0.32.0 provides no preference "
                     f"trainer, so this is the documented mlx-examples DPO "
                     f"fallback implemented against mlx-lm's LoRA machinery.")

    model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTERS))

    def rendered(pair: dict) -> str:
        messages = [{"role": "system", "content": pair.get("system", "")},
                    {"role": "user", "content": pair["prompt"]}]
        return tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False)

    # Reference log-probabilities from the frozen stage 1 model, computed once.
    # DPO needs only the reference scores, so caching them is exact and avoids
    # keeping a second model resident.
    started = time.monotonic()
    reference: list[dict] = []
    for index, pair in enumerate(pairs, start=1):
        prompt = rendered(pair)
        chosen = _sequence_logprob(model, tokenizer, prompt, pair["chosen"])
        rejected = _sequence_logprob(model, tokenizer, prompt, pair["rejected"])
        if chosen is None or rejected is None:
            continue
        mx.eval(chosen, rejected)
        reference.append({
            "prompt": prompt,
            "chosen": pair["chosen"], "rejected": pair["rejected"],
            "mode": pair.get("mode", "unknown"),
            "ref_chosen": float(chosen.item()), "ref_rejected": float(rejected.item()),
        })
        if index % 200 == 0:
            log_event("3.7", f"Stage 2: reference log-probabilities cached for "
                             f"{index:,}/{len(pairs):,} pairs.")
    log_event("3.7", f"Stage 2: reference cache built for {len(reference):,} pairs "
                     f"in {(time.monotonic() - started) / 60:.1f} min.")

    # Only the LoRA parameters train; the base weights stay frozen.
    model.freeze()
    for module in model.modules():
        if hasattr(module, "lora_a") or module.__class__.__name__.startswith("LoRA"):
            module.unfreeze(keys=["lora_a", "lora_b"], recurse=False)
    trainable = [p for _, p in tree_flatten(model.trainable_parameters())]
    if not trainable:
        return {"ran": False,
                "reason": "no trainable LoRA parameters found after freezing"}

    optimizer = optim.Adam(learning_rate=LEARNING_RATE)

    def loss_fn(batch: list[dict]):
        total = mx.zeros(())
        for item in batch:
            policy_chosen = _sequence_logprob(
                model, tokenizer, item["prompt"], item["chosen"])
            policy_rejected = _sequence_logprob(
                model, tokenizer, item["prompt"], item["rejected"])
            if policy_chosen is None or policy_rejected is None:
                continue
            # The DPO objective: prefer chosen over rejected relative to the
            # reference model's own preference.
            margin = DPO_BETA * (
                (policy_chosen - item["ref_chosen"])
                - (policy_rejected - item["ref_rejected"])
            )
            # -log(sigmoid(margin)), written as logaddexp for numerical
            # stability. MLX exposes no log_sigmoid, and log(sigmoid(x))
            # underflows for strongly negative x.
            total = total + mx.logaddexp(mx.zeros_like(margin), -margin)
        return total / max(1, len(batch))

    value_and_grad = nn.value_and_grad(model, loss_fn)
    history: list[dict] = []
    step = 0
    started = time.monotonic()

    # The DPO loop is this project's own code, so it reports to W&B itself.
    run = None
    if wandb_available():
        try:
            import wandb

            run = wandb.init(
                project=WANDB_PROJECT, job_type="dpo",
                name=f"binman-lm-dpo-{time.strftime('%Y%m%d-%H%M%S')}",
                config={"beta": DPO_BETA, "pairs": len(reference),
                        "batch_size": batch_size, "epochs": epochs,
                        "learning_rate": LEARNING_RATE, "base_model": BASE_MODEL,
                        "stage": "2-preference"},
                reinit=True,
            )
        except Exception as exc:  # noqa: BLE001
            log_event("3.7", f"W&B unavailable for stage 2, training anyway: "
                             f"{type(exc).__name__}")
            run = None

    for epoch in range(epochs):
        for offset in range(0, len(reference), batch_size):
            batch = reference[offset:offset + batch_size]
            if not batch:
                continue
            try:
                loss, grads = value_and_grad(batch)
                optimizer.update(model, grads)
                mx.eval(model.parameters(), optimizer.state, loss)
            except Exception as exc:  # noqa: BLE001
                log_event("3.7", f"Stage 2 step {step} failed: "
                                 f"{type(exc).__name__}: {exc}"[:180])
                return {
                    "ran": False, "steps_completed": step,
                    "reason": f"{type(exc).__name__}: {exc}"[:200],
                    "history": history,
                }
            step += 1
            value = float(loss.item())
            history.append({"step": step, "loss": value})
            if run is not None:
                try:
                    run.log({"dpo/loss": value, "dpo/step": step})
                except Exception:  # noqa: BLE001
                    run = None
            if step % 20 == 0:
                recent = sum(h["loss"] for h in history[-20:]) / 20
                log_event("3.7", f"Stage 2: step {step}, mean loss over the last 20 "
                                 f"steps {recent:.4f}.")

    STAGE2_ADAPTERS.mkdir(parents=True, exist_ok=True)
    # Carry the stage 1 config forward so the adapters stay loadable.
    for name in ("adapter_config.json",):
        source = ADAPTERS / name
        if source.exists():
            shutil.copy2(source, STAGE2_ADAPTERS / name)
    weights = dict(tree_flatten(model.trainable_parameters()))
    mx.save_safetensors(str(STAGE2_ADAPTERS / "adapters.safetensors"), weights)

    if run is not None:
        try:
            run.finish()
        except Exception:  # noqa: BLE001
            pass

    elapsed = time.monotonic() - started
    log_event("3.7", f"Stage 2 DPO complete: {step} steps in {elapsed / 60:.1f} min, "
                     f"adapters saved to {STAGE2_ADAPTERS.relative_to(ROOT)}.")
    return {
        "ran": True, "steps": step, "beta": DPO_BETA, "epochs": epochs,
        "pairs": len(reference),
        "wall_clock_seconds": round(elapsed, 1),
        "first_loss": history[0]["loss"] if history else None,
        "final_loss": history[-1]["loss"] if history else None,
        "adapters": str(STAGE2_ADAPTERS.relative_to(ROOT)),
        "wandb_project": WANDB_PROJECT if wandb_available() else "",
        "reported_to_wandb": run is not None,
        "implementation": (
            "mlx-lm 0.32.0 ships no preference trainer, so this is the spec 3.7 "
            "mlx-examples DPO fallback, implemented against mlx-lm's LoRA "
            "machinery with cached reference log-probabilities."
        ),
    }


# --------------------------------------------------------------------------- #
# fuse
# --------------------------------------------------------------------------- #

def fuse(adapter_path: Path) -> dict:
    FUSED.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "mlx_lm", "fuse",
        "--model", BASE_MODEL,
        "--adapter-path", str(adapter_path),
        "--save-path", str(FUSED),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    ok = result.returncode == 0
    log_event("3.7", f"Fuse {'succeeded' if ok else 'FAILED'}: {FUSED.relative_to(ROOT)}"
                     + ("" if ok else f" ({result.stderr.strip()[:160]})"))
    return {"fused": ok, "path": str(FUSED.relative_to(ROOT)),
            "adapter": str(adapter_path.relative_to(ROOT)),
            "error": "" if ok else result.stderr.strip()[:300]}


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def run(iters: int | None = None, skip_stage_two: bool = False,
        dpo_limit: int | None = 600) -> dict:
    config = load_config()
    batch_size = int(config.u("model.mlx_batch_size"))
    hardware = config.hardware

    iters = iters or MAX_ITERS
    iters = max(MIN_ITERS, min(MAX_ITERS, iters))

    report = {
        "generated_at": utcnow(),
        "identity": {
            "base_model": BASE_MODEL,
            "quantisation": "4-bit",
            "adapter_rank": LORA_RANK,
            "adapter_layers": LORA_LAYERS,
            "fine_tune_type": "lora",
            "fused": False,
            "build_date": utcnow()[:10],
        },
        "hardware": {
            "chip": hardware.get("host", {}).get("chip"),
            "gpu_cores": hardware.get("host", {}).get("gpu_cores"),
            "memory_gb": hardware.get("memory", {}).get("total_gb"),
            "mlx_version": hardware.get("mlx", {}).get("version"),
        },
        "tasks": [
            {"tag": "<task>query</task>",
             "description": "natural language to a BINMAN query object"},
            {"tag": "<task>triage</task>",
             "description": "evidence-class triage",
             "status": "NOT TRAINED: three of five classes have no published label "
                       "source in this build (see lm/corpus/corpus_report.json)"},
            {"tag": "<task>abstain</task>",
             "description": "structured abstention naming exactly what is missing"},
        ],
    }

    report["stage_1"] = stage_one(iters, batch_size)
    if report["stage_1"]["exit_code"] != 0:
        report["stage_2"] = {"ran": False, "reason": "stage 1 failed"}
        report["fuse"] = {"fused": False, "reason": "stage 1 failed"}
        TRAINING_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")
        return report

    if skip_stage_two:
        report["stage_2"] = {"ran": False, "reason": "skipped by request"}
    else:
        try:
            report["stage_2"] = stage_two(batch_size=1, limit=dpo_limit)
        except Exception as exc:  # noqa: BLE001
            # Third rung of the ladder: ship stage 1 alone and log it.
            report["stage_2"] = {
                "ran": False,
                "reason": f"{type(exc).__name__}: {exc}"[:240],
                "note": ("Spec 3.7 fallback: both the mlx-lm preference trainer "
                         "and the DPO loop were unavailable or failed, so stage 1 "
                         "ships alone."),
            }
            log_event("3.7", f"Stage 2 unavailable, shipping stage 1 alone: "
                             f"{type(exc).__name__}")

    adapter = STAGE2_ADAPTERS if report["stage_2"].get("ran") else ADAPTERS
    report["fuse"] = fuse(adapter)
    report["identity"]["fused"] = bool(report["fuse"]["fused"])
    report["identity"]["shipped_adapter"] = str(adapter.relative_to(ROOT))

    TRAINING_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")
    Manifest(STAGE).record(
        "run", status="ok",
        stage_1_exit=report["stage_1"]["exit_code"],
        stage_2_ran=bool(report["stage_2"].get("ran")),
        fused=bool(report["fuse"]["fused"]),
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Train BINMAN-LM")
    parser.add_argument("--iters", type=int, default=None)
    parser.add_argument("--skip-stage-two", action="store_true")
    parser.add_argument("--dpo-limit", type=int, default=600)
    args = parser.parse_args()
    report = run(iters=args.iters, skip_stage_two=args.skip_stage_two,
                 dpo_limit=args.dpo_limit)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
