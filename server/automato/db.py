"""SQLite (WAL) job queue + guard report history. Files stay source of truth for media."""
from __future__ import annotations
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,             -- queued|running|succeeded|failed|blocked|cancelled|quarantined|needs-review
    source TEXT NOT NULL,             -- api|ui|mcp
    title TEXT NOT NULL,
    genre TEXT NOT NULL,
    album TEXT NOT NULL,
    style TEXT NOT NULL,
    lyrics TEXT NOT NULL,
    exclude TEXT,
    weirdness INTEGER,
    style_influence INTEGER,
    instrumental INTEGER NOT NULL DEFAULT 0,
    guard_report TEXT,                -- JSON
    postcheck_report TEXT,            -- JSON
    result TEXT,                      -- JSON: clip_ids, project_dir, stdout tail
    error TEXT,
    progress TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS guard_runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,             -- validate|job-gate
    job_id TEXT,
    title TEXT,
    genre TEXT,
    album TEXT,
    passed INTEGER NOT NULL,
    report TEXT NOT NULL              -- JSON per-gate report
);
CREATE INDEX IF NOT EXISTS idx_guard_created ON guard_runs(created_at DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Database:
    """Small threadsafe sync wrapper (guard/generation work runs in threads anyway)."""

    def __init__(self, path=None):
        self.path = str(path or config.DB_PATH)
        config.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---- jobs ----
    def create_job(self, *, source: str, title: str, genre: str, album: str,
                   style: str, lyrics: str, exclude: str = "",
                   weirdness: int | None = None, style_influence: int | None = None,
                   instrumental: bool = False, status: str = "queued",
                   guard_report: dict | None = None) -> str:
        jid = uuid.uuid4().hex[:12]
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs (id, created_at, updated_at, status, source, title, genre, album,"
                " style, lyrics, exclude, weirdness, style_influence, instrumental, guard_report)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (jid, now, now, status, source, title, genre, album, style, lyrics, exclude,
                 weirdness, style_influence, int(instrumental),
                 json.dumps(guard_report, ensure_ascii=False) if guard_report else None))
            self._conn.commit()
        return jid

    def update_job(self, jid: str, **fields: Any) -> None:
        json_fields = {"guard_report", "postcheck_report", "result"}
        sets, vals = ["updated_at=?"], [_now()]
        for k, v in fields.items():
            sets.append(f"{k}=?")
            vals.append(json.dumps(v, ensure_ascii=False) if k in json_fields and v is not None else v)
        vals.append(jid)
        with self._lock:
            self._conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", vals)
            self._conn.commit()

    def get_job(self, jid: str) -> Optional[dict]:
        row = self._conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        return self._job_dict(row) if row else None

    def list_jobs(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)).fetchall()
        return [self._job_dict(r) for r in rows]

    def queue_depth(self) -> int:
        r = self._conn.execute("SELECT COUNT(*) c FROM jobs WHERE status IN ('queued','running')").fetchone()
        return int(r["c"])

    def next_queued(self) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at ASC LIMIT 1").fetchone()
        return self._job_dict(row) if row else None

    def jobs_today(self) -> int:
        day = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        r = self._conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE created_at LIKE ? AND status IN ('running','succeeded','quarantined','needs-review')",
            (day + "%",)).fetchone()
        return int(r["c"])

    @staticmethod
    def _job_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        for k in ("guard_report", "postcheck_report", "result"):
            if d.get(k):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        d["instrumental"] = bool(d.get("instrumental"))
        return d

    # ---- guard runs ----
    def record_guard_run(self, *, source: str, passed: bool, report: dict,
                         job_id: str | None = None, title: str = "", genre: str = "",
                         album: str = "") -> str:
        gid = uuid.uuid4().hex[:12]
        with self._lock:
            self._conn.execute(
                "INSERT INTO guard_runs (id, created_at, source, job_id, title, genre, album, passed, report)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (gid, _now(), source, job_id, title, genre, album, int(passed),
                 json.dumps(report, ensure_ascii=False)))
            self._conn.commit()
        return gid

    def list_guard_runs(self, limit: int = 50, offset: int = 0, passed: int | None = None) -> list[dict]:
        if passed is None:
            rows = self._conn.execute(
                "SELECT * FROM guard_runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM guard_runs WHERE passed=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (passed, limit, offset)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["report"] = json.loads(d["report"])
            except Exception:
                pass
            d["passed"] = bool(d["passed"])
            out.append(d)
        return out

    def guard_stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) c FROM guard_runs").fetchone()["c"]
        failed = self._conn.execute("SELECT COUNT(*) c FROM guard_runs WHERE passed=0").fetchone()["c"]
        return {"total": total, "failed": failed, "passed": total - failed}


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
