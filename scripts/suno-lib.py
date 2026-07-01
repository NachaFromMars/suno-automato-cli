#!/usr/bin/env python3
"""Suno Library Manager.

Local-first music library organizer for Suno generations.
Creates genre folders, stable take names (#1/#2), metadata, lyrics, and indexes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import urllib.request
import urllib.parse
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = REPO_ROOT / "suno-library"
DEFAULT_SUNO_BIN = REPO_ROOT / "scripts" / "suno-safe.sh"

GENRE_ALIASES = {
    "rap": "Rap",
    "hiphop": "Rap",
    "hip-hop": "Rap",
    "rock": "Rock",
    "pop": "Pop",
    "ballad": "Ballad",
    "edm": "EDM",
    "electronic": "EDM",
    "lofi": "Lofi",
    "lo-fi": "Lofi",
    "thien": "Thien",
    "thiền": "Thien",
    "meditation": "Thien",
    "ambient": "Thien",
    "mantra": "Thien",
    "phat-phap": "Phat-Phap",
    "phật pháp": "Phat-Phap",
    "buddhist": "Phat-Phap",
    "cinematic": "Cinematic",
    "epic": "Cinematic",
    "remix": "Remix-Cover",
    "cover": "Remix-Cover",
    "experimental": "Experimental",
    "other": "Other",
}
DEFAULT_GENRES = [
    "Rap", "Rock", "Pop", "Ballad", "EDM", "Lofi", "Thien", "Phat-Phap",
    "Cinematic", "Remix-Cover", "Experimental", "Other",
]

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
LYRIC_EXTS = {".txt", ".lrc"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def strip_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def slugify(text: str, fallback: str = "untitled") -> str:
    ascii_text = strip_diacritics(text)
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-")
    ascii_text = re.sub(r"-+", "-", ascii_text)
    return ascii_text or fallback


def normalize_genre(genre: str) -> str:
    key = genre.strip().lower()
    key_slug = slugify(key).lower()
    if key in GENRE_ALIASES:
        return GENRE_ALIASES[key]
    if key_slug in GENRE_ALIASES:
        return GENRE_ALIASES[key_slug]
    # Preserve custom genre, but make filesystem-safe.
    return slugify(genre, "Other")


def library_root(args: argparse.Namespace) -> Path:
    return Path(args.library_root or os.environ.get("SUNO_LIBRARY_ROOT") or DEFAULT_LIBRARY_ROOT).expanduser().resolve()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def ensure_taxonomy(root: Path) -> None:
    for genre in DEFAULT_GENRES:
        (root / genre).mkdir(parents=True, exist_ok=True)


def project_dir(root: Path, genre: str, title: str, date: str | None = None, slug: str | None = None) -> Path:
    genre_name = normalize_genre(genre)
    date_part = date or datetime.now().strftime("%Y-%m-%d")
    title_slug = slug or slugify(title)
    return root / genre_name / f"{date_part}_{title_slug}"


def create_project(args: argparse.Namespace) -> Path:
    root = library_root(args)
    ensure_taxonomy(root)
    pdir = project_dir(root, args.genre, args.title, args.date, args.slug)
    for sub in ("audio", "lyrics", "cover", "exports"):
        (pdir / sub).mkdir(parents=True, exist_ok=True)

    metadata = read_json(pdir / "metadata.json", {})
    metadata.update({
        "schema_version": "1.0",
        "title": args.title,
        "title_slug": slugify(args.title),
        "genre": normalize_genre(args.genre),
        "genre_input": args.genre,
        "batch": pdir.name,
        "project_dir": str(pdir),
        "prompt": args.prompt or metadata.get("prompt", ""),
        "style_prompt": args.tags or metadata.get("style_prompt", ""),
        "exclude": getattr(args, "exclude", "") or metadata.get("exclude", ""),
        "weirdness": getattr(args, "weirdness", None) if getattr(args, "weirdness", None) is not None else metadata.get("weirdness"),
        "style_influence": getattr(args, "style_influence", None) if getattr(args, "style_influence", None) is not None else metadata.get("style_influence"),
        "tags": split_csv(args.tags) if args.tags else metadata.get("tags", []),
        "status": args.status or metadata.get("status", "draft"),
        "album": args.album or metadata.get("album", ""),
        "album_id": args.album_id or metadata.get("album_id", ""),
        "takes": metadata.get("takes", []),
        "created_at": metadata.get("created_at", now_iso()),
        "updated_at": now_iso(),
        "remote_album_sync": metadata.get("remote_album_sync", "pending_api_or_manual"),
    })
    write_json(pdir / "metadata.json", metadata)

    readme = pdir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {args.title}\n\n"
            f"- Genre: {metadata['genre']}\n"
            f"- Batch: `{pdir.name}`\n"
            f"- Status: {metadata['status']}\n"
            f"- Album: {metadata.get('album') or '—'}\n\n"
            "## Takes\n\n"
            "Generated takes are stored in `audio/` as `Title__01.ext`, `Title__02.ext`, ...\n",
            encoding="utf-8",
        )
    update_index(root)
    print(str(pdir))
    return pdir


def split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def next_take_no(metadata: dict[str, Any]) -> int:
    nums = []
    for take in metadata.get("takes", []):
        try:
            nums.append(int(take.get("take_no", 0)))
        except Exception:
            pass
    return (max(nums) + 1) if nums else 1


def copy_or_move(src: Path, dst: Path, move: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {dst}")
    if move:
        shutil.move(str(src), str(dst))
    else:
        shutil.copy2(src, dst)


def import_files(args: argparse.Namespace) -> Path:
    root = library_root(args)
    pdir = resolve_project(root, args)
    metadata_path = pdir / "metadata.json"
    metadata = read_json(metadata_path, None)
    if metadata is None:
        raise SystemExit(f"metadata.json not found: {metadata_path}")

    title_slug = metadata.get("title_slug") or slugify(metadata.get("title", args.title or "Untitled"))
    take_no = args.take_no or next_take_no(metadata)
    imported: dict[str, str] = {}

    for raw in args.files:
        src = Path(raw).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"File not found: {src}")
        ext = src.suffix.lower()
        base = f"{title_slug}__{take_no:02d}{ext}"
        if ext in AUDIO_EXTS:
            dst = pdir / "audio" / base
            imported["audio_path"] = str(dst)
        elif ext in IMAGE_EXTS:
            dst = pdir / "cover" / base
            imported.setdefault("cover_path", str(dst))
        elif ext in LYRIC_EXTS:
            dst = pdir / "lyrics" / base
            imported.setdefault("lyrics_path", str(dst))
        else:
            dst = pdir / "exports" / base
            imported.setdefault("extra_path", str(dst))
        copy_or_move(src, dst, args.move)

    take = {
        "take_no": take_no,
        "label": f"#{take_no}",
        "title": f"{metadata.get('title', args.title or title_slug)} #{take_no}",
        "suno_id": args.suno_id or "",
        "status": args.status or "draft",
        "imported_at": now_iso(),
        **imported,
    }
    metadata.setdefault("takes", []).append(take)
    metadata["updated_at"] = now_iso()
    write_json(metadata_path, metadata)
    update_index(root)
    print(json.dumps(take, ensure_ascii=False, indent=2))
    return pdir


def resolve_project(root: Path, args: argparse.Namespace) -> Path:
    if getattr(args, "project", None):
        p = Path(args.project).expanduser()
        return p.resolve() if p.is_absolute() else (root / p).resolve()
    if getattr(args, "title", None) and getattr(args, "genre", None):
        candidates = sorted((root / normalize_genre(args.genre)).glob(f"*_{slugify(args.title)}"))
        if candidates:
            return candidates[-1]
        return project_dir(root, args.genre, args.title, args.date, args.slug)
    raise SystemExit("Provide --project or both --genre and --title")


def update_index(root: Path) -> None:
    ensure_taxonomy(root)
    projects: list[dict[str, Any]] = []
    for meta_path in root.glob("*/*/metadata.json"):
        meta = read_json(meta_path, {})
        projects.append({
            "title": meta.get("title", ""),
            "genre": meta.get("genre", meta_path.parents[1].name),
            "batch": meta.get("batch", meta_path.parent.name),
            "status": meta.get("status", ""),
            "album": meta.get("album", ""),
            "take_count": len(meta.get("takes", [])),
            "project_dir": str(meta_path.parent),
            "updated_at": meta.get("updated_at", ""),
        })
    projects.sort(key=lambda x: (x.get("updated_at") or "", x.get("batch") or ""), reverse=True)
    write_json(root / "index.json", {"schema_version": "1.0", "updated_at": now_iso(), "projects": projects})


def list_projects(args: argparse.Namespace) -> None:
    root = library_root(args)
    update_index(root)
    index = read_json(root / "index.json", {"projects": []})
    genre = normalize_genre(args.genre) if args.genre else None
    rows = [p for p in index["projects"] if not genre or p.get("genre") == genre]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for p in rows:
        print(f"{p['genre']}/{p['batch']}  takes={p['take_count']}  status={p['status']}  title={p['title']}")


def set_status(args: argparse.Namespace) -> None:
    root = library_root(args)
    pdir = resolve_project(root, args)
    meta_path = pdir / "metadata.json"
    meta = read_json(meta_path, None)
    if meta is None:
        raise SystemExit(f"metadata.json not found: {meta_path}")
    meta["status"] = args.status
    meta["updated_at"] = now_iso()
    write_json(meta_path, meta)
    update_index(root)
    print(f"{pdir}: status={args.status}")


def run_suno(args_list: list[str]) -> dict[str, Any] | list[Any] | None:
    cmd = [str(DEFAULT_SUNO_BIN), *args_list, "--json"]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print(out)
        return None


def extract_ids(payload: Any) -> list[str]:
    def walk(x: Any) -> Iterable[str]:
        if isinstance(x, dict):
            if isinstance(x.get("id"), str):
                yield x["id"]
            if isinstance(x.get("clip_id"), str):
                yield x["clip_id"]
            for v in x.values():
                yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)
    seen: list[str] = []
    for item in walk(payload):
        if item not in seen:
            seen.append(item)
    return seen


def extract_clip_media(payload: Any) -> dict[str, dict[str, str]]:
    """Return {clip_id: {image_url, audio_url, title}} from Suno JSON payload."""
    clips: dict[str, dict[str, str]] = {}
    def walk(x: Any):
        if isinstance(x, dict):
            cid = x.get("id") or x.get("clip_id")
            if isinstance(cid, str):
                info = clips.setdefault(cid, {})
                for key in ("image_url", "audio_url", "video_url", "title"):
                    val = x.get(key)
                    if isinstance(val, str) and val:
                        info[key] = val
                meta = x.get("metadata")
                if isinstance(meta, dict):
                    for key in ("image_url", "audio_url", "title"):
                        val = meta.get(key)
                        if isinstance(val, str) and val:
                            info.setdefault(key, val)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return clips

def download_url(url: str, dst: Path) -> bool:
    if not url:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, dst.open("wb") as f:
            shutil.copyfileobj(r, f)
        return dst.exists() and dst.stat().st_size > 0
    except Exception as e:
        print(f"cover download failed: {url}: {e}", file=sys.stderr)
        return False

def create_and_generate(args: argparse.Namespace) -> None:
    pdir = create_project(args)
    lyrics_file = Path(args.lyrics_file).expanduser().resolve() if args.lyrics_file else None
    cmd = ["generate", "--title", args.title, "--tags", args.tags or args.genre, "--model", args.model]
    if getattr(args, "exclude", ""):
        cmd += ["--exclude", args.exclude]
    if getattr(args, "weirdness", None) is not None:
        cmd += ["--weirdness", str(args.weirdness)]
    if getattr(args, "style_influence", None) is not None:
        cmd += ["--style-influence", str(args.style_influence)]
    if getattr(args, "instrumental", False):
        cmd.append("--instrumental")
    if lyrics_file:
        cmd += ["--lyrics-file", str(lyrics_file)]
    elif args.lyrics:
        lyric_path = pdir / "lyrics" / f"{slugify(args.title)}__source.txt"
        lyric_path.write_text(args.lyrics, encoding="utf-8")
        cmd += ["--lyrics-file", str(lyric_path)]
    if args.wait:
        cmd.append("--wait")
    download_tmp = None
    if args.download:
        download_tmp = pdir / "exports" / f"generate-download-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        download_tmp.mkdir(parents=True, exist_ok=True)
        cmd += ["--download", str(download_tmp)]
    payload = run_suno(cmd)
    meta_path = pdir / "metadata.json"
    meta = read_json(meta_path, {})
    meta["last_generate_payload"] = payload
    ids = extract_ids(payload)
    clip_media = extract_clip_media(payload)
    if ids:
        meta["suno_ids"] = list(dict.fromkeys([*meta.get("suno_ids", []), *ids]))
    if clip_media:
        meta["clip_media"] = {**meta.get("clip_media", {}), **clip_media}
    meta["updated_at"] = now_iso()
    write_json(meta_path, meta)

    imported_files = []
    if download_tmp and download_tmp.exists():
        audio_files = sorted([x for x in download_tmp.iterdir() if x.suffix.lower() in AUDIO_EXTS])
        for idx, audio in enumerate(audio_files, start=next_take_no(read_json(meta_path, {}))):
            ns = argparse.Namespace(**vars(args))
            ns.files = [str(audio)]
            ns.project = str(pdir)
            ns.take_no = idx
            ns.suno_id = ids[idx - 1] if idx - 1 < len(ids) else ""
            ns.move = True
            ns.status = "draft"
            import_files(ns)
            # Download Suno cover/image for this take when available.
            cid = ns.suno_id
            media = clip_media.get(cid, {}) if cid else {}
            cover_path = ""
            if media.get("image_url"):
                ext = Path(urllib.parse.urlparse(media["image_url"]).path).suffix.lower() or ".jpg"
                if ext not in IMAGE_EXTS:
                    ext = ".jpg"
                dst = pdir / "cover" / f"{slugify(args.title)}__{idx:02d}{ext}"
                if download_url(media["image_url"], dst):
                    cover_path = str(dst)
                    latest_meta = read_json(meta_path, {})
                    for take in latest_meta.get("takes", []):
                        if take.get("take_no") == idx:
                            take["cover_path"] = cover_path
                            take["image_url"] = media.get("image_url", "")
                    write_json(meta_path, latest_meta)
            imported_files.append(str(pdir / "audio" / f"{slugify(args.title)}__{idx:02d}{audio.suffix.lower()}"))
    update_index(library_root(args))
    print(json.dumps({"project_dir": str(pdir), "suno_ids": ids, "imported_files": imported_files}, ensure_ascii=False, indent=2))


def download_ids(args: argparse.Namespace) -> None:
    root = library_root(args)
    pdir = resolve_project(root, args)
    tmp = pdir / "exports" / f"download-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    tmp.mkdir(parents=True, exist_ok=True)
    run_suno(["download", *args.suno_ids, "--output", str(tmp)])
    audio_files = sorted([p for p in tmp.iterdir() if p.suffix.lower() in AUDIO_EXTS])
    if not audio_files:
        print(f"No audio files found in {tmp}", file=sys.stderr)
        return
    for i, file in enumerate(audio_files, start=args.start_take):
        ns = argparse.Namespace(**vars(args))
        ns.files = [str(file)]
        ns.take_no = i
        ns.suno_id = args.suno_ids[i - args.start_take] if i - args.start_take < len(args.suno_ids) else ""
        ns.move = True
        import_files(ns)


def main() -> None:
    parser = argparse.ArgumentParser(description="Suno Library Manager")
    parser.add_argument("--library-root", default=None, help="Library root (default: ./suno-library)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create library taxonomy folders")
    p.set_defaults(func=lambda a: (ensure_taxonomy(library_root(a)), update_index(library_root(a)), print(library_root(a))))

    p = sub.add_parser("create", help="Create a local Suno project")
    p.add_argument("--genre", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--prompt", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--album", default="")
    p.add_argument("--album-id", default="")
    p.add_argument("--exclude", default="")
    p.add_argument("--weirdness", type=int, default=None)
    p.add_argument("--style-influence", type=int, default=None)
    p.add_argument("--status", default="draft")
    p.add_argument("--date", default=None)
    p.add_argument("--slug", default=None)
    p.set_defaults(func=create_project)

    p = sub.add_parser("import", help="Import audio/lyrics/cover files as a take")
    p.add_argument("files", nargs="+")
    p.add_argument("--project", default=None)
    p.add_argument("--genre", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--take-no", type=int, default=None)
    p.add_argument("--suno-id", default="")
    p.add_argument("--status", default="draft")
    p.add_argument("--move", action="store_true")
    p.set_defaults(func=import_files)

    p = sub.add_parser("list", help="List library projects")
    p.add_argument("--genre", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=list_projects)

    p = sub.add_parser("favorite", help="Mark a project favorite")
    p.add_argument("--project", default=None)
    p.add_argument("--genre", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--slug", default=None)
    p.set_defaults(status="favorite", func=set_status)

    p = sub.add_parser("status", help="Set project status")
    p.add_argument("status", choices=["draft", "favorite", "published", "archived"])
    p.add_argument("--project", default=None)
    p.add_argument("--genre", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--slug", default=None)
    p.set_defaults(func=set_status)

    p = sub.add_parser("export-index", help="Rebuild index.json")
    p.set_defaults(func=lambda a: (update_index(library_root(a)), print(library_root(a) / "index.json")))

    p = sub.add_parser("album", help="Local album helpers. Remote Suno album sync is marked pending until API exists.")
    album_sub = p.add_subparsers(dest="album_command", required=True)
    ap = album_sub.add_parser("create", help="Create a local album manifest")
    ap.add_argument("name")
    ap.add_argument("--genre", default="Other")
    ap.add_argument("--description", default="")
    def album_create(a):
        root = library_root(a)
        ensure_taxonomy(root)
        album_dir = root / "_albums" / slugify(a.name)
        album_dir.mkdir(parents=True, exist_ok=True)
        manifest = read_json(album_dir / "album.json", {})
        manifest.update({
            "schema_version": "1.0",
            "name": a.name,
            "slug": slugify(a.name),
            "genre": normalize_genre(a.genre),
            "description": a.description,
            "projects": manifest.get("projects", []),
            "remote_album_sync": "pending_api_or_manual",
            "created_at": manifest.get("created_at", now_iso()),
            "updated_at": now_iso(),
        })
        write_json(album_dir / "album.json", manifest)
        print(album_dir)
    ap.set_defaults(func=album_create)

    p = sub.add_parser("generate", help="Create project, call Suno generate, and capture metadata")
    p.add_argument("--genre", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--prompt", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--lyrics-file", default=None)
    p.add_argument("--lyrics", default=None)
    p.add_argument("--album", default="")
    p.add_argument("--album-id", default="")
    p.add_argument("--exclude", default="")
    p.add_argument("--weirdness", type=int, default=None)
    p.add_argument("--style-influence", type=int, default=None)
    p.add_argument("--status", default="draft")
    p.add_argument("--date", default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--model", default="v5.5")
    p.add_argument("--wait", action="store_true")
    p.add_argument("--download", action="store_true")
    p.add_argument("--instrumental", action="store_true")
    p.set_defaults(func=create_and_generate)

    p = sub.add_parser("download", help="Download Suno IDs into a project and rename as takes")
    p.add_argument("suno_ids", nargs="+")
    p.add_argument("--project", default=None)
    p.add_argument("--genre", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--start-take", type=int, default=1)
    p.set_defaults(func=download_ids)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
