#!/bin/bash
# Overnight ablation for BINMAN-LM.
#
# One variable per round, so a difference can be attributed. Rounds run
# sequentially: they all want the same GPU, and two at once would make both
# slower and neither comparable.
#
#   round 07  32 layers, rank 8    isolates DEPTH   against round 06
#   round 08  16 layers, rank 32   isolates RANK    against round 06
#   round 09  32B base             isolates SIZE    against round 06
#
# Round 06 (16 layers, rank 8, 2 epochs) is the control, and round 05
# (0.23 epochs) already answered the epoch question against it.
#
# Each round is evaluated as it finishes rather than at the end, so a crash at
# 4am still leaves the earlier results on disk. Everything is appended to
# RESULTS so the morning comparison is one file.

set -u
cd /Users/dellboy/Documents/Vibe_Coding/BINMAN

LOG_DIR="models/binman-lm/overnight"
mkdir -p "$LOG_DIR"
RESULTS="$LOG_DIR/results.jsonl"
PROGRESS="$LOG_DIR/progress.log"

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$PROGRESS"; }

# 2 epochs over the 28,304-example corpus at batch 4.
ITERS=14152
BASE_3B="mlx-community/Qwen2.5-3B-Instruct-4bit"
BASE_32B="mlx-community/Qwen2.5-32B-Instruct-4bit"

run_round() {
  local label="$1"; local base="$2"; shift 2
  say "START $label :: $*"
  local started=$(date +%s)
  if pixi run -q python lm/train.py --skip-stage-two "$@" \
       > "$LOG_DIR/$label.train.log" 2>&1; then
    say "TRAINED $label in $(( ($(date +%s) - started) / 60 )) min"
  else
    say "FAILED $label (exit $?) -- see $LOG_DIR/$label.train.log"
    # A failed round must not stop the sweep: the later rounds are independent
    # and their results are still worth having in the morning.
    return 1
  fi

  say "EVAL $label"
  # The adapter is copied to the stable adapters/ path by train.py, and the
  # base model has to be named explicitly or a 32B adapter is evaluated against
  # the 3B base and scores like noise.
  if pixi run -q python lm/evaluate.py --adapter models/binman-lm/adapters \
       --model "$base" --label "$label" --skip-preference \
       > "$LOG_DIR/$label.eval.log" 2>&1; then
    say "EVALUATED $label"
  else
    say "EVAL FAILED $label -- adapter is on disk, evaluate by hand"
  fi
  python3 - "$label" "$LOG_DIR" "$RESULTS" <<'PY'
import json, pathlib, sys
label, log_dir, results = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
row = {"label": label}
# lm_eval.json is keyed by stage label, so the metrics sit one level down.
# Writing the whole file put every round's row at the top level and left the
# comparison reading None for everything.
p = pathlib.Path("data/interim/lm_eval.json")
if p.exists():
    try:
        blob = json.loads(p.read_text())
        row["eval"] = blob.get(label) or blob.get(label.split("-")[0]) or {}
    except json.JSONDecodeError:
        row["eval"] = {}
with results.open("a") as handle:
    handle.write(json.dumps(row, default=str) + "\n")
print(f"recorded {label}")
PY
}

say "=== overnight sweep starting ==="
say "control is round 06: 16 layers, rank 8, 2 epochs"

# Depth. The question Marc asked first.
run_round "round07-32layers" "$BASE_3B" --iters $ITERS --layers 32 --rank 8

# Rank. The knob that was never actually reaching mlx until tonight (D-033),
# and the one most likely to matter: rank 8 over 16 layers is a very small
# number of trainable parameters for a four-class problem plus two others.
run_round "round08-rank32" "$BASE_3B" --iters $ITERS --layers 16 --rank 32

# Size. Timed rather than assumed: if 32B is too slow to reach a comparable
# number of epochs it is reported as not comparable rather than quietly run at
# a tenth of the data. The driver measures throughput and adjusts the cap.
say "measuring 32B throughput before committing to a full round"
MEASURED=$(pixi run -q python lm/measure_throughput.py \
             --model mlx-community/Qwen2.5-32B-Instruct-4bit --iters 10 2>&1 | tail -1)
say "32B throughput: $MEASURED"
ITERS_32B=$(python3 -c "
import sys
try:
    rate = float('$MEASURED'.split()[0])
except Exception:
    rate = 0.0
# Budget 6 hours. Report what that buys rather than forcing 2 epochs.
print(max(600, int(rate * 60 * 6)) if rate > 0 else 1200)
")
say "32B budget: $ITERS_32B iterations"
run_round "round09-32b" "$BASE_32B" --iters "$ITERS_32B" --layers 16 --rank 8 \
          --base-model "$BASE_32B" --batch-size 1

say "=== overnight sweep finished ==="
