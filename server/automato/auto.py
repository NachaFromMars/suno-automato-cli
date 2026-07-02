"""Auto-generation mode (P7).

Enqueues N auto-jobs into the SAME gated queue used by manual generate.
Each auto job:
  1. picks a target album (explicit, or next album under target, optionally genre-filtered)
  2. asks the seed-engine for a fresh novel concept (title/style/lyrics)
  3. runs the SAME guard_gate via engine.submit_job (precheck+lyrics+playlist-route+novelty)
  4. on PASS -> a normal queued job the single worker + flock will execute (no double-run)

"Auto" == enqueue N seed-generated jobs. It does NOT spawn a competing process.
Credits are only spent when the worker executes a queued job; pausing the worker
lets you test enqueue/status/stop mechanics without spending anything.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from . import config, engine

SEED_ENGINE = config.SCRIPTS_DIR / "suno-seed-engine.py"
SEED_TIMEOUT = 240  # matches batch runner budget (F-08)

# In-process auto-session state (single worker/host, so a module-level lock is fine).
_lock = threading.Lock()
_state: dict = {
    "running": False,
    "requested": 0,
    "remaining": 0,
    "enqueued": [],   # job ids
    "skipped": [],    # {reason, album, title?}
    "current": None,  # human-readable current step
    "started_at": None,
    "finished_at": None,
    "stop_requested": False,
    "last_error": None,
}


def _albums_under_target(genre: Optional[str] = None) -> list[dict]:
    out = []
    for a in engine.list_albums():
        tc = a.get("track_count", 0)
        tgt = a.get("target", 8)
        if tc < tgt:
            if genre and (a.get("genre") or "").lower() != genre.lower():
                continue
            out.append(a)
    # albums with the least progress first
    out.sort(key=lambda a: (a.get("track_count", 0) - a.get("target", 8)))
    return out


def _pick_album(explicit_album: Optional[str], genre: Optional[str]) -> Optional[dict]:
    albums = engine.list_albums()
    if explicit_album:
        for a in albums:
            if a.get("slug") == explicit_album or a.get("name") == explicit_album:
                return a
        return None
    under = _albums_under_target(genre)
    return under[0] if under else None


def _seed_concept(genre: str, base_title: str, iteration: int) -> Optional[dict]:
    """Invoke the seed-engine to build a fresh concept. Returns dict or None."""
    cmd = ["python3", str(SEED_ENGINE), "--genre", genre,
           "--title", base_title, "--iteration", str(iteration)]
    try:
        proc = subprocess.run(cmd, cwd=str(config.REPO_ROOT), text=True,
                              capture_output=True, timeout=SEED_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except Exception:
        return None


def status() -> dict:
    with _lock:
        s = dict(_state)
    s["albums_under_target"] = [
        {"slug": a.get("slug"), "genre": a.get("genre"),
         "track_count": a.get("track_count", 0), "target": a.get("target", 8)}
        for a in _albums_under_target()
    ]
    return s


def stop() -> dict:
    with _lock:
        if not _state["running"]:
            return {"ok": True, "running": False, "note": "not running"}
        _state["stop_requested"] = True
    return {"ok": True, "stopping": True}


def _run_session(count: int, album: Optional[str], genre: Optional[str]):
    from .db import get_db
    db = get_db()
    try:
        for i in range(count):
            with _lock:
                if _state["stop_requested"]:
                    _state["current"] = "stopped by user"
                    break
                _state["current"] = f"seeding concept {i+1}/{count}"

            # daily cap guard (shared with manual)
            if db.jobs_today() >= config.MAX_GENERATIONS_PER_DAY:
                with _lock:
                    _state["skipped"].append({"reason": "daily_generation_cap_reached"})
                    _state["remaining"] = 0
                break

            target = _pick_album(album, genre)
            if not target:
                with _lock:
                    _state["skipped"].append({"reason": "no_album_under_target",
                                              "album": album, "genre": genre})
                break

            tgenre = target.get("genre") or genre or "Bolero"
            talbum = target.get("name") or target.get("slug")

            # try a few seed attempts until one passes the gate
            accepted = False
            for attempt in range(3):
                concept = _seed_concept(tgenre, f"Auto {talbum}", iteration=int(time.time()) % 100000 + attempt)
                if not concept:
                    continue
                res = engine.submit_job(
                    source="auto",
                    title=concept.get("title", f"Auto {talbum}"),
                    genre=tgenre,
                    album=talbum,
                    style=concept.get("style_prompt", ""),
                    lyrics=concept.get("lyrics", ""),
                    exclude=concept.get("exclude", ""),
                    weirdness=concept.get("weirdness"),
                    style_influence=concept.get("style_influence"),
                )
                if res.get("accepted"):
                    with _lock:
                        _state["enqueued"].append(res["job_id"])
                    accepted = True
                    break
                else:
                    # gate rejected this concept; try another seed
                    reason = res.get("reason", "guard_blocked")
                    if reason == "daily_generation_cap_reached":
                        with _lock:
                            _state["skipped"].append({"reason": reason})
                        break
            if not accepted:
                with _lock:
                    _state["skipped"].append({"reason": "seed_failed_gate_after_retries",
                                              "album": talbum, "genre": tgenre})
            with _lock:
                _state["remaining"] = max(0, count - i - 1)
    except Exception as e:
        with _lock:
            _state["last_error"] = str(e)
    finally:
        with _lock:
            _state["running"] = False
            _state["stop_requested"] = False
            _state["finished_at"] = engine.now_iso()
            _state["current"] = None


def start(count: int, album: Optional[str] = None, genre: Optional[str] = None) -> dict:
    count = max(1, min(int(count), config.MAX_GENERATIONS_PER_DAY))
    with _lock:
        if _state["running"]:
            return {"accepted": False, "reason": "auto_already_running",
                    "remaining": _state["remaining"]}
        _state.update({
            "running": True, "requested": count, "remaining": count,
            "enqueued": [], "skipped": [], "current": "starting",
            "started_at": engine.now_iso(), "finished_at": None,
            "stop_requested": False, "last_error": None,
        })
    t = threading.Thread(target=_run_session, args=(count, album, genre), daemon=True)
    t.start()
    return {"accepted": True, "requested": count, "album": album, "genre": genre,
            "note": "auto session started; jobs enqueue into the gated worker queue"}
