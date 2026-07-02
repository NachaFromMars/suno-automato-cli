# Security Policy

## Secrets handling

- **Suno credentials** (`auth.json`: session cookie + JWT) are created by the upstream
  `suno auth` flow and live in `~/.config/suno-cli/auth.json` with mode `0600` —
  **outside this repo**, never committed, never baked into the Docker image
  (mounted read-only at runtime), never stored in the SQLite database, never returned
  by any API endpoint. `GET /api/v1/config` exposes paths only; the presence of an API
  token is reported as a boolean.
- `.gitignore` and `.dockerignore` exclude cookies, JWTs, env files, browser profiles
  and all generated media.
- Logs: guard reports and job records contain prompts/lyrics/clip ids — no credentials.

## Network posture

- Default bind is `127.0.0.1:8765` — nothing is exposed off-host out of the box.
- Optional bearer token (`api_token` in `automato.toml` / `AUTOMATO_API_TOKEN`) protects
  all mutating endpoints (`generate`, job `cancel`, worker `pause`/`resume`, `/ui/generate`)
  and the `/mcp` mount. Comparison is constant-time.
- Read-only endpoints stay open by design for loopback use. If you expose the server
  beyond loopback, use TLS (reverse proxy) + the bearer token, and consider protecting
  the dashboard as well — see [docs/DEPLOY.md](docs/DEPLOY.md).

## Spend protection

- Single gated chokepoint: no code path spends credits without the full guard PASS.
- OS-level flock prevents concurrent generation (double spend) across server + CLI.
- Daily generation cap (`max_generations_per_day`, default 40).
- Cancel only affects queued jobs; running generations are never silently duplicated.

## Media path safety

- Audio/cover streaming resolves paths strictly inside `suno-library/`; `..`/absolute
  traversal attempts return `404`.

## Reporting a vulnerability

Open a GitHub issue **without** exploit details and ask for a private channel, or
contact the repository owner directly. Please do not publish credential-impacting
issues before a fix is available.
