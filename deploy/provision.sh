#!/usr/bin/env bash
# Provision BINMAN on the mdeller.com droplet, matching the layout its other
# Flask apps already use: /opt/<name>, a dedicated service user, a .venv inside
# the app directory, a <name>-web.service unit and an nginx vhost.
#
# GATE G3. This reaches a live production host, so like deploy/rsync.sh it
# refuses to start without BINMAN_DEPLOY_CONFIRM=yes.
#
#   BINMAN_DEPLOY_CONFIRM=yes ./deploy/provision.sh
#
# Idempotent: safe to re-run. The transfer step is deploy/rsync.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DROPLET="${DROPLET_SSH:-root@45.55.102.228}"
APP_DIR="/opt/binman"
DOMAIN="${BINMAN_DOMAIN:-binman.mdeller.com}"

if [[ "${BINMAN_DEPLOY_CONFIRM:-no}" != "yes" ]]; then
  cat >&2 <<MSG
refusing to provision.

This is Gate G3 and $DROPLET is a live host serving seventeen other apps.
Nothing has been changed. To proceed:

  BINMAN_DEPLOY_CONFIRM=yes ./deploy/provision.sh
MSG
  exit 2
fi

./deploy/preflight.sh

printf '\n== 1. service user and directory ==\n'
ssh "$DROPLET" bash -s <<REMOTE
set -euo pipefail
id -u binman >/dev/null 2>&1 || useradd --system --home-dir $APP_DIR --shell /usr/sbin/nologin binman
# rsync does not create nested parents, so every destination directory it will
# write into has to exist first.
mkdir -p $APP_DIR/app $APP_DIR/config $APP_DIR/data/atlas
chown -R binman:binman $APP_DIR
REMOTE

printf '\n== 2. application and atlas ==\n'
# --delete keeps the droplet in step with the build. The excludes are the
# licence and weight rules from deploy/README.md: no model weights, no
# third-party dataset rows, no build intermediates.
rsync -avz --delete --human-readable \
  --exclude '.git/' --exclude '.pixi/' --exclude '.venv/' \
  --exclude '__pycache__/' --exclude 'data/cache/' --exclude 'data/interim/' \
  --exclude 'data/manifests/' --exclude 'data/validation/*.tsv' \
  --exclude 'data/validation/raw/' --exclude 'models/' --exclude 'lm/corpus/' \
  --exclude 'qc/' \
  app/ "$DROPLET:$APP_DIR/app/"
rsync -avz --delete config/ "$DROPLET:$APP_DIR/config/"
rsync -avz --delete data/atlas/ "$DROPLET:$APP_DIR/data/atlas/"
rsync -avz wsgi.py pyproject.toml "$DROPLET:$APP_DIR/"

printf '\n== 3. virtualenv ==\n'
ssh "$DROPLET" bash -s <<REMOTE
set -euo pipefail
cd $APP_DIR
test -d .venv || python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet flask gunicorn
chown -R binman:binman $APP_DIR
REMOTE

printf '\n== 4. service ==\n'
rsync -az deploy/binman-web.service "$DROPLET:/etc/systemd/system/binman-web.service"
ssh "$DROPLET" bash -s <<'REMOTE'
set -euo pipefail
systemctl daemon-reload
systemctl enable binman-web.service
# `enable --now` starts the service only when it is stopped, so on every
# redeploy of an already-running app it did nothing. Flask caches templates in
# the worker processes, so the new HTML sat on disk while gunicorn kept serving
# the old: a template change has never reached the live site from this script.
# Static files were fine, which is what made it hard to see. Restart always.
systemctl restart binman-web.service
sleep 3
systemctl is-active --quiet binman-web.service || { journalctl -u binman-web -n 30 --no-pager; exit 1; }
curl -fsS -o /dev/null -w 'local gunicorn: HTTP %{http_code}\n' http://127.0.0.1:8090/ || exit 1
REMOTE

printf '\n== 5. nginx ==\n'
rsync -az deploy/nginx-binman.conf "$DROPLET:/etc/nginx/sites-available/binman"
ssh "$DROPLET" bash -s <<REMOTE
set -euo pipefail
ln -sf /etc/nginx/sites-available/binman /etc/nginx/sites-enabled/binman
nginx -t
systemctl reload nginx
REMOTE

printf '\n== 6. TLS ==\n'
ssh "$DROPLET" bash -s <<REMOTE
set -euo pipefail
certbot --nginx -d $DOMAIN --non-interactive --agree-tos \
  -m marc@marcdeller.com --redirect || {
    echo "certbot failed. The site is up on plain HTTP; re-run certbot by hand." >&2
    exit 0
  }
REMOTE

printf '\nprovisioned. https://%s\n' "$DOMAIN"
