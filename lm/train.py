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
import re
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


# Run naming follows the convention used across Marc's other W&B projects:
#
#     {project}-{model}-{ver}-{parameters}-round{NN}
#
#     faffabout-llama-3.1-8b-8bit-round01
#     chatmcd-qwen3-8b-round02
#     binman-qwen-2.5-3b-4bit-round01
#
# The round number always ticks up: it is read from the runs already in the
# project rather than from a local counter, so it stays correct across machines
# and after a clone.
WANDB_RUN_ENTITY = os.environ.get("BINMAN_WANDB_ENTITY", "")
MODEL_SLUG = "qwen-2.5-3b-4bit"
RUN_STEM = f"binman-{MODEL_SLUG}"

ROUND_PATTERN = re.compile(r"-round(\d+)$")


def next_round(stem: str = RUN_STEM) -> int:
    """The next round number for this project, read from W&B.

    Falls back to a local counter file when W&B cannot be reached, so an offline
    run still increments rather than colliding on round01.
    """
    highest = 0
    try:
        import wandb

        api = wandb.Api()
        entity = WANDB_RUN_ENTITY or api.default_entity
        for run in api.runs(f"{entity}/{WANDB_PROJECT}", per_page=100):
            match = ROUND_PATTERN.search(run.name or "")
            if match:
                highest = max(highest, int(match.group(1)))
    except Exception:  # noqa: BLE001 - offline or unauthenticated is not fatal
        counter = ROOT / "models" / "binman-lm" / ".round"
        try:
            highest = int(counter.read_text().strip())
        except (OSError, ValueError):
            highest = 0

    nxt = highest + 1
    counter = ROOT / "models" / "binman-lm" / ".round"
    try:
        counter.parent.mkdir(parents=True, exist_ok=True)
        counter.write_text(str(nxt))
    except OSError:
        pass
    return nxt


def run_name(round_number: int | None = None, stem: str = RUN_STEM) -> str:
    """`binman-qwen-2.5-3b-4bit-roundNN`, matching the other projects."""
    number = round_number if round_number is not None else next_round(stem)
    return f"{stem}-round{number:02d}"


def wandb_env(name: str, group: str, notes: str, tags: list[str]) -> dict:
    """Environment that names and groups a run mlx-lm starts on our behalf."""
    return {
        "WANDB_NAME": name,
        "WANDB_RUN_GROUP": group,
        "WANDB_JOB_TYPE": "sft",
        "WANDB_NOTES": notes,
        "WANDB_TAGS": ",".join(tags),
        "WANDB_PROJECT": WANDB_PROJECT,
    }

# Spec 3.7 hyperparameters.
# LORA_RANK reaches mlx only through a YAML config: `mlx_lm lora` has no
# --lora-rank flag and silently defaults to rank 8. Rounds 01 to 06 therefore
# trained at rank 8 while this constant said 16 and that 16 went into W&B and
# training.json. See DECISIONS.md D-033. Changing this number now changes the
# training rather than only the label.
LORA_RANK = 8
LORA_SCALE = 20.0
LORA_DROPOUT = 0.0
LORA_LAYERS = 16
LEARNING_RATE = 1e-5
MIN_ITERS = 600
# Raised from the spec's 1200. With Task B in the mix the corpus is ~28,000
# examples, and 1200 iterations at batch 4 shows the model 4,800 samples, which
# is under a quarter of one epoch. Capping there would have left three quarters
# of the curated labels unseen. See DECISIONS.md D-024.
MAX_ITERS = 20000

# Task-level mix. Marc's "treat them all as unique data" applies to the CLASSES
# inside Task B, and it is honoured: every Task B example is kept. The task axis
# is a different question. Left alone, Task B's size made the mix 74% triage,
# 22% query and 4% abstain, and abstain is the task that keeps the model honest
# (spec 3.5 says to over-weight it, not starve it). Task A and Task C are
# therefore oversampled by repetition, which discards nothing.
TASK_OVERSAMPLE = {"task_a": 2, "task_c": 4}
DPO_BETA = 0.1
# Preference tuning needs a much gentler step than the SFT stage: the first run
# reused the SFT learning rate for 600 updates and collapsed the policy.
DPO_LEARNING_RATE = 5e-7
DPO_MAX_STEPS = 150


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

    # All three tasks interleaved (spec 3.7). Task B joined once its labels
    # became available: see DECISIONS.md D-022.
    for split, sources in (
        ("train", ("task_a_train.jsonl", "task_b_train.jsonl", "task_c_train.jsonl")),
        ("valid", ("task_a_valid.jsonl", "task_b_valid.jsonl", "task_c_valid.jsonl")),
        ("test", ("task_a_test.jsonl", "task_b_test.jsonl", "task_c_test.jsonl")),
    ):
        rows: list[dict] = []
        for name in sources:
            stem = name.rsplit("_", 1)[0]
            # Oversample only the training split: repeating validation or test
            # rows would flatter the metrics.
            repeat = TASK_OVERSAMPLE.get(stem, 1) if split == "train" else 1
            for row in _read_jsonl(CORPUS / name):
                # mlx-lm wants only `messages`; the extra keys confuse its loader.
                for _ in range(repeat):
                    rows.append({"messages": row["messages"]})
        # Interleave rather than concatenate, so a batch mixes tasks and the
        # model never sees a long run of one task tag.
        rows.sort(key=lambda r: hash(r["messages"][1]["content"]) % 1_000_003)
        path = TRAIN_DATA / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        counts[split] = len(rows)

    # Report the task mix so a skew is visible in the log rather than inferred.
    mix: dict[str, int] = {}
    for row in _read_jsonl(TRAIN_DATA / "train.jsonl"):
        tag = row["messages"][0]["content"].split("</task>")[0].replace("<task>", "")
        mix[tag] = mix.get(tag, 0) + 1
    counts["task_mix"] = mix
    log_event("3.7", f"SFT corpus assembled: {counts['train']:,} train "
                     f"(oversampling {TASK_OVERSAMPLE}), task mix "
                     + ", ".join(f"{k} {v / max(1, counts['train']):.0%}"
                                 for k, v in sorted(mix.items())))
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


def stage_one(iters: int, batch_size: int, model: str = BASE_MODEL,
              round_number: int | None = None) -> dict:
    counts = prepare_sft_data()

    # mlx-lm names its W&B run `os.path.basename(log_dir)`, which is the adapter
    # path, and that explicit argument overrides WANDB_NAME. So training writes
    # into a directory named after the run, and the result is copied to the
    # stable `adapters/` path afterwards. The run is then named correctly while
    # it is live, rather than being renamed after the fact.
    name = run_name(round_number) if round_number else "adapters"
    work_dir = (MODELS / "runs" / name) if round_number else ADAPTERS
    work_dir.mkdir(parents=True, exist_ok=True)
    ADAPTERS.mkdir(parents=True, exist_ok=True)

    # The only route to lora_parameters is a YAML config file, so one is written
    # per run and kept beside the adapter as part of the run's provenance.
    config_path = work_dir / "lora_config.yaml"
    config_path.write_text(
        "lora_parameters:\n"
        f"  rank: {LORA_RANK}\n"
        f"  scale: {LORA_SCALE}\n"
        f"  dropout: {LORA_DROPOUT}\n"
    )

    command = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--model", model,
        "--train",
        "--data", str(TRAIN_DATA),
        "--fine-tune-type", "lora",
        "--config", str(config_path),
        "--num-layers", str(LORA_LAYERS),
        "--batch-size", str(batch_size),
        "--iters", str(iters),
        "--learning-rate", str(LEARNING_RATE),
        "--adapter-path", str(work_dir),
        "--steps-per-eval", "100",
        "--val-batches", "20",
        "--max-seq-length", "1024",
        "--mask-prompt",
        "--steps-per-report", "10",
    ]
    environment = dict(os.environ)
    group = f"{RUN_STEM}-round{round_number:02d}" if round_number else RUN_STEM
    if wandb_available():
        command += ["--report-to", "wandb", "--project-name", WANDB_PROJECT]
        environment.update(wandb_env(
            name, group,
            notes=(f"Stage 1 LoRA SFT. Task A (query) and Task C (abstain) "
                   f"interleaved, {counts['train']} train / {counts['valid']} valid. "
                   f"rank {LORA_RANK}, {LORA_LAYERS} layers, lr {LEARNING_RATE}, "
                   f"mask-prompt, max-seq 1024."),
            tags=["stage1-sft", "lora", f"rank{LORA_RANK}", "task-a", "task-c",
                  "qwen2.5-3b-4bit"],
        ))
    log_event("3.7", f"Stage 1 LoRA SFT starting: {counts['train']:,} train / "
                     f"{counts['valid']:,} valid examples, rank {LORA_RANK}, "
                     f"{LORA_LAYERS} layers, lr {LEARNING_RATE}, batch {batch_size}, "
                     f"{iters} iterations.")

    started = time.monotonic()
    log_path = INTERIM / "lm_stage1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT,
                                text=True, env=environment)
    elapsed = time.monotonic() - started

    text = log_path.read_text(errors="replace")
    losses = _parse_losses(text)

    # Copy the trained adapter to the stable path everything else serves from.
    if result.returncode == 0 and work_dir != ADAPTERS:
        for item in work_dir.iterdir():
            if item.is_file() and item.suffix in {".safetensors", ".json"}:
                shutil.copy2(item, ADAPTERS / item.name)
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
        "wandb_run_name": name,
        "wandb_group": group,
        "reported_to_wandb": bool(name),
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


def stage_two(batch_size: int, epochs: int = 1, limit: int | None = None,
              round_number: int | None = None, group: str = "") -> dict:
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

    optimizer = optim.Adam(learning_rate=DPO_LEARNING_RATE)

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
                name=run_name(round_number),
                group=group or RUN_STEM,
                tags=["stage2-dpo", "preference", f"beta{DPO_BETA}",
                      MODEL_SLUG],
                notes=("Stage 2 preference tuning on the corruption pairs. "
                       "mlx-lm 0.32 ships no preference trainer, so this is the "
                       "spec 3.7 DPO fallback with cached reference logprobs."),
                config={"beta": DPO_BETA, "pairs": len(reference),
                        "batch_size": batch_size, "epochs": epochs,
                        # The DPO stage has its own, much gentler rate; logging
                        # the SFT rate here would misreport what actually ran.
                        "learning_rate": DPO_LEARNING_RATE,
                        "max_steps": DPO_MAX_STEPS,
                        "base_model": BASE_MODEL, "stage": "2-preference"},
                reinit=True,
            )
        except Exception as exc:  # noqa: BLE001
            log_event("3.7", f"W&B unavailable for stage 2, training anyway: "
                             f"{type(exc).__name__}")
            run = None

    for epoch in range(epochs):
        for offset in range(0, len(reference), batch_size):
            if step >= DPO_MAX_STEPS:
                break
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
        "wandb_run_name": run.name if run is not None else "",
        "reported_to_wandb": run is not None,
        "implementation": (
            "mlx-lm 0.32.0 ships no preference trainer, so this is the spec 3.7 "
            "mlx-examples DPO fallback, implemented against mlx-lm's LoRA "
            "machinery with cached reference log-probabilities."
        ),
    }


# --------------------------------------------------------------------------- #
# the generation guard
# --------------------------------------------------------------------------- #

def generation_healthy(adapter_path: Path, samples: int = 6) -> dict:
    """Does this adapter still produce parseable query objects?

    Stage 2 can reach a near-zero DPO loss by collapsing the policy rather than
    by learning the preference: a degenerate model trivially scores one string
    above another, so the win rates look perfect while generation is ruined. The
    first DPO run did exactly that and emitted "ccdccdccdccd..." forever.

    Nothing downstream noticed, because the preference metric cannot see it. So
    the adapter is checked against the parser before it is allowed to ship.
    """
    import sys as _sys

    _sys.path.insert(0, str(ROOT))
    from app.queries import QueryError, parse as parse_query
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    from lm.evaluate import TRAINED_SYSTEM, extract_json

    # Probes come from the held-out test corpus, not from hand-written
    # questions: freehand phrasings drift out of the training distribution and
    # fail for ordinary reasons (asking for "relative SASA" when the field is
    # `nz_rel_sasa`), which would make the guard reject healthy adapters. The
    # guard exists to catch collapse, so it must measure the same distribution
    # the real metric does.
    probes: list[str] = []
    test_file = CORPUS / "task_a_test.jsonl"
    if test_file.exists():
        with test_file.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                probes.append(row["messages"][1]["content"])
                if len(probes) >= samples:
                    break
    if not probes:
        probes = ["ligases with a pocket score above 0.5"]

    # The path may be an adapter directory or a fused model directory. A fused
    # model is a complete model and must be loaded as one, not as an adapter.
    is_adapter = (adapter_path / "adapter_config.json").exists()
    try:
        if is_adapter:
            model, tokenizer = load(BASE_MODEL, adapter_path=str(adapter_path))
        else:
            model, tokenizer = load(str(adapter_path))
    except Exception as exc:  # noqa: BLE001
        return {"healthy": False, "parsed": 0, "n": len(probes),
                "kind": "adapter" if is_adapter else "model",
                "reason": f"would not load: {type(exc).__name__}: {exc}"[:160]}

    parsed = 0
    examples = []
    for question in probes:
        messages = [{"role": "system", "content": TRAINED_SYSTEM},
                    {"role": "user", "content": question}]
        prompt = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False)
        try:
            raw = generate(model, tokenizer, prompt=prompt, max_tokens=200,
                           sampler=make_sampler(temp=0.0), verbose=False)
            parse_query(extract_json(raw))
            parsed += 1
        except (QueryError, Exception):  # noqa: B014
            examples.append(raw[:90] if "raw" in dir() else "")
    rate = parsed / max(1, len(probes))
    # A collapsed model parses essentially nothing; a merely imperfect one parses
    # most. The threshold separates those two states, it is not a quality bar:
    # quality is measured properly by lm/evaluate.py against the real database.
    return {
        "healthy": rate >= 0.8, "parsed": parsed, "n": len(probes),
        "parse_rate": round(rate, 3),
        "reason": "" if rate >= 0.8 else
                  f"only {parsed}/{len(probes)} probes parsed; sample output "
                  f"{examples[0]!r}" if examples else "",
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
        dpo_limit: int | None = 600, batch_size: int | None = None) -> dict:
    config = load_config()
    batch_size = batch_size or int(config.u("model.mlx_batch_size"))
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

    # One round number per stage, both ticking up, grouped under the stage 1
    # round so a two-stage training shows as one experiment.
    sft_round = next_round() if wandb_available() else None
    group = f"{RUN_STEM}-round{sft_round:02d}" if sft_round else RUN_STEM
    report["round"] = sft_round
    report["stage_1"] = stage_one(iters, batch_size, round_number=sft_round)
    if report["stage_1"]["exit_code"] != 0:
        report["stage_2"] = {"ran": False, "reason": "stage 1 failed"}
        report["fuse"] = {"fused": False, "reason": "stage 1 failed"}
        TRAINING_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")
        return report

    if skip_stage_two:
        report["stage_2"] = {"ran": False, "reason": "skipped by request"}
    else:
        try:
            dpo_round = next_round() if wandb_available() else None
            report["stage_2"] = stage_two(batch_size=1, limit=dpo_limit,
                                          round_number=dpo_round, group=group)
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

    # Spec 3.7's third rung: if stage 2 did not help, ship stage 1 alone and log
    # it. "Did not help" now includes "trained successfully but broke
    # generation", which the preference metric alone cannot detect.
    adapter = ADAPTERS
    if report["stage_2"].get("ran"):
        guard = generation_healthy(STAGE2_ADAPTERS)
        report["stage_2"]["generation_guard"] = guard
        if guard["healthy"]:
            adapter = STAGE2_ADAPTERS
            log_event("3.7", f"Stage 2 adapter passed the generation guard "
                             f"({guard['parsed']}/{guard['n']} probes parsed) and ships.")
        else:
            log_event("3.7", f"Stage 2 adapter REJECTED by the generation guard: "
                             f"{guard['reason'][:140]}. Shipping stage 1 alone "
                             f"(spec 3.7 fallback).")
            report["stage_2"]["shipped"] = False
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
    # Declared up front: the help strings below read these names, and Python
    # rejects a global statement that follows a use in the same scope.
    global LORA_LAYERS, LORA_RANK, BASE_MODEL, MODEL_SLUG, RUN_STEM

    parser = argparse.ArgumentParser(description="Train BINMAN-LM")
    parser.add_argument("--iters", type=int, default=None)
    parser.add_argument("--skip-stage-two", action="store_true")
    parser.add_argument("--dpo-limit", type=int, default=600)
    # The ablation knobs. Each overrides a module constant for this run only, so
    # an overnight sweep can vary one at a time without editing the file between
    # runs and losing track of which round used what.
    parser.add_argument("--layers", type=int, default=None,
                        help=f"LoRA layers, counted from the last (default {LORA_LAYERS})")
    parser.add_argument("--rank", type=int, default=None,
                        help=f"LoRA rank (default {LORA_RANK})")
    parser.add_argument("--base-model", default=None,
                        help=f"mlx base model (default {BASE_MODEL})")
    parser.add_argument("--batch-size", type=int, default=None)
    args = parser.parse_args()

    if args.layers is not None:
        LORA_LAYERS = args.layers
    if args.rank is not None:
        LORA_RANK = args.rank
    if args.base_model is not None:
        BASE_MODEL = args.base_model
        # The run name carries the model, so a 32B round cannot be mistaken for
        # a 3B one in W&B after the fact.
        MODEL_SLUG = (args.base_model.rsplit("/", 1)[-1]
                      .replace("Qwen2.5-", "qwen-2.5-").replace("-Instruct", "")
                      .lower())
        RUN_STEM = f"binman-{MODEL_SLUG}"

    report = run(iters=args.iters, skip_stage_two=args.skip_stage_two,
                 dpo_limit=args.dpo_limit, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
