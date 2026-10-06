#!/bin/bash
# Round 15: Qwen2.5-3B-Instruct-4bit, round 07's recipe exactly, new corpus.
#
# The defect this exists to fix: the abstain head refuses every question the
# atlas can answer. Abstention recall 1.0000 on 40 unanswerable questions,
# specificity 0.0000 on BINMAN's own twelve presets, each of which parses,
# returns its page's record type and returns rows (D-086). Task C held 784
# training rows and every one of them was a refusal, so the head learned that
# the answer is always no. A classifier shown one class is not a classifier.
#
# Two things changed, and nothing else:
#
#   1. Task C now has an answerable class, 980 rows against 980 refusals. The
#      positives are Task A training questions, the only questions in this build
#      whose answerability is established rather than assumed: each was
#      generated against the live atlas and then parsed by the app's own parser,
#      and anything the parser rejected was dropped. The twelve app presets that
#      specificity is measured on are NOT in the corpus, and neither is the
#      Task A held-out split.
#   2. The abstain system prompt asks for a decision rather than presupposing
#      one. It used to read "you state precisely what is missing when a question
#      cannot be answered", which answers the question in the prompt. It is
#      defined once now, in app/lm.py, and imported by the corpus builder and
#      the evaluator, because it had been written out three times.
#
# 3B and not 32B, because 3B is what is served. deploy/hf-adapter carries the
# round 07 LoRA over Qwen/Qwen2.5-3B-Instruct and that is the adapter the Space
# loads, so it is the adapter the measurement was taken on and the one that has
# to improve. The 32B round 14 is the better model and is not deployed.
#
# Round 07's hyperparameters to the letter: rank 8, 32 layers, batch 4, lr 1e-5.
# 15,806 iterations is two epochs of the new 31,610-row corpus, matching round
# 07's two epochs of its 28,304 rows, so corpus is the only variable and the
# comparison against round 07 means something.
#
# Stage two is skipped. The new preference set has 980
# `refused_an_answerable_question` pairs aimed at exactly this defect, and DPO
# is the obvious next lever, but an earlier run at the SFT learning rate
# collapsed the policy. SFT first, measure, then decide. One variable at a time.
#
# Per D-036: this file is not to be edited while it runs.

set -u
cd /Users/dellboy/Documents/Vibe_Coding/BINMAN

LOG_DIR="models/binman-lm/overnight"
mkdir -p "$LOG_DIR"
RESULTS="$LOG_DIR/results.jsonl"
PROGRESS="$LOG_DIR/progress.log"
BASE_3B="mlx-community/Qwen2.5-3B-Instruct-4bit"
LABEL="round15-3b-abstain-balanced"
# 31,610 training examples at batch 4, two epochs.
ITERS=15806

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$PROGRESS"; }

say "START $LABEL :: 3B, 32 layers, rank 8, batch 4, $ITERS iters (two epochs)"
STARTED=$(date +%s)

if pixi run -q python lm/train.py --skip-stage-two --iters "$ITERS" \
     --layers 32 --rank 8 --batch-size 4 --base-model "$BASE_3B" \
     > "$LOG_DIR/$LABEL.train.log" 2>&1; then
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

# The metric this round exists for. It is not part of lm/evaluate.py, because it
# asks the atlas which questions are answerable rather than reading a label
# file, so it needs the database and runs separately.
say "SPECIFICITY $LABEL"
if pixi run -q python pipeline/lm_abstention_check.py \
     --adapter models/binman-lm/adapters --model "$BASE_3B" \
     > "$LOG_DIR/$LABEL.specificity.log" 2>&1; then
  say "SPECIFICITY MEASURED $LABEL"
else
  say "SPECIFICITY FAILED $LABEL -- see $LOG_DIR/$LABEL.specificity.log"
fi

python3 - "$LABEL" "$RESULTS" <<'PY'
import json, pathlib, sys
label, results = sys.argv[1], pathlib.Path(sys.argv[2])
blob = {"label": label}
for key, name in (("eval", "lm_eval.json"),
                  ("specificity", "lm_abstention_check.json")):
    source = pathlib.Path("data/interim") / name
    if source.exists():
        blob[key] = json.loads(source.read_text(encoding="utf-8"))
with results.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(blob, default=str) + "\n")
print(json.dumps({k: v for k, v in blob.items() if k != "eval"},
                 indent=2, default=str)[:2000])
PY

say "DONE $LABEL in $(( ($(date +%s) - STARTED) / 60 )) min total"
