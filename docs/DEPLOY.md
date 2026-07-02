# Deployment Guide

Three ways to run automato-server: bare venv (dev), **systemd** (recommended on a VPS),
or **Docker**. In all cases the golden rules are:

- Bind to `127.0.0.1` unless you have TLS + bearer auth in front.
- `auth.json` (Suno credentials) lives in `~/.config/suno-cli/`, mode `0600`,
  outside the repo — the server never reads it directly, only the `suno` CLI subprocess does.

## 1. systemd (VPS)

```ini
# /etc/systemd/system/automato-server.service
[Unit]
Description=Suno Automato server (FastAPI + worker + MCP)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/suno-automato-cli/server
ExecStart=/opt/suno-automato-cli/.venv/bin/uvicorn automato.server:app --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
# Optional overrides (or use automato.toml next to the repo root):
# Environment=AUTOMATO_API_TOKEN=change-me
# Environment=AUTOMATO_MAX_GEN_PER_DAY=40

[Install]
WantedBy=multi-user.target
```

```bash
python3 -m venv /opt/suno-automato-cli/.venv
/opt/suno-automato-cli/.venv/bin/pip install -r /opt/suno-automato-cli/server/requirements.txt
systemctl daemon-reload && systemctl enable --now automato-server
curl -s 127.0.0.1:8765/health
```

The queue survives restarts (SQLite WAL); jobs that were mid-generation at crash time
are marked `needs-review`, never silently lost.

### Xvfb

The captcha solver needs an X display. Keep **one** fixed display alive with
`scripts/ensure-xvfb.sh` (idempotent, flock-guarded — reuses `:99` instead of
`xvfb-run -a`, which leaks a new display per call):

```bash
scripts/ensure-xvfb.sh            # starts/reuses :99, prints DISPLAY
source scripts/ensure-xvfb.sh     # same, exports DISPLAY into your shell
```

## 2. Docker

```bash
cp automato.toml.example automato.toml   # optional
docker compose up -d --build
curl http://127.0.0.1:8765/health
```

What the compose file wires:

| Mount | Purpose |
|---|---|
| `./suno-library:/data/suno-library` | music library (files = source of truth) |
| `automato-state:/data/state` | SQLite queue + fixed Xauthority |
| `$SUNO_BIN:/app/bin/suno:ro` | your host-installed upstream suno CLI |
| `~/.config/suno-cli/auth.json:…:ro` | credentials, **read-only**, never in the image |

The entrypoint boots Xvfb on `:99` with a **fixed Xauthority** under `/data/state/`
(no `xvfb-run` temp dirs), then execs uvicorn. Container healthcheck hits `/health`.
`shm_size: 1g` is required for Chrome.

Ports stay loopback-published (`127.0.0.1:8765:8765`) by default — change only together
with bearer auth + TLS.

## 3. Bearer-token auth

Set the token in `automato.toml`:

```toml
api_token = "long-random-string"        # openssl rand -hex 32
```

or env: `AUTOMATO_API_TOKEN=…`. Effect:

- 🔒 required (`Authorization: Bearer <token>`, else `401`):
  `POST /api/v1/generate`, `POST /api/v1/jobs/{id}/cancel`,
  `POST /api/v1/worker/pause|resume`, `POST /ui/generate`, everything under `/mcp`.
- Still open: all read-only GET endpoints and the dashboard pages
  (they can't spend credits or mutate state).

Token comparison is constant-time (`hmac.compare_digest`). With no token configured
(default), everything is open — acceptable **only** on loopback.

## 4. Reverse proxy (optional, for remote access)

```nginx
server {
    listen 443 ssl;
    server_name automato.example.com;
    # ssl_certificate …; ssl_certificate_key …;
    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        # SSE support:
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

Always combine remote exposure with `api_token` + TLS. Consider IP allowlists or an
authenticating proxy for the read-only dashboard too — it exposes your library titles
and credit balance.

## 5. Operational safety rails

| Rail | Mechanism |
|---|---|
| No concurrent generation | shared flock `suno-library/.batch-runner.lock` (server worker + CLI runner) |
| Daily credits fuse | `max_generations_per_day` (default 40) |
| No ungated generation | `suno-lib.sh generate` exits 78 without `AUTOMATO_GATED=1` |
| Bad output never counts | postcheck failure ⇒ quarantine, excluded from album targets |
| Crash honesty | jobs running at crash ⇒ `needs-review` |
