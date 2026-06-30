# Suno Automato CLI

Agent-native Suno automation wrapper for OpenClaw/VPS workflows.

This repo packages a safe operating layer around [`paperfoot/suno-cli`](https://github.com/paperfoot/suno-cli) so an agent can control Suno from a VPS after authenticating via a trusted desktop Chrome session.

## What it does

- Uses `suno` CLI as the underlying engine.
- Supports long-lived authentication via Suno/Clerk session cookie.
- Verifies auth with `suno auth --refresh` and `suno credits --json`.
- Provides wrapper commands for agent-safe usage.
- Keeps cookies, JWTs, passwords, and browser profiles out of git.

## Current verified environment

- Source CLI: `paperfoot/suno-cli`
- Local binary path: `/root/.openclaw/workspace/bin/suno`
- Verified Suno model: `v5.5`
- Verified plan detection: `Pro Plan`
- Tested auth refresh: OK

## Install

Download/install upstream `suno` binary first, then put it on PATH or set `SUNO_BIN`:

```bash
export SUNO_BIN=/root/.openclaw/workspace/bin/suno
```

## Auth flow used

1. Launch Chrome on a trusted PC with remote debugging enabled.
2. Connect to that Chrome through Tailscale.
3. Open `https://suno.com/create` and confirm the user is logged in.
4. Extract the `auth.suno.com` Clerk `__client` cookie through Chrome DevTools Protocol.
5. Run:

```bash
suno auth --cookie '<__client_cookie>' --json
suno auth --refresh --json
suno credits --json
```

Do **not** commit cookies or tokens.


## Full Suno CLI Coverage

This wrapper now documents and exposes the full `suno-cli` v0.5.7 command surface:

- Create: `generate`, `describe`, `lyrics`, `extend`, `concat`, `cover`, `remaster`, `stems`
- Browse/inspect: `list`, `search`, `info`, `persona`, `status`, `credits`, `models`, `timed-lyrics`
- Manage: `download`, `set`, `publish`, `delete`
- Auth/config/agent: `auth`, `config`, `agent-info`, `install-skill`, `update`

See:

- [`docs/full-suno-cli-reference.md`](docs/full-suno-cli-reference.md)
- [`docs/agent-playbook.md`](docs/agent-playbook.md)

## Commands

```bash
./scripts/suno-safe.sh credits
./scripts/suno-safe.sh models
./scripts/suno-safe.sh list
./scripts/suno-safe.sh refresh
```

Generation is intentionally explicit because it can spend Suno credits:

```bash
./scripts/suno-safe.sh generate --title "Demo" --tags "cinematic pop" --lyrics-file lyrics.txt --wait --json
```

## Security

Never commit:

- cookies
- JWTs
- passwords
- browser profiles
- generated private songs unless explicitly intended
- `.env`
- `auth.json`

See `.gitignore`.

## License

Wrapper code in this repo is MIT. Upstream `suno-cli` remains under its own license.
