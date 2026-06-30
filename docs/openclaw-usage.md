# OpenClaw Usage Notes

- Treat generation as credit-spending. Ask before running `generate` unless user explicitly requested a song.
- `credits`, `models`, `list`, `download` are safe read/list operations.
- Use JSON output for agent parsing.
- If auth expires, run `scripts/suno-safe.sh refresh` first.
- If refresh fails, repeat the trusted PC Chrome cookie extraction flow.
