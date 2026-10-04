"""Convert an MLX LoRA adapter to PEFT format for serving on CUDA.

BINMAN-LM is trained with mlx-lm against `mlx-community/Qwen2.5-3B-Instruct-4bit`
on Apple silicon. HuggingFace ZeroGPU is CUDA, where MLX does not run, so the
adapter has to be re-expressed in PEFT's layout and applied to a base the CUDA
side can load.

**The conversion is mechanical; the equivalence is not.** MLX stores
`lora_a` as [in_features, rank] and `lora_b` as [rank, out_features]; PEFT wants
`lora_A.weight` [rank, in_features] and `lora_B.weight` [out_features, rank], so
both are transposed. MLX carries a single `scale`, PEFT carries `lora_alpha` and
`r` and uses alpha/r, so alpha is scale * rank.

What cannot be fixed by renaming tensors: the adapter was trained to correct a
**4-bit quantised** base, and on CUDA it will be applied to a different one.
Nothing guarantees the correction transfers. `--verify` therefore runs the real
held-out test questions through the converted adapter and prints the same
numbers `lm/evaluate.py` reports, so the two can be compared rather than
assumed equal. A conversion that loads cleanly and answers badly is the failure
mode this guards against, and it is the same one that produced DECISIONS D-016.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import log_event  # noqa: E402

MODELS = ROOT / "models" / "binman-lm"
DEFAULT_ADAPTER = MODELS / "adapters"
DEFAULT_OUT = MODELS / "hf-adapter"

# The CUDA-side base. The MLX base is the 4-bit quantisation of this same model,
# so the architecture matches and only the numerics differ.
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
MLX_BASE = "mlx-community/Qwen2.5-3B-Instruct-4bit"

TARGET_SUFFIXES = (
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
)


def convert(adapter_dir: Path, out_dir: Path) -> dict:
    """Rewrite MLX LoRA tensors into a PEFT adapter directory."""
    import numpy as np
    from safetensors.numpy import save_file
    from safetensors import safe_open

    weights_path = adapter_dir / "adapters.safetensors"
    if not weights_path.exists():
        raise SystemExit(f"{weights_path} does not exist")

    config_path = adapter_dir / "adapter_config.json"
    mlx_config = json.loads(config_path.read_text()) if config_path.exists() else {}
    lora = mlx_config.get("lora_parameters", {})
    rank = int(lora.get("rank", 8))
    scale = float(lora.get("scale", 20.0))
    dropout = float(lora.get("dropout", 0.0))

    out: dict = {}
    targets: set[str] = set()
    with safe_open(str(weights_path), framework="np") as handle:
        for key in handle.keys():
            tensor = handle.get_tensor(key)
            if key.endswith(".lora_a"):
                stem, peft = key[: -len(".lora_a")], "lora_A"
            elif key.endswith(".lora_b"):
                stem, peft = key[: -len(".lora_b")], "lora_B"
            else:
                # Anything else is not a LoRA factor and has no PEFT equivalent.
                continue
            targets.add(stem.rsplit(".", 1)[-1])
            # PEFT expects the transpose of MLX's layout for both factors.
            out[f"base_model.model.{stem}.{peft}.weight"] = (
                np.ascontiguousarray(tensor.T).astype(np.float32)
            )

    if not out:
        raise SystemExit("no LoRA tensors found: is this an mlx-lm adapter?")

    unexpected = targets - set(TARGET_SUFFIXES)
    if unexpected:
        raise SystemExit(f"unexpected LoRA targets, refusing to guess: {sorted(unexpected)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    save_file(out, str(out_dir / "adapter_model.safetensors"))

    peft_config = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "base_model_name_or_path": BASE_MODEL,
        "r": rank,
        # MLX applies a single `scale`; PEFT applies lora_alpha / r.
        "lora_alpha": scale * rank,
        "lora_dropout": dropout,
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "target_modules": sorted(targets),
        "modules_to_save": None,
    }
    (out_dir / "adapter_config.json").write_text(
        json.dumps(peft_config, indent=2) + "\n")

    report = {
        "tensors": len(out),
        "rank": rank,
        "scale": scale,
        "lora_alpha": scale * rank,
        "targets": sorted(targets),
        "layers": len({k.split(".layers.")[1].split(".")[0]
                       for k in out if ".layers." in k}),
        "source_adapter": str(adapter_dir),
        "mlx_base": MLX_BASE,
        "cuda_base": BASE_MODEL,
        "out": str(out_dir),
    }
    (out_dir / "conversion.json").write_text(json.dumps(report, indent=2) + "\n")
    log_event("3.9", f"MLX adapter converted to PEFT: {len(out)} tensors, rank "
                     f"{rank}, alpha {scale * rank:g}, {report['layers']} layers.")
    return report


def verify(out_dir: Path, limit: int = 25) -> dict:
    """Run the held-out test questions through the converted adapter.

    Deliberately uses `lm.evaluate`'s own prompts and scorers rather than a
    bespoke check, so the numbers printed here are comparable to the MLX ones
    line for line.
    """
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = ("cuda" if torch.cuda.is_available()
              else "mps" if torch.backends.mps.is_available() else "cpu")
    dtype = torch.float16 if device != "cpu" else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    # transformers 5 renamed `torch_dtype` to `dtype`; 4.x only knows the old
    # name. Try the new one and fall back rather than pinning the library.
    try:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, dtype=dtype, device_map=None).to(device)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, torch_dtype=dtype, device_map=None).to(device)
    model = PeftModel.from_pretrained(model, str(out_dir)).eval()

    import sqlite3

    from lm import evaluate as ev

    # Replace only the generation call. Every prompt, parser and scorer below is
    # the one lm/evaluate.py uses for the MLX numbers, so the two are comparable
    # rather than merely similar.
    def generate_one(_model, _tokenizer, question: str, schema_text: str,
                     max_tokens: int = 320, system_override: str | None = None) -> str:
        system = system_override or (
            (ev.SYSTEM + schema_text) if schema_text else ev.TRAINED_SYSTEM)
        text = tokenizer.apply_chat_template(
            [{"role": "system", "content": system},
             {"role": "user", "content": question}],
            tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(device)
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=max_tokens,
                                    do_sample=False,
                                    pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(output[0][inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)

    original = ev.generate_one
    ev.generate_one = generate_one
    try:
        connection = sqlite3.connect(f"file:{ev.DB_PATH}?mode=ro", uri=True)
        try:
            synthetic = ev.load_query_set(ev.CORPUS / "task_a_test.jsonl", limit)
            report = {
                "device": device,
                "base": BASE_MODEL,
                "adapter": str(out_dir),
                "n": len(synthetic),
                "task_a": ev.evaluate_task_a(model, tokenizer, synthetic,
                                             connection, "", "converted"),
            }
            triage = ev.CORPUS / "task_b_test.jsonl"
            if triage.exists():
                report["task_b"] = ev.evaluate_triage(
                    model, tokenizer, ev.load_query_set(triage, limit))
            abstain = ev.CORPUS / "task_c_test.jsonl"
            if abstain.exists():
                report["task_c"] = ev.evaluate_abstention(
                    model, tokenizer, ev.load_query_set(abstain, limit), "")
        finally:
            connection.close()
    finally:
        ev.generate_one = original

    print(json.dumps(report, indent=2, default=str))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verify", action="store_true",
                        help="run the held-out test questions through the result")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    report = convert(args.adapter, args.out)
    print(json.dumps(report, indent=2))
    if args.verify:
        verify(args.out, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
