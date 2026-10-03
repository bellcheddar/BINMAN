#!/usr/bin/env bash
# Assert the atlas bundle is complete and within budget before any transfer.
# Exits non-zero on the first problem: a partial deploy is worse than none.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MAX_BUNDLE_GB=$(grep -E '^max_bundle_gb' config/thresholds.toml | awk -F'= *' '{print $2}')
fail() { printf 'preflight FAILED: %s\n' "$1" >&2; exit 1; }
ok()   { printf '  ok  %s\n' "$1"; }

printf 'BINMAN deploy preflight\n'

[[ -f data/atlas/binman.sqlite ]] || fail "data/atlas/binman.sqlite is missing"
ok "atlas present ($(du -h data/atlas/binman.sqlite | cut -f1))"

# The atlas must be readable and carry rows.
BRIDGES=$(sqlite3 data/atlas/binman.sqlite "SELECT COUNT(*) FROM bridge" 2>/dev/null || echo 0)
[[ "$BRIDGES" -gt 0 ]] || fail "the bridge table is empty"
ok "bridge rows: $BRIDGES"

[[ -f app/static/about.json ]] || fail "about.json is missing: run pipeline/build_about.py"
ok "About tab generated"

[[ -f app/static/vendor/VENDOR.json ]] || fail "vendored assets are missing"
for asset in molstar/molstar.js d3/d3.min.js plotly/plotly.min.js \
             tabulator/tabulator.min.js fonts/fonts.css; do
  [[ -s "app/static/vendor/$asset" ]] || fail "vendored asset missing: $asset"
done
ok "vendored front-end complete (no CDN at serve time)"

# Nothing licence-restricted may be inside the bundle.
if find data/atlas app/static -name '*.tsv' -o -name '*ubibrowser*' -o -name '*protacdb*' \
     -o -name '*biolip*' 2>/dev/null | grep -q .; then
  fail "a third-party dataset file is inside the bundle; see deploy/README.md"
fi
ok "no third-party dataset rows in the bundle"

if [[ -s models/binman-lm/fused/model.safetensors ]] && \
   find app/static data/atlas -name '*.safetensors' 2>/dev/null | grep -q .; then
  fail "model weights are inside the bundle; they must not ship"
fi
ok "no model weights in the bundle"

BUNDLE_BYTES=$(du -sk data/atlas app/static config 2>/dev/null | awk '{s+=$1} END {print s*1024}')
BUNDLE_GB=$(awk -v b="$BUNDLE_BYTES" 'BEGIN {printf "%.2f", b/1024/1024/1024}')
awk -v g="$BUNDLE_GB" -v m="$MAX_BUNDLE_GB" 'BEGIN {exit !(g <= m)}' \
  || fail "bundle is ${BUNDLE_GB} GB, over the ${MAX_BUNDLE_GB} GB budget"
ok "bundle size ${BUNDLE_GB} GB, within the ${MAX_BUNDLE_GB} GB budget"

printf '\npreflight passed. deploy/rsync.sh is cleared to run (Gate G3).\n'
