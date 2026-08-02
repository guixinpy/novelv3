import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, enable_sqlite_foreign_keys, get_db
from app.main import app

# 临时文件 DB + 默认连接池（修复 SSE 流内 db 会话独占连接的间歇性死锁：
# in-memory + StaticPool 单连接时，流内 session 借出唯一连接不归还，
# 其他请求（如审批轮询）永远等连接池）。
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"novelv3_test_{os.getpid()}.db")
TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
enable_sqlite_foreign_keys(engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
