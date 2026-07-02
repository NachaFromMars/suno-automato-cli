# REST API Reference — automato-server

Base URL: `http://127.0.0.1:8765` (default bind is loopback-only).
All request/response bodies are JSON. Interactive OpenAPI docs: `GET /docs`.

**Auth:** open by default. If `api_token` is set (automato.toml / `AUTOMATO_API_TOKEN`),
the endpoints marked 🔒 require `Authorization: Bearer <token>` and return `401`
otherwise. Read-only endpoints are always open.

---

## Health & status

### `GET /health` (alias `GET /api/v1/health`)

```bash
curl -s 127.0.0.1:8765/health
```
```json
{"ok": true, "service": "suno-automato", "version": "1.0.0", "worker_alive": true, "at": "2026-07-02T16:31:59+02:00"}
```

### `GET /api/v1/status`

Live status: Suno credits probe, Xvfb display, worker, generation lock, queue, guard stats.
`?credits=false` skips the (slower) credits probe.

```bash
curl -s '127.0.0.1:8765/api/v1/status?credits=false'
```
```json
{
  "at": "2026-07-02T16:44:58+02:00",
  "auth_credits": {"ok": null, "skipped": true},
  "xvfb": {"display": ":99", "alive": true},
  "worker_alive": true,
  "generation_lock_held": false,
  "queue_depth": 0,
  "jobs_today": 0,
  "max_generations_per_day": 40,
  "guard_stats": {"total": 11, "failed": 7, "passed": 4}
}
```

---

## Guard validation (free — no credits)

### `POST /api/v1/validate`

Runs the full 4-gate guard (precheck, lyrics-check, playlist-route, novelty-check) and
returns a per-gate report plus an 11-block presence map. Same code path as the real gate.

```bash
curl -s 127.0.0.1:8765/api/v1/validate -X POST -H 'content-type: application/json' -d '{
  "title": "Golden Hour Letters",
  "genre": "Ballad",
  "album": "ballad-tinh-khuc-vol1",
  "style": "Leading Genre DNA: modern Vietnamese pop ballad ... Strictly Avoid: ...",
  "lyrics": "[Verse 1] ...",
  "instrumental": false
}'
```

Response (excerpt):
```json
{
  "passed": false,
  "gates": {
    "precheck":      {"passed": false, "exit_code": 2, "detail": {"missing": ["Hook Design", "..."]}},
    "lyrics_check":  {"passed": false, "exit_code": 2, "detail": {"missing_sections": ["chorus"]}},
    "playlist_route":{"passed": true,  "exit_code": 0, "detail": {"ok": true}},
    "novelty_check": {"passed": true,  "exit_code": 0, "detail": {"ok": true}}
  },
  "blocks_present": {"Leading Genre DNA": true, "Hook Design": false, "...": true}
}
```

---

## Generation

### 🔒 `POST /api/v1/generate`

**The** gated entry point. Re-runs the full guard server-side; only a PASS enqueues a job.

- `202 Accepted` → `{"accepted": true, "job_id": "…", "guard_report": {…}}`
- `422 Unprocessable` → `{"accepted": false, "reason": "guard_blocked", "guard_report": {…}}`
  (no credits spent) or `{"reason": "daily_generation_cap_reached", …}`

```bash
curl -s 127.0.0.1:8765/api/v1/generate -X POST \
  -H 'Authorization: Bearer $TOKEN' -H 'content-type: application/json' -d '{
  "title": "Golden Hour Letters",
  "genre": "Ballad",
  "album": "ballad-tinh-khuc-vol1",
  "style": "<full 11-block PromptStyle>",
  "lyrics": "<full sectioned lyrics>",
  "exclude": "generic stock loop, karaoke backing track",
  "weirdness": 62,
  "style_influence": 86,
  "instrumental": false
}'
```

Fields: `weirdness` / `style_influence` 0-100; `exclude` optional; `instrumental`
switches lyrics-check mode and the novelty threshold.

---

## Jobs & worker

### `GET /api/v1/jobs`

`?status=queued|running|succeeded|failed|blocked|cancelled|quarantined|needs-review`,
`?limit=` (≤200), `?offset=`.

```bash
curl -s '127.0.0.1:8765/api/v1/jobs?status=succeeded&limit=5'
```

### `GET /api/v1/jobs/{id}`

Full job record: status, progress, guard_report, postcheck_report, result (clip ids,
project dir, stdout tail). `404` if unknown.

### 🔒 `POST /api/v1/jobs/{id}/cancel`

Cancels a **queued** job (running jobs cannot be cancelled — the money is in flight).
`409` if not cancellable, `404` if unknown.

```bash
curl -s -X POST 127.0.0.1:8765/api/v1/jobs/ab12cd34ef56/cancel -H 'Authorization: Bearer $TOKEN'
```

### 🔒 `POST /api/v1/worker/pause` · `POST /api/v1/worker/resume`

Pause/resume the single generation worker (queue keeps accepting jobs).

```bash
curl -s -X POST 127.0.0.1:8765/api/v1/worker/pause -H 'Authorization: Bearer $TOKEN'
```

---

## Library (read-only)

### `GET /api/v1/library/projects`

Query: `genre`, `album`, `q` (text search over title/album/genre/style), `limit`, `offset`.

```bash
curl -s '127.0.0.1:8765/api/v1/library/projects?q=Bamboo&limit=3'
```

### `GET /api/v1/library/projects/{genre}/{batch}`

Full project detail: takes (with audio/cover file names + existence), style prompt,
quarantined takes, suno ids.

### `GET /api/v1/media/{genre}/{batch}/audio/{file}.mp3`

Streams audio with **HTTP Range** support (seeking works in `<audio>`):

```bash
curl -s -r 0-1023 -o /dev/null -w '%{http_code} %{size_download}\n' \
  '127.0.0.1:8765/api/v1/media/Thieu-Nhi/2026-07-02_Bamboo-Telegraph/audio/take1.mp3'
# → 206 1024
```

### `GET /api/v1/media/{genre}/{batch}/cover/{file}`

Cover art (jpeg/png). Path traversal attempts return `404`.

---

## Albums & reports

### `GET /api/v1/albums` · `GET /api/v1/albums/{slug}`

Album manifests: track count vs target, remote playlist id, last remote sync.

### `GET /api/v1/guards/reports`

Guard-run history (`?passed=true|false`, `limit`, `offset`) + aggregate stats.

### `GET /api/v1/novelty`

Novelty-history entries (newest first): title, genre, album, clip ids, style excerpt.

### `GET /api/v1/config`

Safe path-only config subset — never returns secrets; `api_token_set` is a boolean only.

---

## Events

### `GET /events` (alias `GET /api/v1/events`)

Server-Sent Events: job state changes, worker state, queue heartbeats (every ~15s).

```bash
curl -N 127.0.0.1:8765/events
# event: heartbeat
# data: {"at":"…","queue_depth":0,"worker_alive":true,"worker_paused":false,"current_job":null}
```

---

## Dashboard (HTML)

`/` overview · `/generate` (live guard preview) · `/jobs` (+`/jobs/{id}`) ·
`/library` (+`/library/{genre}/{batch}`) · `/albums` (+`/albums/{slug}`) · `/reports`.
The HTMX partials under `/ui/*` are internal; 🔒 `/ui/generate` is token-protected like
`/api/v1/generate`.

## MCP

`POST /mcp` — streamable-http MCP endpoint (🔒 when a token is set). See [MCP.md](MCP.md).
