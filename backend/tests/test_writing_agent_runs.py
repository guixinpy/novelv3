from unittest.mock import AsyncMock, patch

from app.core.athena_longform import import_setup_to_world_model
from app.core.world_contracts import DERIVED
from app.core.world_proposal_service import create_bundle, write_candidate_fact
from app.models import (
    AIModelCallTrace,
    ChapterContent,
    ChapterRevision,
    Outline,
    Project,
    ProjectProfileVersion,
    RevisionAnnotation,
    RevisionCorrection,
    Setup,
    Storyline,
    WorldFactClaim,
    WorldProposalItem,
    WorldProposalReview,
    WritingAgentRun,
    WritingAgentStep,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate


def test_writing_agent_run_and_step_persist(client, db_session):
    project = Project(name="Agent Persist")
    db_session.add(project)
    db_session.flush()

    run = WritingAgentRun(
        project_id=project.id,
        goal="生成第2章",
        status="running",
        entrypoint="api",
        input={"chapter_index": 2},
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        AIModelCallTrace(id="trace-1", project_id=project.id, trace_type="chapter_generation", status="success")
    )
    step = WritingAgentStep(
        run_id=run.id,
        project_id=project.id,
        step_index=1,
        tool_name="generate_chapter",
        status="success",
        input={"params": {"chapter_index": 2}},
        output={"trace_id": "trace-1"},
        trace_id="trace-1",
        target_type="chapter",
        target_id="chapter-1",
        chapter_index=2,
    )
    db_session.add(step)
    db_session.commit()

    saved_run = db_session.query(WritingAgentRun).filter_by(project_id=project.id).one()
    saved_step = db_session.query(WritingAgentStep).filter_by(run_id=saved_run.id).one()

    assert saved_run.goal == "生成第2章"
    assert saved_run.input == {"chapter_index": 2}
    assert saved_step.tool_name == "generate_chapter"
    assert saved_step.output == {"trace_id": "trace-1"}


def test_create_agent_run_records_steps_and_returns_detail(client, db_session, monkeypatch):
    project_id = _create_project(client, "Agent API")
    _create_trace(db_session, project_id, "trace-setup", "setup_generation")

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": "trace-setup"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成设定",
            "tools": [{"tool_name": "generate_setup", "command_args": "城市悬疑"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["goal"] == "生成设定"
    assert len(payload["steps"]) == 1
    assert payload["steps"][0]["tool_name"] == "generate_setup"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["trace_id"] == "trace-setup"


def test_agent_run_list_and_detail_are_project_scoped(client, db_session):
    project_a = _create_project(client, "Project A")
    project_b = _create_project(client, "Project B")
    run = WritingAgentRun(project_id=project_a, goal="A run", status="success", entrypoint="api", input={})
    other_run = WritingAgentRun(project_id=project_b, goal="B run", status="success", entrypoint="api", input={})
    db_session.add_all([run, other_run])
    db_session.commit()

    listing = client.get(f"/api/v1/projects/{project_a}/agent-runs")
    detail = client.get(f"/api/v1/projects/{project_a}/agent-runs/{run.id}")
    cross_project_detail = client.get(f"/api/v1/projects/{project_b}/agent-runs/{run.id}")

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == run.id
    assert detail.status_code == 200
    assert detail.json()["id"] == run.id
    assert cross_project_detail.status_code == 404


def test_cancel_agent_run_marks_pending_or_running_run_cancelled(client, db_session):
    project_id = _create_project(client, "Cancel Project")
    run = WritingAgentRun(project_id=project_id, goal="cancel me", status="running", entrypoint="api", input={})
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project_id}/agent-runs/{run.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["finished_at"] is not None


def test_agent_run_records_successful_tool_step_with_trace_id(client, db_session, monkeypatch):
    project_id = _create_project(client, "Trace Project")
    _create_trace(db_session, project_id, "trace-storyline", "storyline_generation")

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": "trace-storyline"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成故事线",
            "tools": [{"tool_name": "generate_storyline", "command_args": "主线和支线"}],
        },
    )

    step = response.json()["steps"][0]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert step["trace_id"] == "trace-storyline"
    assert step["output"]["trace_id"] == "trace-storyline"


def test_agent_run_stops_after_failed_tool_step(client, db_session, monkeypatch):
    project_id = _create_project(client, "Fail Project")
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "failed", "error": "model unavailable"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "失败后停止",
            "tools": [
                {"tool_name": "generate_setup"},
                {"tool_name": "generate_storyline"},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "failed"
    assert payload["error"] == "model unavailable"
    assert [step["status"] for step in payload["steps"]] == ["failed"]
    assert calls == ["generate_setup"]


def test_agent_run_records_chapter_length_and_world_model_diagnostics(client, db_session, monkeypatch):
    project_id = _create_project(client, "Diagnostics Project")
    trace = AIModelCallTrace(
        project_id=project_id,
        trace_type="chapter_generation",
        status="success",
        chapter_index=2,
        trace_metadata={
            "chapter_word_target": {
                "status": "over",
                "actual_word_count": 3735,
                "target_min_word_count": 1700,
                "target_average_word_count": 2000,
                "target_max_word_count": 2300,
            }
        },
    )
    db_session.add(trace)
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": trace.id, "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成第2章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    length_decision = output["chapter_length_decision"]
    assert length_decision["status"] == "over"
    assert length_decision["decision"] == "accept_with_warning"
    assert length_decision["severity"] == "warning"
    assert length_decision["actual_word_count"] == 3735
    assert length_decision["target_min_word_count"] == 1700
    assert length_decision["target_average_word_count"] == 2000
    assert length_decision["target_max_word_count"] == 2300
    assert length_decision["repeated_drift_count"] == 0
    assert length_decision["recommended_actions"] == []
    assert output["world_model_proposal_diagnostic"]["status"] == "missing"
    assert output["world_model_proposal_diagnostic"]["reason"] == "missing_profile"


def test_agent_preflight_blocks_when_target_outline_is_missing(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [
                {"tool_name": "preflight_writing", "params": {"chapter_index": 3}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["error"] == "第3章缺少章节大纲。"
    assert payload["output"]["blocked_step_count"] == 1
    assert len(payload["steps"]) == 1
    step = payload["steps"][0]
    assert step["tool_name"] == "preflight_writing"
    assert step["status"] == "blocked"
    assert step["target_type"] == "preflight"
    assert step["chapter_index"] == 3
    assert step["output"]["status"] == "blocked"
    assert step["output"]["checks"]["outline_chapter"]["status"] == "missing"
    assert step["output"]["issues"][0]["code"] == "missing_outline_chapter"


def test_agent_preflight_ready_when_required_context_exists(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["checks"]["world_model_profile"]["status"] == "ready"
    assert output["checks"]["outline_chapter"]["status"] == "ready"
    assert output["checks"]["previous_chapter"]["status"] == "ready"


def test_agent_preflight_blocks_when_generated_chapter_outline_gap_exists(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第4章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 4}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["checks"]["historical_outline_gaps"]["status"] == "missing"
    assert output["checks"]["historical_outline_gaps"]["chapter_indexes"] == [2]
    assert output["issues"][0]["code"] == "missing_historical_outline_chapters"
    assert output["issues"][0]["suggested_tool"] == "backfill_outline_gaps"


def test_agent_backfill_outline_gaps_uses_existing_chapter_content_then_preflight_ready(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "回填历史大纲缺口并检查第4章",
            "tools": [
                {"tool_name": "backfill_outline_gaps", "params": {"before_chapter": 4}},
                {"tool_name": "preflight_writing", "params": {"chapter_index": 4}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["output"]["backfilled_chapter_indexes"] == [2]
    assert payload["steps"][1]["output"]["status"] == "ready"
    outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    assert [chapter["chapter_index"] for chapter in outline.chapters] == [1, 2, 3, 4]
    chapter_two = next(chapter for chapter in outline.chapters if chapter["chapter_index"] == 2)
    assert chapter_two["title"] == "雾港线索2"
    assert chapter_two["purpose"] == "根据已生成正文自动回填章节大纲。"


def test_agent_import_setup_world_model_creates_profile(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "导入世界模型",
            "tools": [{"tool_name": "import_setup_world_model"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["profile_version"] == 1
    assert db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).count() == 1


def test_agent_analyze_chapter_world_model_records_proposal_output(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "分析第1章",
            "tools": [{"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["chapter_index"] == 1
    assert output["created"]["proposal_items"] >= 1


def test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="chapter_generation",
        status="success",
        chapter_index=4,
        trace_metadata={
            "chapter_word_target": {
                "status": "within",
                "actual_word_count": 2100,
                "target_min_word_count": 1700,
                "target_average_word_count": 2000,
                "target_max_word_count": 2300,
            }
        },
    )
    db_session.add(trace)
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {
            "status": "success",
            "chapter_index": 4,
            "trace_id": trace.id,
            "athena_analysis": {
                "status": "completed",
                "chapter_index": 4,
                "proposal_bundle_id": "bundle-4",
                "created": {"proposal_items": 3},
                "updated": {"proposal_items": 0},
            },
        }

    def fail_duplicate_analysis(**_kwargs):
        raise AssertionError("duplicate analyze should have been skipped")

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fail_duplicate_analysis)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第4章并分析世界模型",
            "tools": [
                {"tool_name": "generate_chapter", "params": {"chapter_index": 4}},
                {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 4}},
            ],
        },
    )

    payload = response.json()
    analyze_output = payload["steps"][1]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert analyze_output["status"] == "skipped"
    assert analyze_output["reason"] == "chapter_already_analyzed_in_run"
    assert analyze_output["chapter_index"] == 4
    assert analyze_output["source_step_id"] == payload["steps"][0]["id"]
    assert analyze_output["proposal_bundle_id"] == "bundle-4"


def test_agent_chapter_length_decision_flags_repeated_over_target_drift(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3000
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="chapter_generation",
        status="success",
        chapter_index=3,
        trace_metadata={
            "chapter_word_target": {
                "status": "over",
                "actual_word_count": 3000,
                "target_min_word_count": 1700,
                "target_average_word_count": 2000,
                "target_max_word_count": 2300,
            }
        },
    )
    db_session.add(trace)
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": trace.id, "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第3章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 3}}],
        },
    )

    decision = response.json()["steps"][0]["output"]["chapter_length_decision"]
    assert response.status_code == 200
    assert decision["status"] == "over"
    assert decision["decision"] == "requires_policy_review"
    assert decision["severity"] == "warning"
    assert decision["repeated_drift_count"] == 3
    assert decision["policy_reason"] == "repeated_over_target"
    assert "revise_or_adjust_project_target" in decision["recommended_actions"]


def test_agent_preflight_blocks_when_repeated_over_target_drift_requires_review(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第4章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 4}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["checks"]["length_policy"]["status"] == "blocked"
    assert output["checks"]["length_policy"]["reason"] == "repeated_over_target"
    assert output["issues"][0]["code"] == "repeated_chapter_length_drift"


def test_agent_review_chapter_quality_flags_generic_title_and_length(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第2章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert {finding["code"] for finding in output["findings"]} >= {"generic_chapter_title", "chapter_over_target"}
    assert "revise_chapter" in output["recommended_actions"]


def test_agent_review_chapter_quality_flags_future_outline_overlap(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=3).one()
    chapter.title = "雾中童谣"
    chapter.content = "顾衍出现在地下实验室，警告他们不要靠近黑市雾晶。"
    chapter.word_count = 2000
    outline = db_session.query(Outline).filter_by(project_id=project.id).one()
    chapters = [dict(item) for item in outline.chapters]
    chapters[3]["title"] = "顾衍的警告"
    chapters[3]["summary"] = "顾衍现身并警告主角不要继续调查。"
    outline.chapters = chapters
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第3章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert any(finding["code"] == "future_outline_overlap" for finding in output["findings"])


def test_agent_plan_chapter_revision_maps_review_findings_to_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第2章修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    chapter_after_plan = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["should_generate_next_chapter"] is False
    assert {action["action"] for action in output["revision_actions"]} >= {
        "retitle_chapter",
        "compress_chapter",
    }
    assert "revise_chapter" in output["recommended_next_tools"]
    assert chapter_after_plan.content == original_content
    assert chapter_after_plan.title == "第2章"


def test_agent_plan_chapter_revision_records_revision_plan_target_type(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    step = response.json()["steps"][0]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert step["target_type"] == "revision_plan"
    assert step["output"]["status"] == "ready"
    assert step["output"]["should_generate_next_chapter"] is True


def test_agent_plan_chapter_revision_blocks_followup_generation_when_plan_is_blocked(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    db_session.commit()
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先规划第2章修订，再尝试生成第3章",
            "tools": [
                {"tool_name": "plan_chapter_revision", "params": {"chapter_index": 2}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "plan_chapter_revision"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_plan_chapter_revision_reports_world_model_pressure_without_reviewing_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    import_setup_to_world_model(db_session, project.id)
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="待审事实",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.phase8.agent.role",
            chapter_index=1,
            subject_ref="char.林深",
            predicate="role",
            object_ref_or_value="雾港调查者",
            claim_layer="truth",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.9,
            contract_version=profile.contract_version,
        ),
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章修订并检查世界模型压力",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "warning"
    assert output["world_model_proposal_pressure"]["total_items"] == 1
    assert "review_world_model_proposals" in output["recommended_next_tools"]
    assert stored_item.item_status == "pending"


def test_agent_review_world_model_proposals_reports_queue_without_reviewing_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase10.agent.role",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "汇总世界模型待审提案队列",
            "tools": [{"tool_name": "review_world_model_proposals", "params": {"limit": 20}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "world_model"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["total_items"] == 1
    assert output["returned_items"] == 1
    assert output["risk_counts"]["high"] == 1
    assert output["review_mode_counts"]["individual"] == 1
    assert output["clusters"][0]["item_ids"] == [item.id]
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_review_world_model_proposals_ready_when_queue_empty(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认世界模型待审提案队列为空",
            "tools": [{"tool_name": "review_world_model_proposals"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["total_items"] == 0
    assert output["risk_counts"] == {"high": 0, "medium": 0, "low": 0}
    assert output["review_mode_counts"] == {"individual": 0, "batch": 0}
    assert output["recommended_actions"] == ["preflight_writing"]
    assert output["should_generate_next_chapter"] is True


def test_agent_review_world_model_proposals_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase10.agent.status",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查提案队列后尝试生成第2章",
            "tools": [
                {"tool_name": "review_world_model_proposals", "params": {"limit": 20}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "review_world_model_proposals"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    high_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.status",
        predicate="status",
        subject_ref="char.林深",
    )
    low_item_one = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.mentioned-one",
        predicate="mentioned_in_chapter",
        subject_ref="char.林深",
    )
    low_item_two = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.mentioned-two",
        predicate="mentioned_in_chapter",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划世界模型待审提案解决顺序",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    steps = output["resolution_steps"]
    stored_high_item = db_session.query(WorldProposalItem).filter_by(id=high_item.id).one()
    stored_low_item_one = db_session.query(WorldProposalItem).filter_by(id=low_item_one.id).one()
    stored_low_item_two = db_session.query(WorldProposalItem).filter_by(id=low_item_two.id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "world_model"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["plan_only"] is True
    assert output["total_items"] == 3
    assert output["high_priority_step_count"] == 1
    assert output["batch_step_count"] == 1
    assert output["requires_human_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["should_generate_next_chapter"] is False
    assert steps[0]["action_type"] == "review_individual"
    assert steps[0]["risk_level"] == "high"
    assert steps[0]["item_ids"] == [high_item.id]
    assert steps[1]["action_type"] == "review_batch"
    assert steps[1]["risk_level"] == "low"
    assert set(steps[1]["item_ids"]) == {low_item_one.id, low_item_two.id}
    assert steps[1]["candidate_count"] == 2
    assert stored_high_item.item_status == "pending"
    assert stored_low_item_one.item_status == "pending"
    assert stored_low_item_two.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_plan_world_model_proposal_resolution_ready_when_queue_empty(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认无需解决世界模型提案",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["resolution_steps"] == []
    assert output["high_priority_step_count"] == 0
    assert output["batch_step_count"] == 0
    assert output["requires_human_confirmation"] is False
    assert output["can_auto_apply"] is False
    assert output["recommended_actions"] == ["preflight_writing"]
    assert output["should_generate_next_chapter"] is True


def test_agent_plan_world_model_proposal_resolution_keeps_full_batch_item_ids(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seeded_item_ids = []
    for index in range(12):
        item = _seed_pending_world_proposal(
            db_session,
            project_id=project.id,
            claim_id=f"claim.phase11.agent.batch-full-{index}",
            predicate="mentioned_in_chapter",
            subject_ref=f"char.batch-{index}",
        )
        seeded_item_ids.append(item.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划低风险批量提案",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    batch_step = output["resolution_steps"][0]
    assert response.status_code == 200
    assert batch_step["action_type"] == "review_batch"
    assert batch_step["candidate_count"] == 12
    assert set(batch_step["item_ids"]) == set(seeded_item_ids)


def test_agent_plan_world_model_proposal_resolution_counts_medium_separately_from_high(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.high-count",
        predicate="status",
        subject_ref="char.林深",
    )
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.medium-count",
        predicate="symbolic_hint",
        subject_ref="char.苏晚晴",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "区分高风险和中风险提案规划",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["high_priority_step_count"] == 1
    assert [step["risk_level"] for step in output["resolution_steps"]] == ["high", "medium"]


def test_agent_review_world_model_proposals_allows_resolution_plan_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.chain",
        predicate="role",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先看队列再规划解决顺序",
            "tools": [
                {"tool_name": "review_world_model_proposals", "params": {"limit": 20}},
                {"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "review_world_model_proposals",
        "plan_world_model_proposal_resolution",
    ]
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert payload["steps"][1]["output"]["should_generate_next_chapter"] is False
    assert payload["steps"][1]["output"]["resolution_steps"][0]["action_type"] == "review_individual"


def test_agent_plan_world_model_proposal_resolution_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.blocks-generation",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划提案解决后尝试生成第2章",
            "tools": [
                {"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "plan_world_model_proposal_resolution"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_create_revision_draft_from_plan_is_non_destructive(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "为第2章创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    chapter_after = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=revision.id).all()
    corrections = db_session.query(RevisionCorrection).filter_by(revision_id=revision.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "drafted"
    assert output["annotation_count"] >= 2
    assert output["correction_count"] == 0
    assert revision.status == "draft"
    assert revision.result_version_id is None
    assert corrections == []
    assert any("[PLAN_ACTION:retitle_chapter]" in item.comment for item in annotations)
    assert any("[PLAN_ACTION:compress_chapter]" in item.comment for item in annotations)
    assert chapter_after.content == original_content
    assert chapter_after.title == "第2章"


def test_agent_create_revision_draft_reuses_existing_draft(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    db_session.commit()

    first = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "为第2章创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )
    second = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "再次为第2章创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_output = first.json()["steps"][0]["output"]
    second_output = second.json()["steps"][0]["output"]
    assert first_output["revision_id"] == second_output["revision_id"]
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).count() == 1
    assert second_output["revision_index"] == 1


def test_agent_create_revision_draft_does_not_modify_manual_draft(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    revision = ChapterRevision(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_index=2,
        revision_index=1,
        status="draft",
    )
    db_session.add(revision)
    db_session.flush()
    db_session.add(
        RevisionAnnotation(
            revision_id=revision.id,
            paragraph_index=0,
            start_offset=0,
            end_offset=2,
            selected_text="林深",
            comment="用户手写批注",
        )
    )
    db_session.add(
        RevisionCorrection(
            revision_id=revision.id,
            paragraph_index=0,
            original_text="旧句",
            corrected_text="新句",
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "不要覆盖用户手写草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=revision.id).all()
    corrections = db_session.query(RevisionCorrection).filter_by(revision_id=revision.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["steps"][0]["output"]["reason"] == "existing_manual_draft"
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).count() == 1
    assert [item.comment for item in annotations] == ["用户手写批注"]
    assert corrections[0].corrected_text == "新句"


def test_agent_create_revision_draft_does_not_compete_with_submitted_revision(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    submitted = ChapterRevision(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_index=2,
        revision_index=1,
        status="submitted",
    )
    db_session.add(submitted)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "不要创建竞争修订",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["steps"][0]["output"]["reason"] == "existing_active_revision"
    revisions = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).all()
    assert len(revisions) == 1
    assert revisions[0].id == submitted.id
    assert revisions[0].status == "submitted"


def test_agent_create_revision_draft_skips_ready_chapter(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第1章是否需要修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "no_revision_actions"
    assert output["revision_id"] is None
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id).count() == 0


def test_agent_create_revision_draft_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    db_session.commit()
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第2章修订草稿后尝试生成第3章",
            "tools": [
                {"tool_name": "create_revision_draft", "params": {"chapter_index": 2}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "create_revision_draft"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_agent_expand_outline_window_adds_missing_outline_then_preflight_ready(
    mock_parse,
    mock_complete,
    mock_key,
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    mock_complete.return_value.content = "{}"
    mock_parse.return_value = {
        "total_chapters": 600,
        "chapters": [
            {
                "chapter_index": 3,
                "title": "诊所残影",
                "summary": "林深和苏晚晴追查记忆诊所。",
                "scenes": ["诊所门口", "档案室"],
                "characters": ["林深", "苏晚晴"],
                "purpose": "补齐第3章大纲",
            }
        ],
    }

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "补齐第3章大纲并检查可写性",
            "tools": [
                {
                    "tool_name": "expand_outline_window",
                    "params": {"start_chapter": 3, "end_chapter": 3, "command_args": "补齐第3章"},
                },
                {"tool_name": "preflight_writing", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["tool_name"] == "expand_outline_window"
    assert payload["steps"][0]["output"]["added_chapter_count"] == 1
    assert payload["steps"][1]["output"]["status"] == "ready"
    outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    assert [chapter["chapter_index"] for chapter in outline.chapters] == [1, 2, 3]


def _create_project(client, name: str) -> str:
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 200
    return response.json()["id"]


def _create_trace(db_session, project_id: str, trace_id: str, trace_type: str) -> None:
    db_session.add(AIModelCallTrace(id=trace_id, project_id=project_id, trace_type=trace_type, status="success"))
    db_session.commit()


def _seed_pending_world_proposal(
    db_session,
    *,
    project_id: str,
    claim_id: str,
    predicate: str,
    subject_ref: str,
) -> WorldProposalItem:
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="待审事实",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id=claim_id,
            chapter_index=1,
            subject_ref=subject_ref,
            predicate=predicate,
            object_ref_or_value="雾港调查者",
            claim_layer="truth",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.9,
            contract_version=profile.contract_version,
        ),
    )
    db_session.commit()
    return item


def _seed_longform_project(db_session, *, outline_chapters: list[int], generated_chapters: list[int]) -> Project:
    project = Project(
        name="Preflight Novel",
        genre="都市悬疑",
        target_chapter_count=600,
        target_word_count=1200000,
    )
    db_session.add(project)
    db_session.flush()
    setup = Setup(
        project_id=project.id,
        status="generated",
        world_building={
            "background": "雾港被记忆异常和雾晶实验影响。",
            "geography": "故事发生在‘雾港’和‘旧灯塔’，地下实验室藏有‘雾晶核心’。",
            "society": "‘雾安局’控制异常档案，‘记忆诊所’收容失忆者。",
            "rules": "雾晶只能放大记忆回声，不能凭空创造真实记忆。",
        },
        characters=[
            {
                "name": "林深",
                "personality": "冷静",
                "background": "私家侦探",
                "goals": "查清十年前雾灾真相",
                "character_status": "alive",
            },
            {
                "name": "苏晚晴",
                "personality": "敏锐",
                "background": "失踪者家属",
                "goals": "找到父亲",
                "character_status": "alive",
            },
        ],
        core_concept={"theme": "记忆与真相", "hook": "雾港会回放被删除的记忆"},
    )
    db_session.add(setup)
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查雾港记忆异常", "milestones": []}],
            foreshadowing=[],
        )
    )
    outline = Outline(
        project_id=project.id,
        total_chapters=600,
        status="generated",
        chapters=[
            {
                "chapter_index": index,
                "title": f"雾港线索{index}",
                "summary": f"第{index}章推进雾港记忆异常调查。",
                "scenes": ["调查现场", "冲突升级"],
                "characters": ["林深", "苏晚晴"],
                "purpose": "推进主线",
            }
            for index in outline_chapters
        ],
        plotlines=[],
        foreshadowing=[],
    )
    db_session.add(outline)
    for index in generated_chapters:
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"雾港线索{index}",
                content=f"林深和苏晚晴在雾港旧灯塔调查雾晶核心。第{index}章里，雾安局巡逻队逼近，记忆诊所留下新的证词。",
                word_count=80,
                status="generated",
            )
        )
    db_session.commit()
    db_session.refresh(project)
    return project
