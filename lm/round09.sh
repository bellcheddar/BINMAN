#!/bin/bash
# Round 09: 32 layers AND rank 32, the combination the sweep did not test.
#
# Rounds 07 and 08 each lifted Task B macro-F1 from the control's 0.8862 to
# about 0.93, by different routes: depth (32 layers, rank 8) reached 0.9336 and
# width (16 layers, rank 32) reached 0.9293 for 48 fewer minutes. Neither
# saturated, so the combination is the obvious next point and nothing in the
# original sweep covered it.
#
# Written as a NEW file rather than an edit to lm/overnight.sh, which is the
# whole lesson of D-035: bash reads a running script lazily by byte offset, and
# the original was edited mid-run and then restored, which left the interpreter
# re-executing the round 08 line instead of advancing to the 32B section. This
# file is not to be touched while it runs.

set -u
cd /Users/dellboy/Documents/Vibe_Coding/BINMAN

LOG_DIR="models/binman-lm/overnight"
mkdir -p "$LOG_DIR"
RESULTS="$LOG_DIR/results.jsonl"
PROGRESS="$LOG_DIR/progress.log"
BASE_3B="mlx-community/Qwen2.5-3B-Instruct-4bit"
ITERS=14152

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$PROGRESS"; }

LABEL="round09-32layers-rank32"
say "START $LABEL :: 32 layers, rank 32, $ITERS iters"
STARTED=$(date +%s)

if pixi run -q python lm/train.py --skip-stage-two --iters $ITERS \
     --layers 32 --rank 32 > "$LOG_DIR/$LABEL.train.log" 2>&1; then
  say "TRAINED $LABEL in $(( ($(date +%s) - STARTED) / 60 )) min"
else
  say "FAILED $LABEL -- see $LOG_DIR/$LABEL.train.log"
  exit 1
fi

say "EVAL $LABEL"
if pixi run -q python lm/evaluate.py --adapter models/binman-lm/adapters \
     --model "$BASE_3B" --label "$LABEL" --skip-preference \
     > "$LOG_DIR/$LABEL.eval.log" 2>&1; then
  say "EVALUATED $LABEL"
else
  say "EVAL FAILED $LABEL -- the adapter is on disk, evaluate by hand"
fi

# Capture reads the stage-keyed entry rather than the whole file, which is what
# left the earlier rows empty.
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

say "=== round 09 finished ==="
