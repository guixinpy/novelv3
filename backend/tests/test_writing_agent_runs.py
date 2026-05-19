import json
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
    Version,
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
                "target_min_word_count": 2000,
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
    assert length_decision["target_min_word_count"] == 2000
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


def test_agent_preflight_reports_previous_chapter_state_card(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "空白信的秘密"
    chapter.content = "林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。"
    chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    card = output["checks"]["previous_chapter_state_card"]
    assert response.status_code == 200
    assert card["status"] == "ready"
    assert card["chapter_index"] == 1
    assert card["title"] == "空白信的秘密"
    assert "雾晶是钥匙" in card["last_excerpt"]
    assert "空白信" in card["key_terms"]
    assert "下城" in card["key_terms"]


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
                "target_min_word_count": 2000,
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
                "target_min_word_count": 2000,
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


def test_agent_preflight_warns_when_repeated_over_target_drift_requires_review(client, db_session):
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
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["checks"]["length_policy"]["status"] == "review_required"
    assert output["checks"]["length_policy"]["reason"] == "repeated_over_target"
    assert output["issues"][0]["code"] == "repeated_chapter_length_drift"
    assert output["issues"][0]["severity"] == "warning"


def test_agent_preflight_keeps_historical_length_debt_out_of_recent_drift_warning(client, db_session):
    project = _seed_longform_project(
        db_session,
        outline_chapters=list(range(1, 10)),
        generated_chapters=list(range(1, 9)),
    )
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3000 if chapter.chapter_index <= 3 else 2100
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第9章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 9}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    length_policy = output["checks"]["length_policy"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert length_policy["status"] == "ready"
    assert length_policy["historical_over_target_count"] == 3
    assert length_policy["recent_over_target_count"] == 0
    assert [issue["code"] for issue in output["issues"]] == []


def test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3000
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["action_type"] = action_type
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 4}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第4章",
            "tools": [
                {
                    "tool_name": "generate_chapter",
                    "command_args": "保留悬疑压迫感",
                    "params": {"chapter_index": 4},
                }
            ],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert captured["action_type"] == "generate_chapter"
    assert "保留悬疑压迫感" in command_args
    assert "近期章节连续偏长" in command_args
    assert "2000-2300字" in command_args
    assert output["agent_generation_feedback"]["reason"] == "repeated_over_target"


def test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 1200
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 4}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第4章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 4}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "近期章节连续偏短" in command_args
    assert "2000-2300字" in command_args
    assert output["agent_generation_feedback"]["reason"] == "repeated_under_target"


def test_agent_generate_chapter_ignores_old_over_target_debt_when_recent_window_is_clean(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(
        db_session,
        outline_chapters=list(range(1, 10)),
        generated_chapters=list(range(1, 9)),
    )
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3000 if chapter.chapter_index <= 3 else 2100
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 9}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第9章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 9}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "近期章节连续偏长" not in command_args
    assert "agent_generation_feedback" not in output


def test_agent_generate_chapter_ignores_old_under_target_debt_when_recent_window_is_clean(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(
        db_session,
        outline_chapters=list(range(1, 10)),
        generated_chapters=list(range(1, 9)),
    )
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 1200 if chapter.chapter_index <= 3 else 2100
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 9}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第9章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 9}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "近期章节连续偏短" not in command_args
    assert "agent_generation_feedback" not in output


def test_agent_generate_chapter_appends_previous_state_card(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "空白信的秘密"
    chapter.content = "林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。"
    chapter.word_count = 2000
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第2章",
            "tools": [
                {
                    "tool_name": "generate_chapter",
                    "command_args": "保持紧张感",
                    "params": {"chapter_index": 2},
                }
            ],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert "保持紧张感" in command_args
    assert "上一章状态卡" in command_args
    assert "空白信的秘密" in command_args
    assert "雾晶是钥匙" in command_args
    assert "下城" in command_args
    assert output["agent_continuity_feedback"]["card"]["title"] == "空白信的秘密"


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


def test_agent_review_chapter_quality_warns_on_modest_over_target_length(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "雾中回声"
    chapter.word_count = 2482
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    over_finding = next(finding for finding in output["findings"] if finding["code"] == "chapter_over_target")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "warning"
    assert over_finding["severity"] == "warning"
    assert "revise_chapter" not in output["recommended_actions"]


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


def test_agent_review_chapter_quality_ignores_single_future_character_name_match(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=3).one()
    chapter.title = "雾中童谣"
    chapter.content = "林深接到苏晚晴的电话，两人只确认了旧码头的见面时间。"
    chapter.word_count = 2000
    outline = db_session.query(Outline).filter_by(project_id=project.id).one()
    chapters = [dict(item) for item in outline.chapters]
    chapters[3]["title"] = "苏晚晴的梦境"
    chapters[3]["summary"] = "苏晚晴在梦境里看见雾港旧案的另一段证词。"
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
    assert output["status"] == "ready"
    assert all(finding["code"] != "future_outline_overlap" for finding in output["findings"])


def test_agent_review_chapter_quality_flags_character_profile_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员，只是一直隐瞒身份。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "character_profile_drift")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["character"] == "苏晚晴"
    assert "失踪者家属" in finding["evidence"]["known_profile"]


def test_agent_review_chapter_quality_flags_ability_boundary_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴抬手制造幻觉，凭空创造出一段真实记忆骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "ability_boundary_drift")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert "制造幻觉" in finding["evidence"]["matched_terms"]


def test_agent_review_chapter_quality_warns_on_convenient_key_item_acquisition(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "老赵看了林深一眼，立刻把稀有记忆雾晶给了他，让他们马上离开。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "convenient_key_item_acquisition")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert "记忆雾晶" in finding["evidence"]["matched_terms"]


def test_agent_review_chapter_quality_flags_unclosed_quote_tail(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "信任裂缝"
    chapter.content = "林深走进雾中，听见父亲的声音响起——“林深，好久不见。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "unclosed_dialogue_quote")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"


def test_agent_review_chapter_continuity_flags_event_date_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "信封上的邮戳日期是2045年8月9日——雾灾发生前三天。"
    first.word_count = 2000
    second.content = "林深看了看信封上的邮戳——2045年7月12日。那是雾灾发生的前三天。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章连续性锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    payload = response.json()
    step = payload["steps"][0]
    output = step["output"]
    finding = output["findings"][0]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert step["status"] == "success"
    assert step["target_type"] == "review"
    assert output["status"] == "blocked"
    assert finding["code"] == "timeline_anchor_conflict"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["event_key"] == "fog_disaster_minus_3_days"
    assert finding["evidence"]["values"] == ["2045年8月9日", "2045年7月12日"]


def test_agent_review_chapter_continuity_flags_identifier_kind_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "顾衍把军牌扔在桌上，上面刻着编号：N-017。"
    first.word_count = 2000
    second.content = "顾衍掏出军牌，翻到背面。上面刻着一串编号——N-07。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert output["status"] == "blocked"
    assert finding["code"] == "identifier_anchor_conflict"
    assert finding["evidence"]["anchor_key"] == "顾衍:military_tag_number"
    assert finding["evidence"]["values"] == ["N-017", "N-07"]


def test_agent_review_chapter_continuity_allows_experiment_code_distinction(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "顾衍把军牌扔在桌上，上面刻着编号：N-017。"
    first.word_count = 2000
    second.content = "顾衍掏出军牌，正面的编号仍是N-017；背面浮出暗纹——N-07。那不是军牌编号，更像实验代号。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["status"] == "ready"
    assert output["finding_count"] == 0


def test_agent_review_chapter_continuity_flags_relationship_name_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "名单第一是林建国——他父亲的名字。"
    first.word_count = 2000
    second.content = "空白信背面浮出署名——林远山。林深认出那是父亲留下的字迹。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章关系姓名锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["code"] == "relationship_name_anchor_conflict"
    assert finding["evidence"]["anchor_key"] == "林深:father_name"
    assert finding["evidence"]["values"] == ["林建国", "林远山"]


def test_agent_review_chapter_continuity_blocks_against_confirmed_father_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.father-name",
        subject_ref="林深",
        predicate="father_name",
        object_ref_or_value="林建国",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "空白信背面浮出署名——林远山。林深认出那是父亲留下的字迹。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定父亲姓名锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "stable_truth_anchor_conflict")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["anchor_key"] == "林深:father_name"
    assert finding["evidence"]["truth_value"] == "林建国"
    assert finding["evidence"]["observed_values"] == ["林远山"]


def test_agent_review_chapter_continuity_blocks_against_confirmed_military_tag_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.guyan.military-tag",
        subject_ref="顾衍",
        predicate="military_tag_number",
        object_ref_or_value="N-017",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "顾衍掏出军牌，翻到背面。上面刻着一串编号——N-07。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定军牌锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "stable_truth_anchor_conflict")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["evidence"]["anchor_key"] == "顾衍:military_tag_number"
    assert finding["evidence"]["truth_value"] == "N-017"
    assert finding["evidence"]["observed_values"] == ["N-07"]


def test_agent_review_chapter_continuity_blocks_against_confirmed_relative_event_date_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.fog-disaster-minus-3-days",
        subject_ref="event.fog_disaster.minus_3_days",
        predicate="relative_event_date",
        object_ref_or_value="2045年8月9日",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "信封上的邮戳日期是2045年8月12日——雾灾发生前三天。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定雾灾日期锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "stable_truth_anchor_conflict")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["evidence"]["anchor_key"] == "fog_disaster_minus_3_days"
    assert finding["evidence"]["truth_value"] == "2045年8月9日"
    assert finding["evidence"]["observed_values"] == ["2045年8月12日"]


def test_agent_seed_continuity_anchor_proposals_creates_missing_anchor_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "补齐稳定连续性锚点提案",
            "tools": [{"tool_name": "seed_continuity_anchor_proposals"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_items = db_session.query(WorldProposalItem).filter_by(project_id=project.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["created_item_count"] >= 5
    assert output["should_generate_next_chapter"] is False
    assert {(item.subject_ref, item.predicate) for item in stored_items} >= {
        ("林深", "father_name"),
        ("顾衍", "military_tag_number"),
        ("identifier.N-07", "identifier_meaning"),
        ("event.fog_disaster", "event_date"),
        ("event.fog_disaster.minus_3_days", "relative_event_date"),
    }


def test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={"goal": "seed", "tools": [{"tool_name": "seed_continuity_anchor_proposals"}]},
    )
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="林深", predicate="father_name")
        .one()
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审批稳定锚点",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "approve",
                                "reason": "确认父亲姓名锚点",
                                "evidence_refs": ["chapter:10", "chapter:11", "chapter:13"],
                            }
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    db_session.expire_all()
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    stored_claim = db_session.query(WorldFactClaim).filter_by(project_id=project.id, predicate="father_name").one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["applied_count"] == 1
    assert output["after_actionable_items"] == 4
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "approved"
    assert stored_item.approved_claim_id == stored_claim.claim_id
    assert stored_claim.subject_ref == "林深"
    assert stored_claim.object_ref_or_value == "林建国"


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


def test_agent_plan_chapter_revision_maps_drift_findings_to_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章漂移修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    actions = {action["action"]: action for action in output["revision_actions"]}
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert "fix_character_profile_drift" in actions
    assert "respect_ability_boundary" in actions
    assert actions["fix_character_profile_drift"]["source_finding"] == "character_profile_drift"
    assert actions["respect_ability_boundary"]["source_finding"] == "ability_boundary_drift"
    assert actions["fix_character_profile_drift"]["evidence"]["character"] == "苏晚晴"
    assert "制造幻觉" in actions["respect_ability_boundary"]["evidence"]["matched_terms"]


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


def test_agent_preview_world_model_proposal_resolution_validates_decisions_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    approve_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.approve",
        predicate="role",
        subject_ref="char.林深",
    )
    reject_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.reject",
        predicate="mentioned_in_chapter",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览世界模型提案解决决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": approve_item.id,
                                "action": "approve",
                                "reason": "确认角色定位",
                                "evidence_refs": ["test:phase12"],
                            },
                            {
                                "proposal_item_id": reject_item.id,
                                "action": "reject",
                                "reason": "仅作预览拒绝",
                                "evidence_refs": "test:phase12:string-ref",
                            },
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_approve_item = db_session.query(WorldProposalItem).filter_by(id=approve_item.id).one()
    stored_reject_item = db_session.query(WorldProposalItem).filter_by(id=reject_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["preview_only"] is True
    assert output["requires_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["valid_decision_count"] == 2
    assert output["invalid_decision_count"] == 0
    assert output["would_create_review_count"] == 2
    assert output["would_create_fact_count"] == 1
    assert output["would_resolve_item_count"] == 2
    assert output["remaining_actionable_item_count_after_preview"] == 0
    assert output["would_unblock_generation"] is True
    assert output["should_generate_next_chapter"] is False
    reject_preview = next(decision for decision in output["valid_decisions"] if decision["proposal_item_id"] == reject_item.id)
    assert reject_preview["evidence_refs"] == ["test:phase12:string-ref"]
    assert stored_approve_item.item_status == "pending"
    assert stored_reject_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_preview_world_model_proposal_resolution_reports_missing_profile_for_non_dict_decision(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "缺少世界模型档案时预览异常决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {"decisions": ["not-a-decision"]},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "missing_profile"
    assert output["valid_decision_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "missing_profile"
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_reports_invalid_decisions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.valid",
        predicate="role",
        subject_ref="char.林深",
    )
    unsupported_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.unsupported",
        predicate="status",
        subject_ref="char.苏晚晴",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览无效世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "有效拒绝预览",
                            },
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "重复决策",
                            },
                            {
                                "proposal_item_id": "proposal-item.missing.phase12",
                                "action": "approve",
                                "reason": "不存在",
                            },
                            {
                                "proposal_item_id": unsupported_item.id,
                                "action": "split",
                                "reason": "不支持的动作",
                            },
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    invalid_codes = {item["code"] for item in output["invalid_decisions"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["valid_decision_count"] == 1
    assert output["invalid_decision_count"] == 3
    assert invalid_codes == {"duplicate_decision", "missing_item", "unsupported_action"}
    assert output["remaining_actionable_item_count_after_preview"] == 1
    assert output["would_unblock_generation"] is False
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_reports_non_actionable_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.non-actionable",
        predicate="role",
        subject_ref="char.林深",
    )
    item.item_status = "approved"
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览非待审世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "已经不是待审项",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["valid_decision_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "non_actionable_item"
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_blocks_generation_for_empty_queue_decisions(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "空队列下预览无效决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": "proposal-item.missing.empty-queue",
                                "action": "reject",
                                "reason": "不存在",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["invalid_decision_count"] == 1
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_rejects_non_atomized_world_intake_approve(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    intake_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.world-intake",
        predicate="user_proposed_update",
        subject_ref="project.world_intake",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览未原子化世界入口提案",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": intake_item.id,
                                "action": "approve",
                                "reason": "直接审批入口提案",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["valid_decision_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "world_intake_not_atomized"
    assert output["should_generate_next_chapter"] is False


def test_agent_plan_world_model_proposal_resolution_allows_preview_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.plan-preview",
        predicate="role",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先规划再预览世界模型提案决策",
            "tools": [
                {"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}},
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览拒绝",
                            }
                        ]
                    },
                },
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
    ]
    assert payload["steps"][1]["output"]["valid_decision_count"] == 1


def test_agent_preview_world_model_proposal_resolution_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.blocks-generation",
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
            "goal": "预览提案决策后尝试生成第2章",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览拒绝",
                            }
                        ]
                    },
                },
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "preview_world_model_proposal_resolution"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.needs-confirm",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试未确认地应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "未确认，不应落库",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["requires_confirmation"] is True
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 0
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_apply_world_model_proposal_resolution_blocks_missing_profile_without_decisions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "缺少世界模型档案时不能应用空决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {"confirm_apply": True, "decisions": []},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "missing_profile"
    assert output["applied_count"] == 0
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_actions"] == ["import_setup_world_model"]


def test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    reject_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.reject",
        predicate="role",
        subject_ref="char.林深",
    )
    uncertain_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.uncertain",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认应用世界模型非合并提案决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": reject_item.id,
                                "action": "reject",
                                "reason": "拒绝错误角色事实",
                                "evidence_refs": ["test:phase13"],
                            },
                            {
                                "proposal_item_id": uncertain_item.id,
                                "action": "mark_uncertain",
                                "reason": "状态暂不确定",
                                "evidence_refs": "test:phase13:string-ref",
                            },
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    db_session.expire_all()
    stored_reject_item = db_session.query(WorldProposalItem).filter_by(id=reject_item.id).one()
    stored_uncertain_item = db_session.query(WorldProposalItem).filter_by(id=uncertain_item.id).one()
    reviews = (
        db_session.query(WorldProposalReview)
        .filter(WorldProposalReview.proposal_item_id.in_([reject_item.id, uncertain_item.id]))
        .all()
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["applied_count"] == 2
    assert output["before_actionable_items"] == 2
    assert output["after_actionable_items"] == 0
    assert output["should_generate_next_chapter"] is True
    assert db_session.query(WorldFactClaim).count() == before_fact_count
    assert stored_reject_item.item_status == "rejected"
    assert stored_uncertain_item.item_status == "uncertain"
    assert {review.review_action for review in reviews} == {"reject", "mark_uncertain"}
    assert {review.reviewer_ref for review in reviews} == {"writing_agent.phase13"}


def test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.approve-refused",
        predicate="role",
        subject_ref="char.林深",
    )
    edit_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.approve-edits-refused",
        predicate="role",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试在守卫应用中审批事实",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "approve",
                                "reason": "本阶段不允许",
                            },
                            {
                                "proposal_item_id": edit_item.id,
                                "action": "approve_with_edits",
                                "reason": "本阶段同样不允许",
                                "edited_fields": {"object_ref_or_value": "雾港协作者"},
                            }
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 2
    assert {item["code"] for item in output["invalid_decisions"]} == {"approval_not_supported_in_guarded_apply"}
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_apply_world_model_proposal_resolution_rolls_back_when_review_stage_fails(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.rollback-valid",
        predicate="role",
        subject_ref="char.林深",
    )
    drift_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.rollback-drift",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    drift_item.contract_version = "drifted-contract-version"
    db_session.commit()
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "第二条评审阶段失败时整批回滚",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "第一条本应回滚",
                            },
                            {
                                "proposal_item_id": drift_item.id,
                                "action": "mark_uncertain",
                                "reason": "合约版本漂移导致评审阶段失败",
                            },
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    db_session.expire_all()
    stored_valid_item = db_session.query(WorldProposalItem).filter_by(id=valid_item.id).one()
    stored_drift_item = db_session.query(WorldProposalItem).filter_by(id=drift_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "apply_failed"
    assert stored_valid_item.item_status == "pending"
    assert stored_drift_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.valid-batch",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "无效批次不能部分应用",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "有效但不应部分落库",
                            },
                            {
                                "proposal_item_id": "proposal-item.missing.phase13",
                                "action": "mark_uncertain",
                                "reason": "缺失项导致整批阻断",
                            },
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_valid_item = db_session.query(WorldProposalItem).filter_by(id=valid_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "missing_item"
    assert stored_valid_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_preview_world_model_proposal_resolution_allows_apply_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.preview-apply",
        predicate="role",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先预览再确认应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览后确认拒绝",
                            }
                        ]
                    },
                },
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览后确认拒绝",
                            }
                        ],
                    },
                },
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
    ]
    assert payload["steps"][1]["output"]["applied_count"] == 1


def test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item_to_apply = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.apply-one",
        predicate="role",
        subject_ref="char.林深",
    )
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.remains",
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
            "goal": "应用部分提案后尝试生成第2章",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item_to_apply.id,
                                "action": "reject",
                                "reason": "只处理一个，仍有待审项",
                            }
                        ],
                    },
                },
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "apply_world_model_proposal_resolution"
    assert payload["steps"][0]["output"]["after_actionable_items"] == 1
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.clears",
        predicate="role",
        subject_ref="char.林深",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "清空提案队列后生成第2章",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "清空队列",
                            }
                        ],
                    },
                },
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "apply_world_model_proposal_resolution",
        "generate_chapter",
    ]
    assert calls == ["generate_chapter"]


def test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    presence_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.presence",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    location_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.location",
        predicate="present_at_location",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟低风险世界模型提案决策",
            "tools": [{"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_presence = db_session.query(WorldProposalItem).filter_by(id=presence_item.id).one()
    stored_location = db_session.query(WorldProposalItem).filter_by(id=location_item.id).one()
    actions = {decision["proposal_item_id"]: decision["action"] for decision in output["draft_decisions"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["draft_decision_count"] == 2
    assert actions[presence_item.id] == "reject"
    assert actions[location_item.id] == "mark_uncertain"
    assert output["requires_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["should_generate_next_chapter"] is False
    assert stored_presence.item_status == "pending"
    assert stored_location.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_draft_world_model_proposal_resolution_decisions_tracks_unclassified_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.custom",
        predicate="custom_truth",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟未知谓词提案决策",
            "tools": [
                {
                    "tool_name": "draft_world_model_proposal_resolution_decisions",
                    "params": {"limit": 20, "include_unclassified": True},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["draft_decision_count"] == 0
    assert output["unclassified_item_count"] == 1
    assert output["unclassified_items"][0]["predicate"] == "custom_truth"
    assert output["recommended_next_tools"] == ["plan_world_model_proposal_resolution"]


def test_agent_draft_world_model_proposal_resolution_decisions_ignores_approval_policy_overrides(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.custom-approval-policy",
        predicate="custom_truth",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "忽略自定义审批草案策略",
            "tools": [
                {
                    "tool_name": "draft_world_model_proposal_resolution_decisions",
                    "params": {
                        "limit": 20,
                        "include_unclassified": True,
                        "predicate_policies": {
                            "custom_truth": {
                                "action": "approve_with_edits",
                                "reason": "不允许草拟审批",
                            }
                        },
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["draft_decision_count"] == 0
    assert output["unclassified_item_count"] == 1
    assert output["unclassified_items"][0]["predicate"] == "custom_truth"


def test_agent_draft_world_model_proposal_resolution_decisions_allows_apply_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.chain",
        predicate="presence_count",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先草拟再应用世界模型提案决策",
            "tools": [
                {"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}},
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "presence_count 是提取元数据，不进入真相层",
                            }
                        ],
                    },
                },
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "draft_world_model_proposal_resolution_decisions",
        "apply_world_model_proposal_resolution",
    ]
    assert payload["steps"][1]["output"]["applied_count"] == 1


def test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.blocks-generation",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟提案决策后尝试生成第2章",
            "tools": [
                {"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "draft_world_model_proposal_resolution_decisions"
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


def test_agent_create_revision_draft_anchors_drift_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第1章漂移修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=output["revision_id"]).all()
    comments = [annotation.comment or "" for annotation in annotations]
    selected = [annotation.selected_text or "" for annotation in annotations]
    assert response.status_code == 200
    assert output["status"] == "drafted"
    assert output["annotation_count"] == 2
    assert any("[PLAN_ACTION:fix_character_profile_drift]" in comment for comment in comments)
    assert any("[PLAN_ACTION:respect_ability_boundary]" in comment for comment in comments)
    assert any("雾安局研究员" in text for text in selected)
    assert any("制造幻觉" in text for text in selected)
    assert db_session.query(ChapterContent).filter_by(id=chapter.id).one().content == original_content


def test_agent_apply_planner_revision_patch_updates_chapter_and_versions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    draft = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )
    revision_id = draft.json()["steps"][0]["output"]["revision_id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "应用planner修订",
            "tools": [{"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 1}}],
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
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "修订并复审",
            "tools": [
                {"tool_name": "create_revision_draft", "params": {"chapter_index": 1}},
                {"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][2]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "character_profile_drift" not in codes
    assert "ability_boundary_drift" not in codes
    assert review["blocker_count"] == 0


def test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "苏晚晴的梦境"
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    project.current_word_count = 600
    db_session.commit()

    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            assert "不要新增世界模型事实" in messages[-1]["content"]
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写第1章到目标字数",
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    versions = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["previous_word_count"] == 600
    assert output["word_count"] >= 2000
    assert patched.content == expanded_content
    assert patched.word_count >= 2000
    db_session.refresh(project)
    assert project.current_word_count == patched.word_count
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert len(versions) == 2
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["review_chapter_quality"]


def test_agent_expand_chapter_to_target_then_review_clears_under_target_warning(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "苏晚晴的梦境"
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    db_session.commit()
    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写并复审",
            "tools": [
                {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_under_target" not in codes
    assert review["blocker_count"] == 0


def test_agent_expand_chapter_to_target_blocks_direct_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    db_session.commit()
    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写后直接生成下一章",
            "tools": [
                {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["expand_chapter_to_target"]
    assert calls == []


def test_agent_expand_chapter_to_target_skips_when_chapter_already_at_target(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    chapter.word_count = 2100
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called for an already-target chapter")

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写已达标章节",
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_at_target"
    assert output["should_generate_next_chapter"] is True
    assert calls == []


def test_agent_expand_chapter_to_target_blocks_pending_world_model_proposals(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase21.pending",
        predicate="role",
        subject_ref="char.林深",
    )
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called when world proposals are pending")

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "存在世界模型提案时扩写",
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "pending_world_model_proposals"
    assert output["pending_world_model_proposal_count"] == 1
    assert calls == []


def test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "废弃实验室"
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()

    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            assert "压缩到目标字数范围" in messages[-1]["content"]
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章到目标字数",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    versions = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).all()
    db_session.refresh(project)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["previous_word_count"] == 3000
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content == compressed_content.strip()
    assert 2000 <= patched.word_count <= 2300
    assert project.current_word_count == patched.word_count
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert len(versions) == 2
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["review_chapter_quality"]


def test_agent_compress_chapter_to_target_then_review_clears_over_target_warning(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "废弃实验室"
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    db_session.commit()
    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩并复审",
            "tools": [
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_over_target" not in codes
    assert "chapter_under_target" not in codes
    assert review["blocker_count"] == 0


def test_agent_compress_chapter_to_target_blocks_direct_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    db_session.commit()
    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩后直接生成下一章",
            "tools": [
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["compress_chapter_to_target"]
    assert calls == []


def test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    chapter.word_count = 2100
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called for an already-target chapter")

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩已达标章节",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_within_target"
    assert calls == []


def test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase22.pending",
        predicate="role",
        subject_ref="char.林深",
    )
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called when world proposals are pending")

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "存在世界模型提案时压缩",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "pending_world_model_proposals"
    assert output["pending_world_model_proposal_count"] == 1
    assert calls == []


def test_agent_compress_chapter_to_target_repairs_under_target_retry(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗河引路"
    chapter.content = "林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()

    too_short = "林深和苏晚晴沿着暗河追查线索。 " * 80
    repaired = "林深和苏晚晴沿着暗河追查雾晶管线，确认警报来源。 " * 100
    calls = []

    class FakeAIResult:
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

        def __init__(self, content):
            self.content = json.dumps({"content": content, "change_summary": "压缩并恢复场景密度。"}, ensure_ascii=False)

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult(too_short if len(calls) == 1 else repaired)

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并修复过短候选",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    traces = (
        db_session.query(AIModelCallTrace)
        .filter_by(project_id=project.id, trace_type="chapter_compression", chapter_index=1)
        .order_by(AIModelCallTrace.created_at.asc(), AIModelCallTrace.id.asc())
        .all()
    )
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 2
    assert len(output["failed_attempts"]) == 1
    assert output["failed_attempts"][0]["direction"] == "under_target"
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content == repaired.strip()
    assert revision_count == 1
    assert version_count == 2
    assert len(calls) == 2
    assert "上一次压缩结果低于目标下限" in calls[1]
    assert [trace.status for trace in traces] == ["failed", "success"]


def test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    original_content = "林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120
    chapter.content = original_content
    chapter.word_count = 3000
    db_session.commit()

    too_short = "林深和苏晚晴沿着暗河追查线索。 " * 80
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": too_short, "change_summary": "仍然过短。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章但候选持续过短",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "compressed_content_outside_target"
    assert output["compression_attempt_count"] == 3
    assert len(output["failed_attempts"]) == 3
    assert len(calls) == 3
    assert patched.content == original_content
    assert revision_count == 0
    assert version_count == 0


def test_agent_compress_chapter_to_target_repairs_near_target_candidate_from_source(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    source_sentences = [
        "他把旧号码牌贴进证物袋，确认暗河另一端仍有回声。",
        "苏晚晴在墙面找到被水泡开的蓝色封条。",
        "林深听见管道深处传来三短一长的敲击。",
        "两人把警报频率记进随身本，准备回到灯塔核对。",
        "陈默留下的旧坐标在纸背浮出，指向下游闸门。",
        "雾晶管线旁的冷光忽明忽暗，像在回应失踪者的低语。",
    ]
    source_text = "".join(source_sentences)
    chapter.content = ("林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120) + source_text
    chapter.word_count = 3050
    project.current_word_count = 3050
    db_session.commit()

    almost_enough = "林深和苏晚晴沿着暗河追查雾晶管线，确认警报来源。 " * 85
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": almost_enough, "change_summary": "轻量压缩。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并用源文恢复轻微缺口",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 1
    assert output["deterministic_repair_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert any(sentence in patched.content for sentence in source_sentences)
    assert len(calls) == 1


def test_agent_compress_chapter_to_target_trims_near_over_target_candidate(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    opening = "林深握紧灯塔钥匙，确认暗河入口没有被封死。"
    ending = "苏晚晴把号码牌压在掌心，决定回到灯塔核对名单。"
    middle = [f"他们沿着潮湿管道继续记录第{i}处雾晶回声。" for i in range(120)]
    over_target_candidate = opening + "".join(middle) + ending
    chapter.content = over_target_candidate
    chapter.word_count = 2433
    project.current_word_count = 2433
    db_session.commit()
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": over_target_candidate, "change_summary": "模型返回原稿。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并裁剪轻微超长候选",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 1
    assert output["deterministic_trim_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert opening in patched.content
    assert ending in patched.content
    assert len(calls) == 1


def test_agent_compress_chapter_to_target_trims_large_over_target_candidate(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    opening = "林深推开第三研究所的铁门，确认门缝里还压着空白信纸。"
    protected_dialogue = "“别碰那张纸。”苏晚晴按住他的手，“雾晶反应还在。”"
    ending = "门后的红灯重新亮起，林深知道名单上的下一个名字已经出现。"
    low_signal = [f"潮湿走廊里回声第{i}次拉长，墙皮落下细小灰尘。" for i in range(135)]
    candidate = opening + protected_dialogue + "".join(low_signal) + ending
    chapter.content = candidate
    chapter.word_count = 2878
    project.current_word_count = 2878
    db_session.commit()
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": candidate, "change_summary": "模型返回仍然超长的候选。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩大幅超长章节",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["deterministic_trim_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert opening in patched.content
    assert protected_dialogue in patched.content
    assert ending in patched.content
    assert revision_count == 1
    assert version_count == 2
    assert len(calls) == 1


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


def _seed_confirmed_world_fact(
    db_session,
    *,
    project_id: str,
    claim_id: str,
    subject_ref: str,
    predicate: str,
    object_ref_or_value,
    chapter_index: int | None = None,
) -> WorldFactClaim:
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    claim = WorldFactClaim(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        claim_id=claim_id,
        chapter_index=chapter_index,
        subject_ref=subject_ref,
        predicate=predicate,
        object_ref_or_value=object_ref_or_value,
        claim_layer="truth",
        claim_status="confirmed",
        evidence_refs=[f"chapter:{chapter_index}"] if chapter_index is not None else [],
        authority_type=DERIVED,
        confidence=1.0,
        contract_version=profile.contract_version,
    )
    db_session.add(claim)
    db_session.commit()
    return claim


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
