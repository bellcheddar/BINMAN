#!/usr/bin/env bash
# Transfer the atlas bundle to the droplet.
#
# GATE G3: this script is written but has never been run. It refuses to start
# unless BINMAN_DEPLOY_CONFIRM=yes is set, so an accidental invocation during an
# unattended build cannot reach the droplet.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST="${BINMAN_HOST:?set BINMAN_HOST, e.g. deploy@mdeller.com}"
REMOTE="${BINMAN_REMOTE_PATH:-/srv/binman}"

if [[ "${BINMAN_DEPLOY_CONFIRM:-no}" != "yes" ]]; then
  cat >&2 <<'MSG'
refusing to deploy.

This is Gate G3. Nothing has been transferred. To proceed:

  ./deploy/preflight.sh
  BINMAN_DEPLOY_CONFIRM=yes BINMAN_HOST=deploy@mdeller.com ./deploy/rsync.sh
MSG
  exit 2
fi

./deploy/preflight.sh

# --delete keeps the droplet in step with the build, and the excludes are the
# licence and weight rules from deploy/README.md.
rsync -avz --delete --human-readable --progress \
  --exclude '.git/' \
  --exclude '.pixi/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude 'data/cache/' \
  --exclude 'data/interim/' \
  --exclude 'data/manifests/' \
  --exclude 'data/validation/*.tsv' \
  --exclude 'data/validation/raw/' \
  --exclude 'models/' \
  --exclude 'lm/corpus/' \
  --exclude 'qc/' \
  app/ config/ data/atlas/ pyproject.toml \
  "${HOST}:${REMOTE}/"

printf '\ntransferred. On the droplet:\n'
printf '  sudo systemctl restart binman\n'
