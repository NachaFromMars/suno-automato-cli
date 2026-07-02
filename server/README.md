# automato-server (P4+P5)

Self-hosted guarded Suno music factory: FastAPI + worker + REST `/api/v1` + FastMCP `/mcp` + server-rendered dashboard (Jinja2 + HTMX + Alpine.js, all assets local).

## Run

```bash
# venv lives at ../.venv (python3 -m venv .venv && pip install -r requirements.txt)
cd server
../.venv/bin/uvicorn automato.server:app --host 127.0.0.1 --port 8765
# or: systemctl start automato-server   (unit: /etc/systemd/system/automato-server.service)
```

MCP stdio entry: `cd server && ../.venv/bin/python -m automato.mcp`
MCP streamable-http: `POST http://127.0.0.1:8765/mcp`

## Design (per P2 spec)

- **One gated chokepoint:** `engine.submit_job()` runs the REAL `suno_prompt_guard.py`
  gates (precheck 11-block + production density, lyrics-check w/ instrumental mode,
  playlist-route vs album manifests + genre, novelty-check vs novelty-history.json)
  before any job may enter the queue. UI, REST and MCP all pass through it (F-10).
- **Shared flock:** the worker takes the SAME `suno-library/.batch-runner.lock` as the
  CLI batch runner — server and CLI can never spend credits concurrently (F-04).
- **F-07:** post-generation clip ids are cross-checked stdout ∩ metadata.json; if
  unverifiable the job becomes `needs-review`, never a silent success.
- **Quarantine:** postcheck failure moves takes to `_quarantine/` and strips them from
  metadata takes (same semantics as the P3 runner).
- **Files are source of truth for media**; SQLite (WAL, `server/state/app.db`) holds only
  the queue, job records and guard-run history.
- **No secrets:** auth.json stays in `~/.config/suno-cli/` and is only read by the suno
  CLI subprocess; `/api/v1/config` exposes a safe path-only subset.

## Endpoints

See `/docs` (OpenAPI) on the running server. Dashboard pages: `/`, `/generate`, `/jobs`,
`/library`, `/albums`, `/reports`. Live updates over SSE at `/events`.
