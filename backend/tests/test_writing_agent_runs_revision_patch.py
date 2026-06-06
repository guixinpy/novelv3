from app.models import ChapterContent, ChapterRevision
from test_support.writing_agent_run_helpers import (
    approved_apply_planner_revision_patch_tool,
    approved_create_revision_draft_tool,
    seed_longform_project,
)


def test_agent_apply_planner_revision_patch_updates_chapter_and_versions(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    draft = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=1)],
        },
    )
    revision_id = draft.json()["steps"][0]["output"]["revision_id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "应用planner修订",
            "tools": [
                approved_apply_planner_revision_patch_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    revision_id=revision_id,
                )
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=revision_id).one()
    assert response.status_code == 200
    assert output["status"] == "completed"
    assert output["revision_id"] == revision_id
    assert output["applied_replacement_count"] == 2
    assert "雾安局研究员" not in patched.content
    assert "制造幻觉" not in patched.content
    assert "雾港大学神经科学教授" in patched.content
    assert "扰乱雾中感知" in patched.content
    assert patched.word_count != 2000
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert output["should_generate_next_chapter"] is False


def test_agent_apply_planner_revision_patch_then_review_clears_drift_blockers(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    draft = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=1)],
        },
    )
    revision_id = draft.json()["steps"][0]["output"]["revision_id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "修订并复审",
            "tools": [
                approved_apply_planner_revision_patch_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    revision_id=revision_id,
                ),
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "character_profile_drift" not in codes
    assert "ability_boundary_drift" not in codes
    assert review["blocker_count"] == 0
