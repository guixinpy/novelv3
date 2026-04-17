from unittest.mock import AsyncMock, patch
from app.models import ChapterContent


def test_export_markdown(client):
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/export", json={"format": "markdown"})
    assert r2.status_code == 200
    assert "Test Novel" in r2.text
    assert r2.headers["content-type"].startswith("text/markdown")


def test_export_txt(client):
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/export", json={"format": "txt"})
    assert r2.status_code == 200
    assert "Test Novel" in r2.text


def test_list_chapters_empty(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.get(f"/api/v1/projects/{pid}/chapters")
    assert r2.status_code == 200
    assert r2.json()["chapters"] == []


def test_list_chapters_with_content(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    ch = ChapterContent(
        project_id=pid,
        chapter_index=1,
        title="第1章",
        content="测试章节内容",
        word_count=7,
        status="generated",
    )
    db_session.add(ch)
    db_session.commit()

    r2 = client.get(f"/api/v1/projects/{pid}/chapters")
    assert r2.status_code == 200
    assert len(r2.json()["chapters"]) == 1
    assert r2.json()["chapters"][0]["chapter_index"] == 1

