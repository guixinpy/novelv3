from app.models import ChapterContent


def test_export_markdown(client):
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/export", json={"format": "markdown"})
    assert r2.status_code == 200
    assert "Test Novel" in r2.text
    assert r2.headers["content-type"].startswith("text/markdown")


def test_export_markdown_defaults_to_all_chapters(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Long Export"})
    pid = r.json()["id"]
    db_session.add_all(
        [
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文",
                word_count=1000,
                status="generated",
            )
            for index in (1, 100, 150)
        ]
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{pid}/export", json={"format": "markdown"})

    assert response.status_code == 200
    assert "第1章正文" in response.text
    assert "第100章正文" in response.text
    assert "第150章正文" in response.text


def test_export_markdown_honors_explicit_chapter_range(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Range Export"})
    pid = r.json()["id"]
    db_session.add_all(
        [
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文",
                word_count=1000,
                status="generated",
            )
            for index in (1, 100, 150)
        ]
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{pid}/export",
        json={"format": "markdown", "chapter_range": [1, 100]},
    )

    assert response.status_code == 200
    assert "第1章正文" in response.text
    assert "第100章正文" in response.text
    assert "第150章正文" not in response.text


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


def test_list_chapters_defaults_to_bounded_page_with_total(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Long Test"})
    pid = r.json()["id"]
    db_session.add_all(
        [
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content="测试章节内容",
                word_count=1000,
                status="generated",
            )
            for index in range(1, 251)
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{pid}/chapters")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["chapters"]) == 200
    assert payload["chapters"][0]["chapter_index"] == 1
    assert payload["chapters"][-1]["chapter_index"] == 200
    assert payload["total"] == 250
    assert payload["offset"] == 0
    assert payload["limit"] == 200
    assert payload["has_more"] is True
    assert payload["latest_chapter_index"] == 250


def test_list_chapters_returns_explicit_page(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Paged Test"})
    pid = r.json()["id"]
    db_session.add_all(
        [
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content="测试章节内容",
                word_count=1000,
                status="generated",
            )
            for index in range(1, 31)
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{pid}/chapters?offset=10&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert [chapter["chapter_index"] for chapter in payload["chapters"]] == [11, 12, 13, 14, 15]
    assert payload["total"] == 30
    assert payload["offset"] == 10
    assert payload["limit"] == 5
    assert payload["has_more"] is True
