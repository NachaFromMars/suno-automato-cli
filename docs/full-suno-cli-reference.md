# Full Suno CLI Reference

Verified against local binary:

```bash
/root/.openclaw/workspace/bin/suno --version
# suno 0.5.7
```

`paperfoot/suno-cli` exposes the current full Suno automation surface below.

## Global

```bash
suno [--json] [--quiet] <command>
suno --version
suno --help
```

Use `--json` for agent parsing. Many commands auto-detect JSON when stdout is piped.

## Auth & Config

### `auth`

```bash
suno auth --login
suno auth --refresh
suno auth --cookie '<__client or Cookie header>'
suno auth --jwt '<jwt>'
suno auth --device '<device-id>'
suno auth --logout
suno auth --json
```

Notes:
- `--login` extracts from local browsers.
- Headless/VPS path: extract trusted PC Chrome Clerk `__client` cookie, then `suno auth --cookie`.
- `--refresh` refreshes JWT through stored Clerk session.

### `config`

```bash
suno config show --json
suno config set <key> <value>
suno config check --json
```

### `agent-info`

```bash
suno agent-info --json
```

Returns machine-readable capabilities, models, auth paths, features, and exit codes.

### `install-skill`

```bash
suno install-skill --target claude
suno install-skill --target cursor
suno install-skill --path ./SKILL.md --force
suno install-skill --print
```

### `update`

```bash
suno update --check --json
suno update
```

## Read-only / Safe Commands

### `credits`

```bash
suno credits --json
```

Shows plan, credits, monthly usage, model availability.

### `models`

```bash
suno models --json
```

Lists available model versions and limits.

### `list`

```bash
suno list --page 0 --json
```

Lists songs/clips in library.

### `search`

```bash
suno search "query" --json
```

Searches your songs by title or tags.

### `info`

```bash
suno info <clip_id> --json
```

Detailed clip metadata.

### `status`

```bash
suno status <clip_id_1> <clip_id_2> --json
```

Checks generation status.

### `persona`

```bash
suno persona <persona_id> --json
```

Displays voice persona details.

### `timed-lyrics`

```bash
suno timed-lyrics <clip_id> --json
suno timed-lyrics <clip_id> --lrc > song.lrc
```

Gets word-level timestamped lyrics.

## Creation Commands — Credit-Spending / Mutating

Ask for explicit user intent before these in OpenClaw.

### `lyrics` — free lyrics only

```bash
suno lyrics --prompt "Vietnamese ballad about rain and memory" --json
```

No credits used.

### `generate` — custom mode

```bash
suno generate \
  --title "Song Title" \
  --tags "Vietnamese pop ballad, cinematic, piano" \
  --exclude "metal, harsh noise" \
  --lyrics-file lyrics.txt \
  --model v5.5 \
  --vocal male \
  --weirdness 40 \
  --style-influence 65 \
  --variation normal \
  --wait \
  --download ./songs \
  --json
```

Key flags:
- `--title <TITLE>` up to 100 chars
- `--tags <TAGS>` style tags, up to 1000 chars
- `--exclude <EXCLUDE>` negative tags, up to 1000 chars
- `--lyrics <LYRICS>` or `--lyrics-file <FILE>` up to 5000 chars
- `--model v5.5|v5|v4.5+|v4.5|v4|v3.5|v3|v2`
- `--vocal male|female`
- `--weirdness 0-100`
- `--style-influence 0-100`
- `--variation high|normal|subtle`
- `--instrumental`
- `--persona <persona_id>`
- `--wait`
- `--download <dir>`
- `--token <hcaptcha_token>` / `--no-captcha`

### `describe` — prompt mode

```bash
suno describe \
  --prompt "A chill lo-fi track about rainy mornings" \
  --tags "lo-fi, warm keys, soft drums" \
  --model v5.5 \
  --wait \
  --download ./songs \
  --json
```

Suno writes lyrics from prompt.

### `extend`

```bash
suno extend <clip_id> --at 92 --lyrics-file next-part.txt --tags "same style" --wait --json
```

Continues/extends a clip from timestamp seconds.

### `concat`

```bash
suno concat <clip_id> --wait --json
```

Stitches clips into full song.

### `cover`

```bash
suno cover <clip_id> --tags "jazz, smooth piano" --model v5.5 --wait --download ./covers --json
```

Creates a cover of an existing clip.

### `remaster`

```bash
suno remaster <clip_id> --model v5.5 --wait --download ./remastered --json
```

Remasters with newer/different model.

### `stems`

```bash
suno stems <clip_id> --wait --json
```

Extracts vocals/instruments.

## Manage / Mutating Commands

### `download`

```bash
suno download <clip_id_1> <clip_id_2> --output ./songs --json
suno download <clip_id> --output ./videos --video --json
```

Downloads MP3 by default or video with `--video`. MP3 downloads embed lyrics metadata.

### `set`

```bash
suno set <clip_id> --title "New Title" --json
suno set <clip_id> --lyrics-file updated.txt --json
suno set <clip_id> --caption "New caption" --json
suno set <clip_id> --remove-cover --json
```

Updates clip metadata.

### `publish`

```bash
suno publish <clip_id> --json
suno publish <clip_id> --private --json
```

Toggles public/private visibility.

### `delete`

```bash
suno delete <clip_id> --yes --json
```

Deletes/trashes clips. Treat as destructive.

## Models

Generation models:

| Version | Codename | Notes |
|---|---|---|
| v5.5 | chirp-fenix | default/latest |
| v5 | chirp-crow | previous generation |
| v4.5+ | chirp-bluejay | extended capabilities |
| v4.5 | chirp-auk | stable |
| v4 | chirp-v4 | legacy |
| v3.5/v3/v2 | legacy | available where account supports |

Remaster models:

| Version | Codename |
|---|---|
| v5.5 | chirp-flounder |
| v5 | chirp-carp |
| v4.5+ | chirp-bass |

## Agent Policy

Safe by default:
- `credits`
- `models`
- `list`
- `search`
- `info`
- `status`
- `persona`
- `timed-lyrics`
- `auth --refresh`

Ask/confirm first:
- `generate`
- `describe`
- `extend`
- `concat`
- `cover`
- `remaster`
- `stems`
- `publish`
- `set`
- `delete`

Can run without credits:
- `lyrics`

Destructive:
- `delete`
- `set --remove-cover`
- `publish --private` if changing existing public distribution

## Exit Codes

From `agent-info`:

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | transient error; retry later |
| 2 | configuration error |
| 3 | auth error; refresh or re-auth |
| 4 | rate limited; wait |
| 5 | not found; verify resource ID |
