from pathlib import Path

from sqlalchemy import create_engine, text

from app.db import enable_sqlite_foreign_keys
from app.core.database_url import database_url, ensure_sqlite_parent_dir, sqlite_file_url


def test_database_url_uses_env_override(monkeypatch):
    monkeypatch.setenv("MOZHOU_DATABASE_URL", "sqlite:////tmp/novelv3-e2e/mozhou.db")

    assert database_url().endswith("/tmp/novelv3-e2e/mozhou.db")


def test_database_url_defaults_to_local_data(monkeypatch):
    monkeypatch.delenv("MOZHOU_DATABASE_URL", raising=False)

    assert database_url().endswith("/data/mozhou.db")


def test_sqlite_file_url_uses_forward_slashes_for_windows_paths():
    assert sqlite_file_url(Path("C:/workspace/novelv3/data/mozhou.db")) == (
        "sqlite:///C:/workspace/novelv3/data/mozhou.db"
    )


def test_ensure_sqlite_parent_dir_creates_parent(tmp_path):
    db_path = tmp_path / "nested" / "mozhou.db"
    ensure_sqlite_parent_dir(f"sqlite:///{db_path}")

    assert db_path.parent.exists()


def test_sqlite_file_connections_enable_longform_runtime_pragmas(tmp_path):
    db_path = tmp_path / "runtime.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    enable_sqlite_foreign_keys(engine)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert str(conn.execute(text("PRAGMA journal_mode")).scalar_one()).lower() == "wal"
            assert conn.execute(text("PRAGMA busy_timeout")).scalar_one() >= 30000
            assert str(conn.execute(text("PRAGMA synchronous")).scalar_one()).upper() in {"1", "NORMAL"}
    finally:
        engine.dispose()
