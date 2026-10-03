#!/usr/bin/env bash
# Serve BINMAN-LM from the Studio (spec 3.9). The droplet never gets the weights.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${BINMAN_LM_MODEL:-models/binman-lm/fused}"
PORT="${BINMAN_LM_PORT:-8081}"

if [[ ! -d "$MODEL" ]]; then
  printf 'no fused model at %s; falling back to the adapters\n' "$MODEL" >&2
  exec pixi run mlx_lm.server \
    --model mlx-community/Qwen2.5-3B-Instruct-4bit \
    --adapter-path models/binman-lm/adapters \
    --port "$PORT"
fi

exec pixi run mlx_lm.server --model "$MODEL" --port "$PORT"
