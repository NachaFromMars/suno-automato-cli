---
name: suno-automato-cli
description: Use when controlling Suno from OpenClaw/VPS via authenticated suno-cli; supports credits/models/list/generate/download and trusted-PC auth refresh.
---

# Suno Automato CLI Skill

Use `/root/.openclaw/workspace/bin/suno` or `scripts/suno-safe.sh`.

Rules:
- Do not expose cookies/JWT/passwords.
- Before credit-spending generation, confirm explicit user intent.
- Prefer `--json` output for agent parsing.
- If auth expires, run `suno auth --refresh --json`.

Safe checks:

```bash
/root/.openclaw/workspace/bin/suno credits --json
/root/.openclaw/workspace/bin/suno models --json
/root/.openclaw/workspace/bin/suno list --json
```
