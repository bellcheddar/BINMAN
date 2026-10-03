#!/usr/bin/env bash
# Serve BINMAN-LM from the Studio (spec 3.9). The droplet never gets the weights.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${BINMAN_LM_PORT:-8081}"
BASE="${BINMAN_LM_BASE:-mlx-community/Qwen2.5-3B-Instruct-4bit}"
ADAPTER="${BINMAN_LM_ADAPTER:-models/binman-lm/adapters}"

# BINMAN-LM serves as base model plus adapter, not as a fused model. mlx-lm's
# fuse produced a model that did not carry the fine-tune: it parsed 0 of 10
# held-out test questions and invented its own output schema, while the same
# adapter against the base model parses 10 of 10. See DECISIONS.md D-016.
if [[ ! -d "$ADAPTER" ]]; then
  printf 'no adapter at %s; nothing to serve\n' "$ADAPTER" >&2
  exit 1
fi

exec pixi run mlx_lm.server --model "$BASE" --adapter-path "$ADAPTER" --port "$PORT"
