#!/bin/bash
# Round 13: Qwen2.5-32B-Instruct-4bit, one full epoch, no time cap.
#
# Supersedes round 12, which was capped at 4,636 iterations to land inside a
# three-hour window and would have been 0.16 of an epoch: not comparable with
# the 3B rounds, which is exactly what the cap was designed to admit.
#
# One epoch, not two. Round 05 saw 0.23 epochs and round 06 saw two, an
# eightfold difference in exposure, and Task B moved from 0.8956 to 0.8862,
# inside sampling noise. Epochs were not the lever for the 3B and there is no
# reason they become one at 32B. A second epoch would cost another eighteen
# hours for something already measured as flat.
#
# Batch 2 rather than 1: measured at 13.03 iters/min against 24.40, which is
# 26.1 samples per minute against 24.4, so it is both marginally faster and
# half the checkpoint writes.
#
# Per D-036: this file is not to be edited while it runs.

set -u
cd /Users/dellboy/Documents/Vibe_Coding/BINMAN

LOG_DIR="models/binman-lm/overnight"
mkdir -p "$LOG_DIR"
RESULTS="$LOG_DIR/results.jsonl"
PROGRESS="$LOG_DIR/progress.log"
BASE_32B="mlx-community/Qwen2.5-32B-Instruct-4bit"
LABEL="round13-32b-1epoch"
# 28,304 training examples at batch 2.
ITERS=14152

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$PROGRESS"; }

say "START $LABEL :: 32B, 32 layers, rank 8, batch 2, $ITERS iters (one epoch)"
STARTED=$(date +%s)

if pixi run -q python lm/train.py --skip-stage-two --iters "$ITERS" \
     --layers 32 --rank 8 --batch-size 2 --base-model "$BASE_32B" \
     > "$LOG_DIR/$LABEL.train.log" 2>&1; then
  say "TRAINED $LABEL in $(( ($(date +%s) - STARTED) / 60 )) min"
else
  say "FAILED $LABEL -- see $LOG_DIR/$LABEL.train.log"
  exit 1
fi

say "EVAL $LABEL"
if pixi run -q python lm/evaluate.py --adapter models/binman-lm/adapters \
     --model "$BASE_32B" --label "$LABEL" --skip-preference \
     > "$LOG_DIR/$LABEL.eval.log" 2>&1; then
  say "EVALUATED $LABEL"
else
  say "EVAL FAILED $LABEL -- the adapter is on disk, evaluate by hand"
fi

python3 - "$LABEL" "$RESULTS" <<'PY'
import json, pathlib, sys
label, results = sys.argv[1], pathlib.Path(sys.argv[2])
blob = {}
source = pathlib.Path("data/interim/lm_eval.json")
if source.exists():
    try:
        blob = json.loads(source.read_text()).get(label) or {}
    except json.JSONDecodeError:
        blob = {}
with results.open("a") as handle:
    handle.write(json.dumps({"label": label, "eval": blob}, default=str) + "\n")
print(f"recorded {label}")
PY

say "=== $LABEL finished ==="
