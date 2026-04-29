import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'mozhou.db'}"


def database_url() -> str:
    return os.getenv("MOZHOU_DATABASE_URL") or DEFAULT_DATABASE_URL


def ensure_sqlite_parent_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    raw_path = url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
