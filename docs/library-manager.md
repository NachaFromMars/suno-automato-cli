# Suno Library Manager

Local-first organizer for Suno generations. It keeps every generated pair/take in a predictable folder, with intentional names, metadata, lyrics, covers, and a searchable `index.json`.

## Goals

- One generation request becomes one managed project/session.
- Suno's usual two outputs become stable takes: `#1`, `#2`, etc.
- Files are renamed with ASCII-safe names for servers, Telegram, and shell scripts.
- Music is grouped by broad genre folders.
- Remote Suno album/playlist sync is tracked as metadata, and remains `pending_api_or_manual` until the upstream CLI exposes an album API.

## Default library layout

```text
suno-library/
  index.json
  _albums/
    Thien-Rap-Vol-1/
      album.json
  Rap/
    2026-06-30_Tinh-Thuc-Rap-Thien/
      audio/
        Tinh-Thuc-Rap-Thien__01.mp3
        Tinh-Thuc-Rap-Thien__02.mp3
      lyrics/
      cover/
      exports/
      metadata.json
      README.md
  Rock/
  Pop/
  Ballad/
  EDM/
  Lofi/
  Thien/
  Phat-Phap/
  Cinematic/
  Remix-Cover/
  Experimental/
  Other/
```

## Genre taxonomy v0.3.0

- `Rap`
- `Rock`
- `Pop`
- `Ballad`
- `EDM`
- `Lofi`
- `Thien`
- `Phat-Phap`
- `Cinematic`
- `Remix-Cover`
- `Experimental`
- `Other`

Vietnamese labels such as `Thiền` are normalized to filesystem-safe folders like `Thien`.

## Naming convention

Human-facing title:

```text
Tỉnh Thức Rap Thiền #1
Tỉnh Thức Rap Thiền #2
```

Filesystem-safe names:

```text
Tinh-Thuc-Rap-Thien__01.mp3
Tinh-Thuc-Rap-Thien__02.mp3
```

Project folder:

```text
YYYY-MM-DD_Title-Slug
```

Example:

```text
2026-06-30_Tinh-Thuc-Rap-Thien
```

## Commands

Use the wrapper:

```bash
./scripts/suno-lib.sh <command>
```

Initialize folders:

```bash
./scripts/suno-lib.sh init
```

Create a project/session:

```bash
./scripts/suno-lib.sh create \
  --genre Rap \
  --title "Tỉnh Thức Rap Thiền" \
  --prompt "Vietnamese meditation rap about mindfulness" \
  --tags "rap, meditation, vietnamese"
```

Import downloaded files as takes:

```bash
./scripts/suno-lib.sh import ./downloads/song-a.mp3 ./downloads/song-b.mp3 \
  --genre Rap \
  --title "Tỉnh Thức Rap Thiền"
```

Download Suno clip IDs into a project and rename them as takes:

```bash
./scripts/suno-lib.sh download <clip_id_1> <clip_id_2> \
  --genre Rap \
  --title "Tỉnh Thức Rap Thiền"
```

Generate through Suno and capture returned IDs/payload:

```bash
./scripts/suno-lib.sh generate \
  --genre Rap \
  --title "Tỉnh Thức Rap Thiền" \
  --tags "rap, meditation, vietnamese" \
  --lyrics-file lyrics.txt \
  --wait \
  --download
```

List projects:

```bash
./scripts/suno-lib.sh list
./scripts/suno-lib.sh list --genre Rap
./scripts/suno-lib.sh list --json
```

Mark favorite / published / archived:

```bash
./scripts/suno-lib.sh favorite --genre Rap --title "Tỉnh Thức Rap Thiền"
./scripts/suno-lib.sh status published --genre Rap --title "Tỉnh Thức Rap Thiền"
```

Create a local album manifest:

```bash
./scripts/suno-lib.sh album create "Thiền Rap Vol.1" --genre Rap
```

Rebuild index:

```bash
./scripts/suno-lib.sh export-index
```

## Metadata schema

Each project has `metadata.json`:

```json
{
  "schema_version": "1.0",
  "title": "Tỉnh Thức Rap Thiền",
  "title_slug": "Tinh-Thuc-Rap-Thien",
  "genre": "Rap",
  "genre_input": "Rap/Thiền",
  "batch": "2026-06-30_Tinh-Thuc-Rap-Thien",
  "project_dir": ".../suno-library/Rap/2026-06-30_Tinh-Thuc-Rap-Thien",
  "prompt": "...",
  "tags": ["rap", "meditation", "vietnamese"],
  "status": "draft",
  "album": "Thiền Rap Vol.1",
  "album_id": "",
  "remote_album_sync": "pending_api_or_manual",
  "takes": [
    {
      "take_no": 1,
      "label": "#1",
      "title": "Tỉnh Thức Rap Thiền #1",
      "suno_id": "",
      "status": "draft",
      "audio_path": ".../audio/Tinh-Thuc-Rap-Thien__01.mp3",
      "imported_at": "2026-06-30T..."
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

## Album handling

Current upstream `suno-cli` v0.5.7 exposes clip generation, list/search/info/download/set/publish/delete, but no documented album/playlist create/add command. So v0.3.0 treats album management as local-first:

- local album manifest: `suno-library/_albums/<Album-Slug>/album.json`
- project-level fields: `album`, `album_id`, `remote_album_sync`
- remote sync status defaults to `pending_api_or_manual`

When upstream exposes album APIs, add a sync command that maps local album manifests to Suno remote album IDs.
