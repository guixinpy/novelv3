import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def test_create_and_get_project():
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Novel"
    pid = data["id"]

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid
