import os
import tempfile
import uuid

# 必须在 import app.main 之前设置（code-review #5：TestClient 跑 lifespan 曾对
# 真实 data/mozhou.db 执行 create_all DDL）
os.environ.setdefault("NOVELV3_SKIP_CREATE_ALL", "1")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, enable_sqlite_foreign_keys, get_db
from app.main import app

# 临时文件 DB + 默认连接池（修复 SSE 流内 db 会话独占连接的间歇性死锁：
# in-memory + StaticPool 单连接时，流内 session 借出唯一连接不归还，
# 其他请求（如审批轮询）永远等连接池）。
# uuid 命名 + 进程退出清理（code-review 三轮 #14：pid 命名会被 Windows 快速
# 复用——残留库导致后续测试在脏库上跑、绝对计数断言静默失败）
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"novelv3_test_{uuid.uuid4().hex[:12]}.db")
TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
enable_sqlite_foreign_keys(engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束清理临时 DB（含 WAL/SHM 伴生文件）。"""
    for suffix in ("", "-wal", "-shm"):
        path = _TEST_DB_PATH + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(client):
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
