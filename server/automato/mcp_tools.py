"""FastMCP facade — thin wrappers over the SAME engine layer (F-10: no bypass).

Mounted at /mcp (streamable-http) inside the FastAPI app, plus stdio entry:
    python -m automato.mcp
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import auto as auto_mode
from . import engine
from .db import get_db

mcp = FastMCP(
    "suno-automato",
    instructions=(
        "Guarded Suno music factory. ALL generation is gated: suno_generate runs the full "
        "strict guard (11-block PromptStyle precheck, lyrics-check, playlist-route, "
        "novelty-check) and refuses on failure. Use suno_validate to iterate until PASS "
        "before spending credits."
    ),
    stateless_http=True,
)


def _worker_alive() -> bool:
    try:
        from .worker import worker
        return worker.alive
    except Exception:
        return False


@mcp.tool()
def suno_status() -> dict:
    """Auth/credits, worker, Xvfb display, generation lock and queue status."""
    return engine.status_summary(worker_alive=_worker_alive())


@mcp.tool()
def suno_validate(style: str, lyrics: str, title: str, genre: str, album: str,
                  instrumental: bool = False) -> dict:
    """Run the full guard gate WITHOUT spending credits. Returns per-gate PASS/FAIL report."""
    passed, report = engine.guard_gate(title=title, genre=genre, album=album,
                                       style=style, lyrics=lyrics, instrumental=instrumental)
    get_db().record_guard_run(source="mcp:validate", passed=passed, report=report,
                              title=title, genre=genre, album=album)
    report["blocks_present"] = engine.precheck_blocks(style)
    return report


@mcp.tool()
def suno_generate(title: str, genre: str, album: str, style: str, lyrics: str,
                  exclude: str = "", weirdness: int = 62, style_influence: int = 86,
                  instrumental: bool = False) -> dict:
    """Gated generation: guard gate runs first; on FAIL returns the guard report instead of
    spending credits. On PASS the job is queued and a job_id returned."""
    return engine.submit_job(source="mcp", title=title, genre=genre, album=album,
                             style=style, lyrics=lyrics, exclude=exclude,
                             weirdness=weirdness, style_influence=style_influence,
                             instrumental=instrumental)


@mcp.tool()
def suno_job(job_id: str) -> dict:
    """Job detail: status, guard report, postcheck report, clip ids."""
    job = get_db().get_job(job_id)
    return job or {"error": "not_found", "job_id": job_id}


@mcp.tool()
def suno_jobs(status: str = "", limit: int = 20) -> list[dict[str, Any]]:
    """List jobs, optionally filtered by status (queued|running|succeeded|failed|blocked|cancelled|quarantined|needs-review)."""
    jobs = get_db().list_jobs(status=status or None, limit=min(limit, 100))
    return [{k: j.get(k) for k in ("id", "created_at", "status", "source", "title",
                                   "genre", "album", "progress", "error")} for j in jobs]


@mcp.tool()
def suno_library_search(query: str = "", genre: str = "", album: str = "",
                        limit: int = 20) -> dict:
    """Search the local suno-library (metadata.json index) by text/genre/album."""
    return engine.scan_projects(genre=genre or None, album=album or None,
                                q=query or None, limit=min(limit, 100))


@mcp.tool()
def suno_albums() -> list[dict]:
    """All album manifests with track counts and remote playlist sync state."""
    return engine.list_albums()

@mcp.tool()
def suno_auto_start(count: int = 1, album: str = "", genre: str = "") -> dict:
    """Start auto-generation: enqueue `count` seed-generated jobs (each runs the full
    guard). Optional `album` (slug) or `genre` filter; default picks albums under target.
    Jobs execute through the same gated worker — credits spent only on execution."""
    return auto_mode.start(count, album or None, genre or None)

@mcp.tool()
def suno_auto_status() -> dict:
    """Current auto-session status: running, remaining, enqueued job ids, skipped, albums under target."""
    return auto_mode.status()

@mcp.tool()
def suno_auto_stop() -> dict:
    """Stop the auto session after the current step; no further jobs enqueued."""
    return auto_mode.stop()
