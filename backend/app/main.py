import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mozhou AI Writer")

_allow_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import projects, config

app.include_router(projects.router)
app.include_router(config.router)

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
