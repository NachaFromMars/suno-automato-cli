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

## Managed library workflow

When the user wants generated songs managed instead of dumped into a flat output folder, use `scripts/suno-lib.sh`.

1. Create or generate into a project folder:

```bash
scripts/suno-lib.sh create --genre Rap --title "Tỉnh Thức Rap Thiền" --tags "rap, meditation"
```

2. If Suno returns/downloads two clips, import/download both as takes. The library manager names them `#1` and `#2` in metadata and stores files as `Title-Slug__01.mp3`, `Title-Slug__02.mp3`.

```bash
scripts/suno-lib.sh download <clip_id_1> <clip_id_2> --genre Rap --title "Tỉnh Thức Rap Thiền"
```

3. Use status fields for curation:

```bash
scripts/suno-lib.sh favorite --genre Rap --title "Tỉnh Thức Rap Thiền"
scripts/suno-lib.sh status published --genre Rap --title "Tỉnh Thức Rap Thiền"
```

4. For albums, create local manifests for now:

```bash
scripts/suno-lib.sh album create "Thiền Rap Vol.1" --genre Rap
```

Remote Suno album/playlist sync is pending until the upstream CLI exposes an album API.
