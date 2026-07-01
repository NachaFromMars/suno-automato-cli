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


## Suno Library Manager v0.3.0

This repo now includes a local-first library manager for generated songs:

- Intentional title + take naming: `Song Title #1`, `Song Title #2`
- ASCII-safe downloaded files: `Song-Title__01.mp3`, `Song-Title__02.mp3`
- Genre folders: Rap, Rock, Pop, Ballad, EDM, Lofi, Thien, Phat-Phap, Cinematic, Remix-Cover, Experimental, Other
- Per-project `metadata.json`, `README.md`, lyrics/cover/audio folders
- Global `suno-library/index.json`
- Local album manifests under `suno-library/_albums/` while remote Suno album API is unavailable

Commands:

```bash
./scripts/suno-lib.sh init
./scripts/suno-lib.sh create --genre Rap --title "Tỉnh Thức Rap Thiền" --tags "rap, meditation"
./scripts/suno-lib.sh import ./downloads/a.mp3 ./downloads/b.mp3 --genre Rap --title "Tỉnh Thức Rap Thiền"
./scripts/suno-lib.sh download <clip_id_1> <clip_id_2> --genre Rap --title "Tỉnh Thức Rap Thiền"
./scripts/suno-lib.sh list --genre Rap
./scripts/suno-lib.sh album create "Thiền Rap Vol.1" --genre Rap
```

See [`docs/library-manager.md`](docs/library-manager.md).

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


## Maestro Evolution v0.4.0

The batch runner now performs two audits after every successful generation:

- `scripts/suno-audit.py` checks style prompt richness: subgenre, BPM/groove, vocal identity, flow, beat/bass, instrument hooks, production/mix, emotion arc, section cues, exclude styles, and sliders.
- `scripts/suno-lyric-audit.py` checks lyric quality: structure tags, performance cues, concise hook, repeatability, syllable/rhythm consistency, singability, emotional arc, blank-line parsing, and length discipline.

Both audit streams write back into each project `metadata.json` and append lessons to `suno-library/maestro-evolution.json`, so later generations can evolve from previous weaknesses.

Docs:

- [`docs/suno-v55-maestro-prompting.md`](docs/suno-v55-maestro-prompting.md)
- [`docs/suno-v55-lyric-maestro.md`](docs/suno-v55-lyric-maestro.md)

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

## Maestro Evolution v0.5.0

New scripts:

- `scripts/suno-seed-engine.py` — generates a fresh idea seed, unique imagery, hook shape, rhyme texture, style chain, negative prompt, and sliders for every generation.
- `scripts/suno-evolution-report.py` — checks audit coverage and possible lyric/style repetition across the library.
- `scripts/suno-remote-playlist-sync.py` — syncs local album manifests to real Suno playlists via discovered Suno API endpoints.

Batch flow after v0.5.0:

1. Select album with fewer than target tracks.
2. Upgrade base job through Idea Seed Engine.
3. Generate via Suno v5.5 with dense style prompt + exclude + sliders.
4. Download and rename audio into local folder.
5. Run style audit and lyric audit.
6. Append lessons to `suno-library/maestro-evolution.json`.
7. Refresh local playlist files.
8. Sync to real Suno playlist.
9. Generate evolution report for repetition/audit coverage.

## Cover/Image capture

From v0.5.1, successful Suno generations also capture cover art when `image_url` is present in the API payload:

- saved under project `cover/`
- linked on each take as `cover_path` and `image_url`
- exported into `album.json`, `PLAYLIST.md`, and `tracks.csv`

This keeps audio + visual identity together for every generated take.
