# MCP Server — automato-mcp

Suno Automato exposes an MCP (Model Context Protocol) server so any MCP-capable AI
client — Claude Desktop, OpenClaw, Cursor, custom agents — can drive the guarded music
factory. All tools are thin wrappers over the **same engine layer** as the REST API and
dashboard: there is no bypass around the guard gate.

## Transports

| Transport | How | Use case |
|---|---|---|
| **stdio** | `cd server && ../.venv/bin/python -m automato.mcp` | local clients (Claude Desktop) |
| **streamable-http** | `POST http://127.0.0.1:8765/mcp` on the running server | remote/agent platforms |

The http transport is stateless and honors bearer auth: when `api_token` is configured,
requests must send `Authorization: Bearer <token>` (401 otherwise).

## The 7 tools

### 1. `suno_status()`
Auth/credits (live probe of the suno CLI), worker alive/paused, Xvfb display state,
generation lock, queue depth, jobs today vs daily cap, guard stats.

### 2. `suno_validate(style, lyrics, title, genre, album, instrumental=False)`
Runs the **full guard gate without spending credits**. Returns the per-gate report
(precheck / lyrics_check / playlist_route / novelty_check, each with exit code + detail)
plus `blocks_present` — a presence map of the 11 PromptStyle blocks. Iterate on your
prompt with this tool until `passed: true` before calling `suno_generate`.

### 3. `suno_generate(title, genre, album, style, lyrics, exclude="", weirdness=62, style_influence=86, instrumental=False)`
Gated generation. The guard gate runs first; on FAIL you get the guard report back and
**no credits are spent**. On PASS the job enters the queue and you get a `job_id`.
Generation is asynchronous — poll with `suno_job`.

### 4. `suno_job(job_id)`
Full job record: status (`queued|running|succeeded|failed|quarantined|needs-review|cancelled`),
guard report, postcheck report, clip ids, project directory.

### 5. `suno_jobs(status="", limit=20)`
Compact job list, optionally filtered by status.

### 6. `suno_library_search(query="", genre="", album="", limit=20)`
Search the local music library (per-project `metadata.json` index) by free text, genre
or album.

### 7. `suno_albums()`
All album manifests: track counts vs targets, remote playlist ids, last sync time.

## Recommended agent flow

```
suno_status                      → check credits + queue is sane
suno_albums                      → pick the target album (genre must match)
suno_validate(...)               → iterate until passed == true   (free)
suno_generate(...)               → job_id                          (spends credits)
suno_job(job_id)                 → poll until succeeded / quarantined
suno_library_search(title)       → confirm the takes landed
```

## Client configuration

### Claude Desktop (stdio)

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "suno-automato": {
      "command": "/path/to/suno-automato-cli/.venv/bin/python",
      "args": ["-m", "automato.mcp"],
      "cwd": "/path/to/suno-automato-cli/server"
    }
  }
}
```

### OpenClaw (streamable-http)

```json
{
  "mcp": {
    "servers": {
      "suno-automato": {
        "url": "http://127.0.0.1:8765/mcp",
        "headers": { "Authorization": "Bearer <api_token>" }
      }
    }
  }
}
```

### Raw streamable-http smoke test

```bash
curl -s -X POST http://127.0.0.1:8765/mcp/ \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
```

## Guarantees

- `suno_generate` cannot skip the gate — it calls the same `engine.submit_job()` as the
  REST API and the dashboard (audit finding F-10).
- The worker shares an OS flock with the CLI batch runner — an MCP-triggered job will
  wait, never double-spend (F-04).
- Post-generation, clip metadata is postchecked; failures are quarantined and excluded
  from album counts (F-05); unverifiable clip ids mark the job `needs-review` (F-07).
