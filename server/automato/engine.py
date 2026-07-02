"""Service layer — the single gated chokepoint for everything (REST, UI, MCP).

All generation goes through submit_job() which runs guard_gate() first (F-10).
Guards call the REAL suno_prompt_guard.py — same code path as the CLI runner,
so the dashboard preview can never drift from the actual gate.
"""
from __future__ import annotations

import fcntl
import glob as _glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config
from .db import get_db

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return re.sub(r"-+", "-", text) or "untitled"


def _run(cmd: list[str], timeout: int = config.GUARD_TIMEOUT, env: dict | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            [str(c) for c in cmd], cwd=str(config.REPO_ROOT), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env or dict(os.environ), timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or ""), ((e.stderr or "") + f"\nTIMEOUT after {timeout}s")
    except FileNotFoundError as e:
        return 127, "", str(e)


def _parse_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        # take last JSON-looking line
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except Exception:
                    continue
    return None


# --------------------------------------------------------------------------
# Guard gate (real suno_prompt_guard.py checks)
# --------------------------------------------------------------------------

def guard_gate(*, title: str, genre: str, album: str, style: str, lyrics: str,
               instrumental: bool = False) -> tuple[bool, dict]:
    """Run the full strict gate. Returns (passed, per-gate report).

    Gates: precheck (11-block + production density), lyrics-check (instrumental-aware),
    playlist-route (manifest + genre validation), novelty-check (vs novelty-history.json).
    """
    pg = str(config.PROMPT_GUARD)
    report: dict[str, Any] = {
        "at": now_iso(),
        "title": title, "genre": genre, "album": album,
        "instrumental": instrumental,
        "style_len": len(style),
        "gates": {},
    }
    passed_all = True

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(lyrics or "")
        lyric_path = fh.name
    try:
        lyrics_cmd = ["python3", pg, "lyrics-check", "--file", lyric_path, "--title", title]
        if instrumental or genre in config.INSTRUMENTAL_GENRES:
            lyrics_cmd.append("--instrumental")

        threshold = (config.NOVELTY_THRESHOLD_INSTRUMENTAL
                     if (instrumental or genre in config.INSTRUMENTAL_GENRES)
                     else config.NOVELTY_THRESHOLD_VOCAL)

        checks = [
            ("precheck", ["python3", pg, "precheck", "--text", style]),
            ("lyrics_check", lyrics_cmd),
            ("playlist_route", ["python3", pg, "playlist-route", "--title", title, "--text", style,
                                "--playlist", album, "--albums-root", str(config.ALBUMS_ROOT),
                                "--expect-genre", genre]),
            ("novelty_check", ["python3", pg, "novelty-check", "--title", title, "--style", style,
                               "--lyrics-file", lyric_path, "--history", str(config.NOVELTY_HISTORY),
                               "--threshold", threshold]),
        ]
        for name, cmd in checks:
            code, out, err = _run(cmd)
            detail = _parse_json(out)
            gate = {"passed": code == 0, "exit_code": code, "detail": detail}
            if err.strip():
                gate["stderr"] = err.strip()[-800:]
            report["gates"][name] = gate
            if code != 0:
                passed_all = False
    finally:
        try:
            os.unlink(lyric_path)
        except OSError:
            pass

    report["passed"] = passed_all
    return passed_all, report


def precheck_blocks(style: str) -> dict:
    """Per-block presence map for the 11 required PromptStyle blocks (for the UI checklist)."""
    blocks = ["Leading Genre DNA", "Singer Identity", "Vocal Register", "Rhythm Section",
              "Signature Motif", "Hook Design", "Arrangement Map", "Instrument Palette",
              "Mood Logic", "Mix Target", "Strictly Avoid"]
    low = (style or "").lower().replace("đ", "d")
    return {b: b.lower() in low for b in blocks}


# --------------------------------------------------------------------------
# Library scanner (metadata.json files are source of truth)
# --------------------------------------------------------------------------

def scan_projects(*, genre: str | None = None, album: str | None = None,
                  q: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    projects = []
    for meta_path in sorted(config.LIBRARY_ROOT.glob("*/*/metadata.json")):
        if meta_path.parts[-3].startswith("_"):
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if genre and meta.get("genre") != genre:
            continue
        if album and meta.get("album") != album:
            continue
        if q:
            hay = " ".join([meta.get("title", ""), meta.get("album", ""),
                            meta.get("genre", ""), meta.get("style_prompt", "")]).lower()
            if q.lower() not in hay:
                continue
        takes = meta.get("takes", []) or []
        projects.append({
            "project_id": f"{meta_path.parts[-3]}/{meta_path.parts[-2]}",
            "title": meta.get("title", ""),
            "genre": meta.get("genre", ""),
            "album": meta.get("album", ""),
            "status": meta.get("status", ""),
            "take_count": len(takes),
            "quarantined_count": len(meta.get("quarantined_takes", []) or []),
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
            "cover": next((t.get("cover_path") for t in takes if t.get("cover_path")), None),
        })
    projects.sort(key=lambda p: p.get("updated_at") or "", reverse=True)
    total = len(projects)
    return {"total": total, "limit": limit, "offset": offset,
            "projects": projects[offset:offset + limit]}


def get_project(project_id: str) -> dict | None:
    """project_id = '<Genre>/<batch-dir>' relative to library root."""
    parts = project_id.strip("/").split("/")
    if len(parts) != 2 or parts[0].startswith("_") or ".." in project_id:
        return None
    meta_path = config.LIBRARY_ROOT / parts[0] / parts[1] / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    takes = []
    for t in meta.get("takes", []) or []:
        audio = t.get("audio_path") or ""
        takes.append({
            "take_no": t.get("take_no"),
            "title": t.get("title") or f"{meta.get('title','')} #{t.get('take_no')}",
            "suno_id": t.get("suno_id", ""),
            "status": t.get("status", ""),
            "audio_file": Path(audio).name if audio else None,
            "audio_exists": bool(audio) and Path(audio).exists(),
            "cover_file": Path(t["cover_path"]).name if t.get("cover_path") else None,
        })
    return {
        "project_id": project_id,
        "title": meta.get("title", ""),
        "genre": meta.get("genre", ""),
        "album": meta.get("album", ""),
        "status": meta.get("status", ""),
        "style_prompt": meta.get("style_prompt", ""),
        "exclude": meta.get("exclude", ""),
        "weirdness": meta.get("weirdness"),
        "style_influence": meta.get("style_influence"),
        "tags": meta.get("tags", []),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("updated_at", ""),
        "takes": takes,
        "quarantined_takes": meta.get("quarantined_takes", []),
        "suno_ids": meta.get("suno_ids", []),
    }


def resolve_media(project_id: str, filename: str, kind: str = "audio") -> Path | None:
    """Safe path resolution for streaming. kind: audio|cover."""
    parts = project_id.strip("/").split("/")
    if len(parts) != 2 or ".." in project_id or ".." in filename or "/" in filename:
        return None
    base = (config.LIBRARY_ROOT / parts[0] / parts[1] / kind).resolve()
    if not str(base).startswith(str(config.LIBRARY_ROOT.resolve())):
        return None
    p = base / filename
    return p if p.exists() and p.is_file() else None


# --------------------------------------------------------------------------
# Albums / playlists
# --------------------------------------------------------------------------

def list_albums() -> list[dict]:
    albums = []
    if not config.ALBUMS_ROOT.exists():
        return albums
    for d in sorted(config.ALBUMS_ROOT.iterdir()):
        m = d / "album.json"
        if not m.exists():
            continue
        try:
            manifest = json.loads(m.read_text(encoding="utf-8"))
        except Exception:
            continue
        albums.append({
            "slug": manifest.get("slug", d.name),
            "name": manifest.get("name", d.name),
            "genre": manifest.get("genre", ""),
            "track_count": manifest.get("track_count", len(manifest.get("tracks", []) or [])),
            "target": 8,
            "remote_playlist_id": manifest.get("remote_playlist_id", ""),
            "remote_album_sync": manifest.get("remote_album_sync", ""),
            "remote_synced_at": manifest.get("remote_synced_at", ""),
            "updated_at": manifest.get("updated_at", ""),
        })
    return albums


def get_album(slug: str) -> dict | None:
    if ".." in slug or "/" in slug:
        return None
    m = config.ALBUMS_ROOT / slug / "album.json"
    if not m.exists():
        return None
    try:
        manifest = json.loads(m.read_text(encoding="utf-8"))
    except Exception:
        return None
    return manifest


# --------------------------------------------------------------------------
# Status probes
# --------------------------------------------------------------------------

def probe_credits() -> dict:
    code, out, err = _run([str(config.SUNO_BIN), "credits", "--json"], timeout=config.PROBE_TIMEOUT)
    data = _parse_json(out)
    if code == 0 and isinstance(data, dict):
        d = data.get("data", {})
        return {"ok": True, "credits": d.get("credits"), "total_credits_left": d.get("total_credits_left"),
                "monthly_usage": d.get("monthly_usage"), "monthly_limit": d.get("monthly_limit"),
                "plan": (d.get("plan") or {}).get("name"), "renews_on": d.get("renews_on")}
    return {"ok": False, "error": (err or out or "credits probe failed").strip()[-300:]}


def probe_xvfb() -> dict:
    display = os.environ.get("DISPLAY") or ":99"
    env = dict(os.environ, DISPLAY=display)
    code, _, _ = _run(["xdpyinfo"], timeout=10, env=env)
    if code != 0 and env.pop("XAUTHORITY", None):
        # host default: bare Xvfb :99 without an auth file
        code, _, _ = _run(["xdpyinfo"], timeout=10, env=env)
    return {"display": display, "alive": code == 0}


def lock_held() -> bool:
    """Is the shared generation lock currently held (CLI runner or our worker)?"""
    try:
        fh = open(config.LOCK_FILE, "a+")
    except OSError:
        return False
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fh, fcntl.LOCK_UN)
        return False
    except (BlockingIOError, OSError):
        return True
    finally:
        fh.close()


def status_summary(worker_alive: bool = False, include_credits: bool = True) -> dict:
    db = get_db()
    return {
        "at": now_iso(),
        "auth_credits": probe_credits() if include_credits else {"ok": None, "skipped": True},
        "xvfb": probe_xvfb(),
        "worker_alive": worker_alive,
        "generation_lock_held": lock_held(),
        "queue_depth": db.queue_depth(),
        "jobs_today": db.jobs_today(),
        "max_generations_per_day": config.MAX_GENERATIONS_PER_DAY,
        "guard_stats": db.guard_stats(),
    }


def novelty_history(limit: int = 30, offset: int = 0) -> dict:
    rows: list = []
    if config.NOVELTY_HISTORY.exists():
        try:
            data = json.loads(config.NOVELTY_HISTORY.read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else data.get("runs", [])
        except Exception:
            rows = []
    total = len(rows)
    window = list(reversed(rows))[offset:offset + limit]
    slim = [{"title": r.get("title"), "genre": r.get("genre"), "album": r.get("album"),
             "created_at": r.get("created_at"), "ids": r.get("ids", []),
             "style_excerpt": (r.get("style") or "")[:180]} for r in window]
    return {"total": total, "limit": limit, "offset": offset, "entries": slim}


# --------------------------------------------------------------------------
# Gated submission chokepoint (F-10)
# --------------------------------------------------------------------------

def submit_job(*, source: str, title: str, genre: str, album: str, style: str,
               lyrics: str, exclude: str = "", weirdness: int | None = None,
               style_influence: int | None = None, instrumental: bool = False) -> dict:
    """THE single generation entry point. Gate first; only PASS reaches the queue."""
    db = get_db()

    if db.jobs_today() >= config.MAX_GENERATIONS_PER_DAY:
        return {"accepted": False, "reason": "daily_generation_cap_reached",
                "jobs_today": db.jobs_today(), "cap": config.MAX_GENERATIONS_PER_DAY}

    passed, report = guard_gate(title=title, genre=genre, album=album, style=style,
                                lyrics=lyrics, instrumental=instrumental)
    if not passed:
        db.record_guard_run(source=f"{source}:gate", passed=False, report=report,
                            title=title, genre=genre, album=album)
        return {"accepted": False, "reason": "guard_blocked", "guard_report": report}

    jid = db.create_job(source=source, title=title, genre=genre, album=album, style=style,
                        lyrics=lyrics, exclude=exclude, weirdness=weirdness,
                        style_influence=style_influence, instrumental=instrumental,
                        guard_report=report)
    db.record_guard_run(source=f"{source}:gate", passed=True, report=report, job_id=jid,
                        title=title, genre=genre, album=album)
    return {"accepted": True, "job_id": jid, "guard_report": report}


def cancel_job(jid: str) -> dict:
    db = get_db()
    job = db.get_job(jid)
    if not job:
        return {"ok": False, "error": "not_found"}
    if job["status"] != "queued":
        return {"ok": False, "error": f"cannot cancel job in status '{job['status']}'"}
    db.update_job(jid, status="cancelled", progress="cancelled by user")
    return {"ok": True, "job_id": jid, "status": "cancelled"}


# --------------------------------------------------------------------------
# Generation execution (called by worker; assumes flock already held)
# --------------------------------------------------------------------------

def _display_env() -> dict:
    env = dict(os.environ)
    # F-10: engine.execute_job only runs jobs that already passed guard_gate();
    # mark the call so suno-lib.sh accepts 'generate' without --force-ungated.
    env["AUTOMATO_GATED"] = "1"
    env.setdefault("CHROME_PATH", str(config.CHROME_WRAPPER))
    env.setdefault("SUNO_CHROME_PATH", str(config.CHROME_WRAPPER))
    env.setdefault("CHROME_FLAGS", "--no-sandbox --disable-dev-shm-usage --disable-gpu --no-zygote")
    env.setdefault("SUNO_CHROME_FLAGS", "--no-sandbox --disable-dev-shm-usage --disable-gpu --no-zygote")
    if not env.get("DISPLAY"):
        # prefer bare :99 (validated), else newest xvfb-run auth pair
        probe = dict(env, DISPLAY=":99")
        probe.pop("XAUTHORITY", None)
        try:
            if subprocess.run(["xdpyinfo"], capture_output=True, timeout=10, env=probe).returncode == 0:
                env["DISPLAY"] = ":99"
                env.pop("XAUTHORITY", None)
                return env
        except Exception:
            pass
        for auth in sorted(_glob.glob("/tmp/xvfb-run.*/Xauthority"), key=os.path.getmtime, reverse=True)[:5]:
            try:
                out = subprocess.run(["xauth", "-f", auth, "list"], capture_output=True,
                                     text=True, timeout=10).stdout
                for line in out.splitlines():
                    host = line.split()[0] if line.split() else ""
                    if ":" not in host:
                        continue
                    disp = ":" + host.rsplit(":", 1)[1]
                    p = dict(env, DISPLAY=disp, XAUTHORITY=auth)
                    if subprocess.run(["xdpyinfo"], capture_output=True, timeout=10, env=p).returncode == 0:
                        env["DISPLAY"] = disp
                        env["XAUTHORITY"] = auth
                        return env
            except Exception:
                continue
        env["DISPLAY"] = ":99"
    return env


def execute_job(job: dict) -> dict:
    """Run one gated generation through the real suno-lib path. Returns final job fields.

    F-07: if the run succeeds but clip ids cannot be verified from BOTH stdout and
    metadata.json → status needs-review, never silently 'succeeded'.
    """
    db = get_db()
    jid = job["id"]
    config.LYRICS_DIR.mkdir(parents=True, exist_ok=True)
    lyric_path = config.LYRICS_DIR / f"server_{jid}_{slugify(job['title'])[:60]}.txt"
    lyric_path.write_text(job["lyrics"], encoding="utf-8")

    cmd = [str(config.SUNO_LIB), "generate",
           "--genre", job["genre"], "--title", job["title"], "--tags", job["style"],
           "--exclude", job.get("exclude") or "generic stock loop, karaoke backing track, muddy mix, weak hook",
           "--weirdness", str(job.get("weirdness") or 62),
           "--style-influence", str(job.get("style_influence") or 86),
           "--lyrics-file", str(lyric_path),
           "--album", job["album"], "--wait", "--download"]
    if job.get("instrumental"):
        cmd.append("--instrumental")

    db.update_job(jid, status="running", progress="generation started (suno-lib generate)")
    code, out, err = _run(cmd, timeout=config.GENERATE_TIMEOUT, env=_display_env())

    result: dict[str, Any] = {"exit_code": code, "stdout_tail": out[-3000:], "stderr_tail": err[-2000:]}
    if code != 0:
        return {"status": "failed", "result": result,
                "error": f"generation failed rc={code}: {(err or out).strip()[-400:]}"}

    # Clip id extraction: stdout regex + metadata.json cross-check (F-07)
    ids_stdout = list(dict.fromkeys(UUID_RE.findall(out)))
    project_dir = (config.LIBRARY_ROOT / job["genre"] /
                   f"{datetime.now().strftime('%Y-%m-%d')}_{slugify(job['title'])}")
    ids_meta: list[str] = []
    if (project_dir / "metadata.json").exists():
        try:
            meta = json.loads((project_dir / "metadata.json").read_text(encoding="utf-8"))
            ids_meta = list(meta.get("suno_ids", []) or [])
            result["project_dir"] = str(project_dir)
        except Exception:
            pass
    ids = ids_meta or ids_stdout
    result["clip_ids"] = ids

    if not ids:
        return {"status": "needs-review", "result": result,
                "error": "generation reported success but no clip ids parsable from stdout or metadata.json (F-07)"}

    # Postcheck (real guard postcheck against live Suno metadata)
    pc_code, pc_out, pc_err = _run(["python3", str(config.PROMPT_GUARD), "postcheck", *ids],
                                   timeout=config.GUARD_TIMEOUT * 2)
    postcheck = {"exit_code": pc_code, "detail": _parse_json(pc_out),
                 "stderr": pc_err.strip()[-500:] if pc_err.strip() else ""}
    if pc_code != 0:
        q = quarantine_takes(job, ids, project_dir)
        result["quarantine"] = q
        return {"status": "quarantined", "result": result, "postcheck_report": postcheck,
                "error": "postcheck failed; takes quarantined and excluded from album counts"}

    # Success: novelty history append + playlist refresh via existing scripts
    _append_novelty_history(job, ids)
    _run([str(config.SCRIPTS_DIR / "suno-playlist-refresh.py")], timeout=120)
    _run([str(config.SCRIPTS_DIR / "suno-remote-playlist-sync.py")], timeout=300)
    return {"status": "succeeded", "result": result, "postcheck_report": postcheck}


def _append_novelty_history(job: dict, clip_ids: list[str]) -> None:
    rows = []
    if config.NOVELTY_HISTORY.exists():
        try:
            data = json.loads(config.NOVELTY_HISTORY.read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else data.get("runs", [])
        except Exception:
            rows = []
    rows.append({"title": job.get("title"), "style": (job.get("style") or "")[:2000],
                 "lyrics": (job.get("lyrics") or "")[:2000], "genre": job.get("genre"),
                 "album": job.get("album"), "ids": clip_ids, "created_at": now_iso()})
    tmp = config.NOVELTY_HISTORY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(config.NOVELTY_HISTORY)


def quarantine_takes(job: dict, clip_ids: list[str], project_dir: Path) -> dict:
    """Same semantics as the P3 runner quarantine: move takes to _quarantine, strip from metadata."""
    meta_path = project_dir / "metadata.json"
    if not meta_path.exists():
        return {"moved": [], "note": "metadata.json not found; nothing imported to quarantine"}
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"moved": [], "error": f"metadata unreadable: {e}"}
    qdir = config.QUARANTINE_DIR / job["genre"] / project_dir.name
    qdir.mkdir(parents=True, exist_ok=True)
    kept, quarantined, moved = [], [], []
    for take in meta.get("takes", []):
        if clip_ids and take.get("suno_id") not in clip_ids:
            kept.append(take)
            continue
        take["status"] = "quarantined"
        audio = take.get("audio_path")
        if audio and Path(audio).exists():
            dest = qdir / Path(audio).name
            try:
                shutil.move(audio, dest)
                take["audio_path"] = str(dest)
                moved.append(str(dest))
            except Exception as e:
                take["quarantine_error"] = str(e)
        quarantined.append(take)
    meta["takes"] = kept
    meta["quarantined_takes"] = meta.get("quarantined_takes", []) + quarantined
    meta["updated_at"] = now_iso()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (qdir / "quarantine-info.json").write_text(json.dumps({
        "reason": "postcheck_failed", "title": job.get("title"), "album": job.get("album"),
        "clip_ids": clip_ids, "at": now_iso(), "takes": quarantined,
    }, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return {"moved": moved, "quarantined": len(quarantined), "kept": len(kept), "dir": str(qdir)}
