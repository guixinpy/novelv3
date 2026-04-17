from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Mozhou AI Writer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import projects, setups, chapters, config, storylines, outlines, dialogs, topologies, consistency, writing, versions, export

app.include_router(projects.router)
app.include_router(setups.router)
app.include_router(chapters.router)
app.include_router(config.router)
app.include_router(storylines.router)
app.include_router(outlines.router)
app.include_router(dialogs.router)
app.include_router(topologies.router)
app.include_router(consistency.router)
app.include_router(writing.router)
app.include_router(versions.router)
app.include_router(export.router)

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
