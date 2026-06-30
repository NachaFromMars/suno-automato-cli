---
name: suno-automato-cli
description: Use when controlling Suno from OpenClaw/VPS via authenticated suno-cli; full v0.5.7 coverage for generate/describe/lyrics/extend/concat/cover/remaster/stems/list/search/info/download/manage/auth.
---

# Suno Automato CLI Skill

Use `/root/.openclaw/workspace/bin/suno` or `scripts/suno-safe.sh`.

## Full command coverage

Create:
- `generate` — custom lyrics/tags/title/sliders/persona
- `describe` — prompt mode, Suno writes lyrics
- `lyrics` — lyrics only, free/no credits
- `extend` — continue clip from timestamp
- `concat` — stitch clips into full song
- `cover` — create cover of existing clip
- `remaster` — remaster with v5.5/v5/v4.5+
- `stems` — extract vocals/instruments

Browse/inspect:
- `list`, `search`, `info`, `status`, `persona`, `credits`, `models`, `timed-lyrics`

Manage:
- `download`, `set`, `publish`, `delete`

Auth/config/agent:
- `auth`, `config`, `agent-info`, `install-skill`, `update`

## Rules

- Do not expose cookies/JWT/passwords.
- Before credit-spending generation, confirm explicit user intent unless the user directly requested music generation.
- Prefer `--json` output for agent parsing.
- If auth expires, run `suno auth --refresh --json`.
- Treat `delete`, `set`, and `publish` as mutating operations.

## Safe checks

```bash
/root/.openclaw/workspace/bin/suno auth --refresh --json
/root/.openclaw/workspace/bin/suno credits --json
/root/.openclaw/workspace/bin/suno models --json
/root/.openclaw/workspace/bin/suno list --json
```

## Docs

- `docs/full-suno-cli-reference.md`
- `docs/agent-playbook.md`
- `docs/pc-chrome-remote-debug.md`
- `docs/openclaw-usage.md`
