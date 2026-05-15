from unittest.mock import AsyncMock, patch

from app.models import Outline, Project, Setup, Storyline


def test_athena_storyline_generate_defaults_to_windowed_response(client, db_session):
    project = Project(name="Windowed Storyline Generate")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={},
            characters=[],
            core_concept={},
        )
    )
    db_session.commit()
    plotlines = [
        {
            "name": f"故事线{index}",
            "type": "sub",
            "milestones": [
                {"chapter_index": chapter_index, "title": f"节点{chapter_index}"}
                for chapter_index in range(1, 1001)
            ] if index == 1 else [],
        }
        for index in range(1, 61)
    ]
    foreshadowing = [
        {
            "hint": f"伏笔{index}",
            "planted_chapter": index,
            "resolved_chapter": index + 10,
            "status": "pending",
        }
        for index in range(1, 301)
    ]

    with patch("app.api.storylines.load_api_key", return_value="sk-test"), \
         patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock) as complete, \
         patch("app.api.storylines.ai_service.parse_json") as parse_json:
        complete.return_value.content = "{}"
        parse_json.return_value = {"plotlines": plotlines, "foreshadowing": foreshadowing}

        response = client.post(f"/api/v1/projects/{project.id}/athena/evolution/plan/generate?target=storyline")

    assert response.status_code == 200
    data = response.json()
    assert len(data["plotlines"]) == 20
    assert data["plotlines_total"] == 60
    assert data["plotlines_has_more"] is True
    assert len(data["plotlines"][0]["milestones"]) == 80
    assert data["plotlines"][0]["milestones_total"] == 1000
    assert len(data["foreshadowing"]) == 100
    assert data["foreshadowing_total"] == 300

    stored = db_session.query(Storyline).filter(Storyline.project_id == project.id).one()
    assert len(stored.plotlines) == 60
    assert len(stored.plotlines[0]["milestones"]) == 1000
    assert len(stored.foreshadowing) == 300


def test_athena_outline_generate_defaults_to_windowed_response(client, db_session):
    project = Project(name="Windowed Outline Generate")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={},
            characters=[],
            core_concept={},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[],
            foreshadowing=[],
        )
    )
    db_session.commit()
    chapters = [
        {
            "chapter_index": index,
            "title": f"第{index}章",
            "summary": "章节摘要" * 20,
        }
        for index in range(1, 1001)
    ]
    plotlines = [
        {
            "name": f"大纲线{index}",
            "type": "sub",
            "milestones": [{"chapter_index": index, "title": f"节点{index}"}],
        }
        for index in range(1, 51)
    ]
    foreshadowing = [
        {
            "hint": f"伏笔{index}",
            "planted_chapter": index,
            "resolved_chapter": index + 10,
            "status": "pending",
        }
        for index in range(1, 301)
    ]

    with patch("app.api.outlines.load_api_key", return_value="sk-test"), \
         patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock) as complete, \
         patch("app.api.outlines.ai_service.parse_json") as parse_json:
        complete.return_value.content = "{}"
        parse_json.return_value = {
            "total_chapters": 1000,
            "chapters": chapters,
            "plotlines": plotlines,
            "foreshadowing": foreshadowing,
        }

        response = client.post(f"/api/v1/projects/{project.id}/athena/evolution/plan/generate?target=outline")

    assert response.status_code == 200
    data = response.json()
    assert len(data["chapters"]) == 100
    assert data["chapters_total"] == 1000
    assert data["chapters_has_more"] is True
    assert len(data["plotlines"]) == 20
    assert data["plotlines_total"] == 50
    assert len(data["foreshadowing"]) == 100
    assert data["foreshadowing_total"] == 300

    stored = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    assert len(stored.chapters) == 1000
    assert len(stored.plotlines) == 50
    assert len(stored.foreshadowing) == 300
