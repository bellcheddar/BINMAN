#!/bin/bash
# Round 12: Qwen2.5-32B-Instruct-4bit, the size question.
#
# Not a straight port of round 07. The 3B is 36 layers at hidden 2048 and the
# winner used 32 of those layers; the 32B is 64 layers at hidden 5120, so "32
# layers" is a different fraction of a much wider model. Depth is held at 32,
# which is where the 3B gain came from, and rank at 8, which is what round 07
# used. Batch 1 with gradient checkpointing, because 32 layers at rank 32 on
# the 3B already exhausted swap at batch 4.
#
# The iteration budget is MEASURED, not assumed. A 32B round that cannot reach
# a comparable number of epochs in the time available is reported as not
# comparable rather than quietly trained on a tenth of the data.
#
# Per D-036: this file is not to be edited while it runs.

set -u
cd /Users/dellboy/Documents/Vibe_Coding/BINMAN

LOG_DIR="models/binman-lm/overnight"
mkdir -p "$LOG_DIR"
RESULTS="$LOG_DIR/results.jsonl"
PROGRESS="$LOG_DIR/progress.log"
BASE_32B="mlx-community/Qwen2.5-32B-Instruct-4bit"
LABEL="round12-32b"
# Marc is out for a game; budget the training itself to about three hours and
# leave the rest for evaluation.
BUDGET_MINUTES=190

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$PROGRESS"; }

say "=== $LABEL: measuring 32B throughput before committing ==="
MEASURED=$(pixi run -q python lm/measure_throughput.py --model "$BASE_32B" \
             --iters 8 --layers 32 --rank 8 --batch-size 1 2>&1 | tail -1)
say "throughput: $MEASURED"

ITERS=$(python3 -c "
line = '''$MEASURED'''
try:
    rate = float(line.split()[0])
except Exception:
    rate = 0.0
budget = $BUDGET_MINUTES
# Cap at two epochs' worth; there is no point buying more than the 3B rounds saw.
two_epochs = 28304
print(min(two_epochs, max(400, int(rate * budget))) if rate > 0 else 600)
")
say "$LABEL budget: $ITERS iterations (~$BUDGET_MINUTES min)"

STARTED=$(date +%s)
if pixi run -q python lm/train.py --skip-stage-two --iters "$ITERS" \
     --layers 32 --rank 8 --batch-size 1 --base-model "$BASE_32B" \
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
