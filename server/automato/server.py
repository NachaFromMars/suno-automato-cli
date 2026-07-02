"""automato-server: FastAPI app — REST /api/v1 + Jinja2/HTMX dashboard + FastMCP mount at /mcp.

Run: uvicorn automato.server:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from . import auto as auto_mode
from . import config, engine
from .db import get_db
from .mcp_tools import mcp
from .worker import worker

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


# ---------------------------------------------------------------------------
# Lifespan: start worker + MCP session manager
# ---------------------------------------------------------------------------
mcp.settings.streamable_http_path = "/"  # so the mount below serves exactly /mcp
mcp_app = mcp.streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    get_db()  # init schema
    worker.start()
    async with mcp.session_manager.run():
        yield
    await worker.stop()


app = FastAPI(title="Suno Automato", version=config.VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
app.mount("/mcp", mcp_app)

# ---------------------------------------------------------------------------
# Optional bearer-token auth (config.API_TOKEN via automato.toml / env).
# When a token is set, MUTATING endpoints + the MCP mount require
#   Authorization: Bearer <token>
# Read-only endpoints and the dashboard stay open (bind 127.0.0.1 by default;
# put a reverse proxy with TLS in front for anything beyond loopback).
# ---------------------------------------------------------------------------
_PROTECTED_PREFIXES = ("/mcp",)
_PROTECTED_ROUTES = {
    ("POST", "/api/v1/generate"),
    ("POST", "/api/v1/worker/pause"),
    ("POST", "/api/v1/worker/resume"),
    ("POST", "/api/v1/auto/start"),
    ("POST", "/api/v1/auto/stop"),
    ("POST", "/ui/generate"),
    ("POST", "/ui/auto-start"),
    ("POST", "/ui/auto-stop"),
}

def _needs_auth(method: str, path: str) -> bool:
    if not config.API_TOKEN:
        return False
    if (method, path) in _PROTECTED_ROUTES:
        return True
    if method == "POST" and path.startswith("/api/v1/jobs/") and path.endswith("/cancel"):
        return True
    return any(path == p or path.startswith(p + "/") for p in _PROTECTED_PREFIXES)

@app.middleware("http")
async def bearer_auth(request: Request, call_next):
    if _needs_auth(request.method, request.url.path):
        header = request.headers.get("authorization", "")
        token = header[7:] if header.lower().startswith("bearer ") else ""
        if not (token and hmac.compare_digest(token, config.API_TOKEN)):
            return JSONResponse({"detail": "missing or invalid bearer token"}, status_code=401,
                                headers={"WWW-Authenticate": "Bearer"})
    return await call_next(request)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ValidateRequest(BaseModel):
    title: str
    genre: str
    album: str
    style: str
    lyrics: str = ""
    instrumental: bool = False


class GenerateRequest(ValidateRequest):
    exclude: str = ""
    weirdness: int = Field(62, ge=0, le=100)
    style_influence: int = Field(86, ge=0, le=100)

class AutoStartRequest(BaseModel):
    count: int = Field(1, ge=1, le=100)
    album: Optional[str] = None
    genre: Optional[str] = None


# ---------------------------------------------------------------------------
# REST /api/v1
# ---------------------------------------------------------------------------
@app.get("/health")
@app.get("/api/v1/health")
async def health():
    return {"ok": True, "service": "suno-automato", "version": config.VERSION,
            "worker_alive": worker.alive, "at": engine.now_iso()}


@app.get("/api/v1/status")
async def api_status(credits: bool = Query(True)):
    return await asyncio.to_thread(engine.status_summary, worker.alive, credits)


@app.post("/api/v1/validate")
async def api_validate(req: ValidateRequest):
    passed, report = await asyncio.to_thread(
        engine.guard_gate, title=req.title, genre=req.genre, album=req.album,
        style=req.style, lyrics=req.lyrics, instrumental=req.instrumental)
    get_db().record_guard_run(source="api:validate", passed=passed, report=report,
                              title=req.title, genre=req.genre, album=req.album)
    report["blocks_present"] = engine.precheck_blocks(req.style)
    return report


@app.post("/api/v1/generate")
async def api_generate(req: GenerateRequest):
    res = await asyncio.to_thread(
        engine.submit_job, source="api", title=req.title, genre=req.genre, album=req.album,
        style=req.style, lyrics=req.lyrics, exclude=req.exclude,
        weirdness=req.weirdness, style_influence=req.style_influence,
        instrumental=req.instrumental)
    if res.get("accepted"):
        worker.emit({"type": "queue", "event": "job_submitted", "job_id": res["job_id"]})
        return JSONResponse(res, status_code=202)
    return JSONResponse(res, status_code=422)


@app.post("/api/v1/auto/start")
async def api_auto_start(req: AutoStartRequest):
    res = await asyncio.to_thread(auto_mode.start, req.count, req.album, req.genre)
    worker.emit({"type": "auto", "event": "auto_start", "requested": req.count})
    return JSONResponse(res, status_code=202 if res.get("accepted") else 409)

@app.get("/api/v1/auto/status")
async def api_auto_status():
    return await asyncio.to_thread(auto_mode.status)

@app.post("/api/v1/auto/stop")
async def api_auto_stop():
    res = await asyncio.to_thread(auto_mode.stop)
    worker.emit({"type": "auto", "event": "auto_stop"})
    return res

@app.get("/api/v1/jobs")
async def api_jobs(status: Optional[str] = None, limit: int = Query(50, le=200), offset: int = 0):
    return {"jobs": get_db().list_jobs(status=status, limit=limit, offset=offset),
            "queue_depth": get_db().queue_depth()}


@app.get("/api/v1/jobs/{job_id}")
async def api_job(job_id: str):
    job = get_db().get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.post("/api/v1/jobs/{job_id}/cancel")
async def api_job_cancel(job_id: str):
    res = engine.cancel_job(job_id)
    if not res.get("ok"):
        raise HTTPException(409 if res.get("error") != "not_found" else 404, res.get("error"))
    worker.emit({"type": "job", "job_id": job_id, "status": "cancelled"})
    return res


@app.post("/api/v1/worker/pause")
async def api_worker_pause():
    worker.pause()
    return {"ok": True, "paused": True}


@app.post("/api/v1/worker/resume")
async def api_worker_resume():
    worker.resume()
    return {"ok": True, "paused": False}


@app.get("/api/v1/library/projects")
async def api_projects(genre: Optional[str] = None, album: Optional[str] = None,
                       q: Optional[str] = None, limit: int = Query(50, le=200), offset: int = 0):
    return await asyncio.to_thread(engine.scan_projects, genre=genre, album=album,
                                   q=q, limit=limit, offset=offset)


@app.get("/api/v1/library/projects/{genre}/{batch}")
async def api_project(genre: str, batch: str):
    p = engine.get_project(f"{genre}/{batch}")
    if not p:
        raise HTTPException(404, "project not found")
    return p


@app.get("/api/v1/media/{genre}/{batch}/audio/{filename}")
async def api_media_audio(genre: str, batch: str, filename: str):
    p = engine.resolve_media(f"{genre}/{batch}", filename, "audio")
    if not p:
        raise HTTPException(404, "audio not found")
    # FileResponse handles HTTP Range natively (206 Partial Content)
    return FileResponse(p, media_type="audio/mpeg", filename=filename)


@app.get("/api/v1/media/{genre}/{batch}/cover/{filename}")
async def api_media_cover(genre: str, batch: str, filename: str):
    p = engine.resolve_media(f"{genre}/{batch}", filename, "cover")
    if not p:
        raise HTTPException(404, "cover not found")
    mt = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return FileResponse(p, media_type=mt)


@app.get("/api/v1/albums")
async def api_albums():
    return {"albums": await asyncio.to_thread(engine.list_albums)}


@app.get("/api/v1/albums/{slug}")
async def api_album(slug: str):
    a = engine.get_album(slug)
    if not a:
        raise HTTPException(404, "album not found")
    return a


@app.get("/api/v1/guards/reports")
async def api_guard_reports(limit: int = Query(50, le=200), offset: int = 0,
                            passed: Optional[bool] = None):
    return {"stats": get_db().guard_stats(),
            "reports": get_db().list_guard_runs(limit=limit, offset=offset,
                                                passed=None if passed is None else int(passed))}


@app.get("/api/v1/novelty")
async def api_novelty(limit: int = Query(30, le=200), offset: int = 0):
    return engine.novelty_history(limit=limit, offset=offset)


@app.get("/api/v1/config")
async def api_config():
    return config.safe_config()


@app.get("/api/v1/events")
@app.get("/events")
async def sse_events(request: Request):
    async def gen():
        q: asyncio.Queue = asyncio.Queue(maxsize=100)

        async def pump():
            async for ev in worker.events():
                with contextlib.suppress(asyncio.QueueFull):
                    q.put_nowait(ev)

        task = asyncio.create_task(pump())
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    yield {"event": ev.get("type", "message"), "data": json.dumps(ev, ensure_ascii=False)}
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat",
                           "data": json.dumps({"at": engine.now_iso(),
                                               "queue_depth": get_db().queue_depth(),
                                               "worker_alive": worker.alive,
                                               "worker_paused": worker.paused,
                                               "current_job": worker.current_job_id})}
        finally:
            task.cancel()

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------
# Dashboard UI (Jinja2 + HTMX)
# ---------------------------------------------------------------------------
def _page(request: Request, template: str, active: str, **ctx):
    return templates.TemplateResponse(request, template, {"active": active, **ctx})


@app.get("/", response_class=HTMLResponse)
async def ui_overview(request: Request):
    status = await asyncio.to_thread(engine.status_summary, worker.alive, True)
    jobs = get_db().list_jobs(limit=10)
    return _page(request, "overview.html", "overview", status=status, jobs=jobs,
                 worker_paused=worker.paused)


@app.get("/generate", response_class=HTMLResponse)
async def ui_generate(request: Request):
    albums = await asyncio.to_thread(engine.list_albums)
    return _page(request, "generate.html", "generate", albums=albums,
                 instrumental_genres=sorted(config.INSTRUMENTAL_GENRES))


@app.get("/jobs", response_class=HTMLResponse)
async def ui_jobs(request: Request, status: Optional[str] = None):
    jobs = get_db().list_jobs(status=status, limit=100)
    return _page(request, "jobs.html", "jobs", jobs=jobs, filter_status=status or "",
                 queue_depth=get_db().queue_depth(), worker_paused=worker.paused,
                 worker_alive=worker.alive)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def ui_job_detail(request: Request, job_id: str):
    job = get_db().get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return _page(request, "job_detail.html", "jobs", job=job,
                 guard_json=json.dumps(job.get("guard_report") or {}, ensure_ascii=False, indent=2),
                 postcheck_json=json.dumps(job.get("postcheck_report") or {}, ensure_ascii=False, indent=2),
                 result_json=json.dumps(job.get("result") or {}, ensure_ascii=False, indent=2))


@app.get("/library", response_class=HTMLResponse)
async def ui_library(request: Request, genre: Optional[str] = None, q: Optional[str] = None,
                     page: int = 1):
    limit = 24
    data = await asyncio.to_thread(engine.scan_projects, genre=genre, album=None, q=q,
                                   limit=limit, offset=(max(page, 1) - 1) * limit)
    genres = sorted({d.name for d in config.LIBRARY_ROOT.iterdir()
                     if d.is_dir() and not d.name.startswith("_")})
    return _page(request, "library.html", "library", data=data, genres=genres,
                 sel_genre=genre or "", q=q or "", page=max(page, 1),
                 pages=max(1, -(-data["total"] // limit)))


@app.get("/library/{genre}/{batch}", response_class=HTMLResponse)
async def ui_project(request: Request, genre: str, batch: str):
    p = engine.get_project(f"{genre}/{batch}")
    if not p:
        raise HTTPException(404, "project not found")
    return _page(request, "project.html", "library", p=p, genre=genre, batch=batch)


@app.get("/albums", response_class=HTMLResponse)
async def ui_albums(request: Request):
    albums = await asyncio.to_thread(engine.list_albums)
    return _page(request, "albums.html", "albums", albums=albums)


@app.get("/albums/{slug}", response_class=HTMLResponse)
async def ui_album_detail(request: Request, slug: str):
    a = engine.get_album(slug)
    if not a:
        raise HTTPException(404, "album not found")
    return _page(request, "album_detail.html", "albums", a=a, slug=slug)


@app.get("/reports", response_class=HTMLResponse)
async def ui_reports(request: Request, show: str = "all"):
    passed = {"passed": 1, "failed": 0}.get(show)
    reports = get_db().list_guard_runs(limit=100, passed=passed)
    novelty = engine.novelty_history(limit=15)
    return _page(request, "reports.html", "reports", reports=reports, show=show,
                 stats=get_db().guard_stats(), novelty=novelty)


@app.get("/auto", response_class=HTMLResponse)
async def ui_auto(request: Request):
    albums = await asyncio.to_thread(engine.list_albums)
    st = await asyncio.to_thread(auto_mode.status)
    genres = sorted({(a.get("genre") or "") for a in albums if a.get("genre")})
    return _page(request, "auto.html", "auto", albums=albums, st=st, genres=genres,
                 max_per_day=config.MAX_GENERATIONS_PER_DAY)

@app.post("/ui/auto-start", response_class=HTMLResponse)
async def ui_auto_start(request: Request, count: int = Form(1),
                        album: Optional[str] = Form(None), genre: Optional[str] = Form(None)):
    album = album or None
    genre = genre or None
    res = await asyncio.to_thread(auto_mode.start, count, album, genre)
    worker.emit({"type": "auto", "event": "auto_start", "requested": count})
    st = await asyncio.to_thread(auto_mode.status)
    return templates.TemplateResponse(request, "partials/auto_status.html", {"st": st, "res": res})

@app.post("/ui/auto-stop", response_class=HTMLResponse)
async def ui_auto_stop(request: Request):
    res = await asyncio.to_thread(auto_mode.stop)
    worker.emit({"type": "auto", "event": "auto_stop"})
    st = await asyncio.to_thread(auto_mode.status)
    return templates.TemplateResponse(request, "partials/auto_status.html", {"st": st, "res": res})

@app.get("/ui/auto-status", response_class=HTMLResponse)
async def ui_auto_status(request: Request):
    st = await asyncio.to_thread(auto_mode.status)
    return templates.TemplateResponse(request, "partials/auto_status.html", {"st": st, "res": None})

# ---- HTMX partials (real endpoints; return HTML fragments) ----
@app.post("/ui/validate", response_class=HTMLResponse)
async def ui_validate(request: Request,
                      title: str = Form(""), genre: str = Form(""), album: str = Form(""),
                      style: str = Form(""), lyrics: str = Form(""),
                      instrumental: Optional[str] = Form(None)):
    inst = instrumental in ("on", "true", "1")
    if not (title and genre and album and style):
        return templates.TemplateResponse(request, "partials/validate_result.html",
                                          {"report": None,
                                           "hint": "Fill in title, genre, album and style to run the guard."})
    passed, report = await asyncio.to_thread(
        engine.guard_gate, title=title, genre=genre, album=album,
        style=style, lyrics=lyrics, instrumental=inst)
    get_db().record_guard_run(source="ui:validate", passed=passed, report=report,
                              title=title, genre=genre, album=album)
    blocks = engine.precheck_blocks(style)
    return templates.TemplateResponse(request, "partials/validate_result.html",
                                      {"report": report, "blocks": blocks, "hint": None})


@app.post("/ui/generate", response_class=HTMLResponse)
async def ui_generate_submit(request: Request,
                             title: str = Form(...), genre: str = Form(...), album: str = Form(...),
                             style: str = Form(...), lyrics: str = Form(""),
                             exclude: str = Form(""), weirdness: int = Form(62),
                             style_influence: int = Form(86),
                             instrumental: Optional[str] = Form(None)):
    inst = instrumental in ("on", "true", "1")
    res = await asyncio.to_thread(
        engine.submit_job, source="ui", title=title, genre=genre, album=album,
        style=style, lyrics=lyrics, exclude=exclude, weirdness=weirdness,
        style_influence=style_influence, instrumental=inst)
    if res.get("accepted"):
        worker.emit({"type": "queue", "event": "job_submitted", "job_id": res["job_id"]})
    return templates.TemplateResponse(request, "partials/submit_result.html", {"res": res})


@app.get("/ui/status-cards", response_class=HTMLResponse)
async def ui_status_cards(request: Request):
    status = await asyncio.to_thread(engine.status_summary, worker.alive, True)
    return templates.TemplateResponse(request, "partials/status_cards.html",
                                      {"status": status, "worker_paused": worker.paused})


@app.get("/ui/jobs-rows", response_class=HTMLResponse)
async def ui_jobs_rows(request: Request, status: Optional[str] = None, limit: int = 20):
    jobs = get_db().list_jobs(status=status, limit=min(limit, 100))
    return templates.TemplateResponse(request, "partials/jobs_rows.html", {"jobs": jobs})
