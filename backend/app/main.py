"""Mozhou AI Writer 入口（arch-refactor：仅挂 v2 agent API）。

旧 v1 路由已随旧代码整链退役（阶段 4）；前端后续重写时将对接新 API。
"""
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v2 import agent as agent_v2


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Mozhou AI Writer (v2 agent)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def local_request_diagnostics(request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        raise
    response.headers["X-Request-ID"] = str(int(started * 1_000_000))
    return response


app.include_router(agent_v2.router)

# 兼容端点：旧前端健康检查
@app.get("/api/v1/health")
def health():
    return {"status": "ok"}

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # /api/* 不落 catch-all：让 API 404 暴露真实错误，而非 200+HTML 掩盖
        if full_path.startswith("api/"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"API 端点不存在: /{full_path}")
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "not found"}
