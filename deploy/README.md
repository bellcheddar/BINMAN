# BINMAN deploy

**Nothing in this directory has been run.** Spec 4.7 requires the deploy scripts
to be written and left unexecuted, and Gate G3 covers running them. `GATE_OPEN.md`
states what G3 needs.

The droplet serves a **precomputed read-only atlas**. There is no folding, no
FreeSASA, no fpocket and no model inference at request time, and the app makes no
outbound request: every front-end library and font is vendored under
`app/static/vendor/`.

## What ships, and what must not

| Ships | Stays on the build machine |
|---|---|
| `app/` (templates, static, vendored libraries) | `data/cache/` |
| `data/atlas/binman.sqlite` | `data/validation/*.tsv` (licence-restricted) |
| `app/static/structures/` (trimmed, gzipped mmCIF) | `models/binman-lm/` (weights) |
| `app/static/about.json`, `workflow.svg` | `data/interim/` |
| `config/thresholds.toml` (the app reads it) | `data/manifests/` |

Two rules the rsync filter enforces:

1. **No third-party dataset row leaves this machine.** Several of the ten source
   databases restrict redistribution (PROTAC-DB prohibits it outright), so only
   computed metrics travel. See `data/validation/MANIFEST.md`.
2. **No model weights travel.** BINMAN-LM is served from the Studio behind the
   `BINMAN_LM_URL` feature flag, and the app is fully functional without it.

## Order

```bash
./deploy/preflight.sh          # asserts the bundle is complete and within budget
./deploy/rsync.sh              # needs G3
sudo cp deploy/binman.service /etc/systemd/system/   # on the droplet
sudo cp deploy/nginx.conf /etc/nginx/sites-available/binman
sudo ln -s /etc/nginx/sites-available/binman /etc/nginx/sites-enabled/
sudo systemctl daemon-reload && sudo systemctl enable --now binman
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d binman.mdeller.com
```

## Serving BINMAN-LM (optional)

On the Studio:

```bash
pixi run mlx_lm.server --model models/binman-lm/fused --port 8081
```

Then set `BINMAN_LM_URL` in `binman.service`. With it unset the natural-language
box is hidden and nothing else changes.
