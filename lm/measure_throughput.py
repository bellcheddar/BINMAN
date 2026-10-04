"""Measure training throughput for a base model, in iterations per minute.

The overnight sweep uses this to decide what a 32B round can actually reach
rather than assuming it. A model that cannot be trained to a comparable number
of epochs in the time available should be reported as not comparable, not run
at a tenth of the data and compared anyway.

Prints a single line: `<iters_per_minute> iters/min on <model>`.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRAIN_DATA = ROOT / "models" / "binman-lm" / "data"


def measure(model: str, iters: int, layers: int, rank: int,
            batch_size: int) -> float:
    work = Path(tempfile.mkdtemp(prefix="binman-throughput-"))
    try:
        (work / "lora_config.yaml").write_text(
            f"lora_parameters:\n  rank: {rank}\n  scale: 20.0\n  dropout: 0.0\n")
        command = [
            sys.executable, "-m", "mlx_lm", "lora",
            "--model", model, "--train", "--data", str(TRAIN_DATA),
            "--fine-tune-type", "lora",
            "--config", str(work / "lora_config.yaml"),
            "--num-layers", str(layers), "--batch-size", str(batch_size),
            "--iters", str(iters), "--learning-rate", "1e-5",
            "--adapter-path", str(work),
            # Evaluation would be counted in the wall clock and is not what is
            # being measured, so it is pushed beyond the end of the run.
            "--steps-per-eval", str(iters * 10),
            "--val-batches", "1", "--max-seq-length", "1024",
            "--mask-prompt", "--steps-per-report", str(iters),
        ]
        # The model download is not throughput, so it is excluded by timing from
        # after the first checkpoint would exist rather than from process start.
        started = time.monotonic()
        completed = subprocess.run(command, capture_output=True, text=True)
        elapsed = time.monotonic() - started
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip().splitlines()
            print(f"0 iters/min on {model} (failed: {tail[-1] if tail else 'no output'})")
            return 0.0
        return iters / (elapsed / 60.0)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--iters", type=int, default=10)
    parser.add_argument("--layers", type=int, default=16)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()

    rate = measure(args.model, args.iters, args.layers, args.rank,
                   args.batch_size)
    if rate:
        print(f"{rate:.2f} iters/min on {args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
