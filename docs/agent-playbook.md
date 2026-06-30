# Agent Playbook for Suno Automato

## Default sequence

```bash
scripts/suno-safe.sh refresh
scripts/suno-safe.sh credits
scripts/suno-safe.sh models
```

## Generate from user-provided lyrics

1. Save lyrics to a file.
2. Ask confirmation if not explicitly requested.
3. Run:

```bash
scripts/suno-safe.sh generate \
  --title "..." \
  --tags "..." \
  --lyrics-file lyrics.txt \
  --model v5.5 \
  --wait \
  --download ./outputs \
  --json
```

## Generate from prompt only

```bash
scripts/suno-safe.sh describe \
  --prompt "..." \
  --tags "..." \
  --model v5.5 \
  --wait \
  --download ./outputs \
  --json
```

## Free lyrics draft

```bash
scripts/suno-safe.sh lyrics --prompt "..." --json
```

## Post-generation workflow

```bash
scripts/suno-safe.sh list --json
scripts/suno-safe.sh info <clip_id> --json
scripts/suno-safe.sh download <clip_id> --output ./outputs --json
scripts/suno-safe.sh timed-lyrics <clip_id> --lrc > ./outputs/song.lrc
```

## Auth expiry recovery

```bash
scripts/suno-safe.sh refresh
```

If refresh fails, repeat trusted-PC Chrome CDP cookie extraction from `docs/pc-chrome-remote-debug.md`.
