import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.local_diagnostics import log_event, new_request_id
from app.db import SessionLocal
from app.services.tasks.background_task_service import BackgroundTaskService


def fail_interrupted_background_tasks():
    db = SessionLocal()
    try:
        count = BackgroundTaskService(db).fail_interrupted_running_tasks()
        if count:
            log_event("background_tasks_interrupted", marked_failed=count)
    except Exception as exc:
        log_event("background_tasks_interrupted_scan_failed", error=str(exc))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    fail_interrupted_background_tasks()
    yield


app = FastAPI(title="Mozhou AI Writer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def local_request_diagnostics(request, call_next):
    request_id = new_request_id()
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log_event(
            "request_done",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=500,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
        raise
    response.headers["X-Request-ID"] = request_id
    log_event(
        "request_done",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    return response

from app.api import (
    athena,
    background_tasks_api,
    chapter_revisions,
    chapters,
    config,
    consistency,
    dialogs,
    export,
    model_call_traces,
    outlines,
    preferences,
    projects,
    setups,
    storylines,
    topologies,
    versions,
    world_model,
    writing,
    writing_agent_runs,
)

app.include_router(projects.router)
app.include_router(setups.router)
app.include_router(chapters.router)
app.include_router(chapter_revisions.router)
app.include_router(config.router)
app.include_router(storylines.router)
app.include_router(outlines.router)
app.include_router(dialogs.router)
app.include_router(topologies.router)
app.include_router(consistency.router)
app.include_router(writing.router)
app.include_router(writing_agent_runs.router)
app.include_router(versions.router)
app.include_router(export.router)
app.include_router(model_call_traces.router)
app.include_router(preferences.router)
app.include_router(background_tasks_api.router)
app.include_router(world_model.router)
app.include_router(athena.router)

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "not found"}
