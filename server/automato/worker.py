"""Single asyncio worker consuming the SQLite queue.

Before every generation it acquires the SAME flock the CLI batch runner uses
(suno-library/.batch-runner.lock) — server and CLI can never spend credits
concurrently (F-04 shared lock).
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import time
from typing import Any

from . import config, engine
from .db import get_db


class Worker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._paused = False
        self._stop = False
        self.last_beat: float = 0.0
        self.current_job_id: str | None = None
        self._events: asyncio.Queue[dict] = asyncio.Queue(maxsize=500)

    # ---- lifecycle ----
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop = False
            self._task = asyncio.get_event_loop().create_task(self._loop(), name="automato-worker")

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    @property
    def alive(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        self._paused = True
        self.emit({"type": "worker", "state": "paused"})

    def resume(self) -> None:
        self._paused = False
        self.emit({"type": "worker", "state": "running"})

    # ---- events (SSE feed) ----
    def emit(self, event: dict) -> None:
        event.setdefault("at", engine.now_iso())
        try:
            self._events.put_nowait(event)
        except asyncio.QueueFull:
            try:
                self._events.get_nowait()
                self._events.put_nowait(event)
            except Exception:
                pass

    async def events(self):
        """Async generator of events for SSE (single shared feed, fan-out per request)."""
        while True:
            ev = await self._events.get()
            yield ev

    # ---- main loop ----
    async def _loop(self) -> None:
        db = get_db()
        # crash recovery: anything left 'running' from a previous process is unknown
        for j in db.list_jobs(status="running", limit=100):
            db.update_job(j["id"], status="needs-review",
                          error="server restarted while job was running; verify library state manually")
        while not self._stop:
            self.last_beat = time.time()
            if self._paused:
                await asyncio.sleep(2)
                continue
            job = db.next_queued()
            if not job:
                await asyncio.sleep(3)
                continue
            await self._run_one(job)

    async def _run_one(self, job: dict[str, Any]) -> None:
        db = get_db()
        jid = job["id"]
        self.current_job_id = jid
        self.emit({"type": "job", "job_id": jid, "status": "starting", "title": job["title"]})

        lock_fh = None
        try:
            config.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            lock_fh = open(config.LOCK_FILE, "a+")
            try:
                fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                db.update_job(jid, progress="generation lock held by CLI runner; waiting")
                self.emit({"type": "job", "job_id": jid, "status": "waiting_lock"})
                lock_fh.close()
                await asyncio.sleep(20)
                self.current_job_id = None
                return  # retry same job next loop iteration
            lock_fh.seek(0)
            lock_fh.truncate()
            lock_fh.write(f"automato-server worker job={jid}")
            lock_fh.flush()

            self.emit({"type": "job", "job_id": jid, "status": "running"})
            outcome = await asyncio.to_thread(engine.execute_job, job)
            fields: dict[str, Any] = {"status": outcome["status"], "result": outcome.get("result")}
            if outcome.get("postcheck_report") is not None:
                fields["postcheck_report"] = outcome["postcheck_report"]
            if outcome.get("error"):
                fields["error"] = outcome["error"]
            fields["progress"] = f"finished: {outcome['status']}"
            db.update_job(jid, **fields)
            self.emit({"type": "job", "job_id": jid, "status": outcome["status"]})
        except Exception as e:  # noqa: BLE001
            db.update_job(jid, status="failed", error=f"worker exception: {e}")
            self.emit({"type": "job", "job_id": jid, "status": "failed", "error": str(e)})
        finally:
            if lock_fh:
                try:
                    fcntl.flock(lock_fh, fcntl.LOCK_UN)
                except Exception:
                    pass
                lock_fh.close()
            self.current_job_id = None


worker = Worker()
