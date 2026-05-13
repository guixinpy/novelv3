from app.models import ChapterContent, LongformMemory, Project


def test_get_project_reconciles_current_word_count_from_chapters(client, db_session):
    project = Project(name="Longform Stats", current_word_count=1)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=1,
                title="一",
                content="正文一",
                word_count=1200,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=2,
                title="二",
                content="正文二",
                word_count=1300,
                status="generated",
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    assert response.json()["current_word_count"] == 2500
    db_session.refresh(project)
    assert project.current_word_count == 2500


def test_longform_memory_model_supports_scope_layers(db_session):
    project = Project(name="Memory Model")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    memory = LongformMemory(
        project_id=project.id,
        memory_type="arc",
        scope_key="arc:1-20",
        start_chapter_index=1,
        end_chapter_index=20,
        title="第一剧情弧",
        summary="主角进入核心冲突。",
        status="current",
        memory_metadata={"chapter_count": 20},
    )
    db_session.add(memory)
    db_session.commit()

    row = db_session.query(LongformMemory).filter_by(project_id=project.id, scope_key="arc:1-20").one()
    assert row.memory_type == "arc"
    assert row.memory_metadata["chapter_count"] == 20


def test_rebuild_longform_memory_creates_chapter_arc_volume_and_global_layers(client, db_session):
    project = Project(name="Hundred Chapter Memory")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 101):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。主角推进第{(index - 1) // 20 + 1}段剧情。" * 8,
                word_count=1000 + index,
                status="generated",
            )
        )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/longform/memory/diagnostics")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["counts_by_type"] == {"chapter": 100, "arc": 5, "volume": 1, "global": 1}
    assert diagnostics.status_code == 200
    assert diagnostics.json()["counts_by_type"]["chapter"] == 100
    assert diagnostics.json()["current_word_count"] == sum(1000 + index for index in range(1, 101))


def test_longform_context_for_chapter_excludes_future_chapters(client, db_session):
    project = Project(name="Future Boundary")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 8):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。{'未来秘密只在第7章揭露。' if index == 7 else '普通线索。'}",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")

    response = client.get(f"/api/v1/projects/{project.id}/athena/longform/context/chapters/5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chapter_index"] == 5
    assert "第4章" in payload["prompt_context"]
    assert "第7章" not in payload["prompt_context"]
    assert "未来秘密" not in payload["prompt_context"]
    assert all(
        item.get("end_chapter_index") is None or item["end_chapter_index"] <= 5
        for section in payload["sections"]
        for item in section["items"]
    )
