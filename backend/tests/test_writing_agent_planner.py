from app.models import ChapterContent, Outline, Project, Setup, Storyline, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.planner import build_writing_agent_run_plan


def test_planner_builds_ready_next_chapter_tool_chain(db_session):
    project = _seed_project(db_session, outline_chapters=[2], generated_chapters=[1])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="继续写下一章", chapter_index=2)

    assert plan["status"] == "completed"
    assert plan["intent_class"] == "continue_next_chapter"
    assert plan["chapter_index"] == 2
    assert plan["trace"]["chapter_generation_route"] == "legacy_generate_chapter"
    assert _tool_names(plan) == [
        "describe_agent_tools",
        "inspect_agent_knowledge_base_route",
        "summarize_longform_context",
        "preflight_writing",
        "generate_chapter",
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
    ]
    assert [step["tool_name"] for step in plan["steps"] if step.get("post_generation")] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
    ]
    assert plan["trace"]["selected_tools"] == _tool_names(plan)
    assert plan["trace"]["plan_id"].startswith("plan:")
    first_step = plan["steps"][0]
    generate_step = next(step for step in plan["steps"] if step["tool_name"] == "generate_chapter")
    assert first_step["step_id"].startswith("step:")
    assert first_step["plan_id"] == plan["trace"]["plan_id"]
    assert first_step["source_projection_id"] is None
    assert first_step["mutability"] == "read"
    assert first_step["requires_confirmation"] is False
    assert generate_step["mutability"] == "write"
    assert generate_step["requires_confirmation"] is True
    generate_request = next(tool for tool in plan["tools"] if tool["tool_name"] == "generate_chapter")
    assert generate_request["planner"] == {
        "step_index": 5,
        "step_id": generate_step["step_id"],
        "plan_id": plan["trace"]["plan_id"],
        "source_projection_id": None,
        "mutability": "write",
        "requires_confirmation": True,
        "reason": "依赖满足后生成第2章正文。",
        "on_missing": "stop",
        "on_failure": "stop",
        "expected_output": "章节正文。",
        "post_generation": False,
        "planner_version": "phase53.context_gate.v1",
    }
    quality_review = next(tool for tool in plan["tools"] if tool["tool_name"] == "review_chapter_quality")
    assert quality_review["planner"]["post_generation"] is True
    assert plan["approval_contract"]["status"] == "requires_confirmation"
    assert plan["approval_contract"]["plan_id"] == plan["trace"]["plan_id"]
    assert [step["tool_name"] for step in plan["approval_contract"]["write_steps"]] == [
        "generate_chapter",
        "analyze_chapter_world_model",
    ]
    assert plan["approval_contract"]["approval"]["approval_contract_hash"].startswith("approval:")


def test_planner_can_prepare_next_chapter_through_approved_route(db_session):
    project = _seed_project(db_session, outline_chapters=[2], generated_chapters=[1])

    plan = build_writing_agent_run_plan(
        db_session,
        project.id,
        goal="继续写下一章",
        chapter_index=2,
        chapter_generation_route="approved_prepare",
    )

    assert plan["status"] == "completed"
    assert plan["intent_class"] == "continue_next_chapter"
    assert plan["trace"]["chapter_generation_route"] == "approved_prepare"
    assert _tool_names(plan) == [
        "describe_agent_tools",
        "inspect_agent_knowledge_base_route",
        "summarize_longform_context",
        "preflight_writing",
        "prepare_generate_chapter_execution",
    ]
    assert "generate_chapter" not in _tool_names(plan)
    assert [step["tool_name"] for step in plan["steps"] if step.get("post_generation")] == []
    prepare_step = next(step for step in plan["steps"] if step["tool_name"] == "prepare_generate_chapter_execution")
    assert prepare_step["mutability"] == "read"
    assert prepare_step["requires_confirmation"] is False
    assert prepare_step["params"] == {"chapter_index": 2}
    assert plan["approval_contract"]["status"] == "not_required"
    assert plan["approval_contract"]["write_steps"] == []


def test_planner_routes_recovery_intent_to_latest_recoverable_run(db_session):
    project = _seed_project(db_session, outline_chapters=[2], generated_chapters=[1])
    blocked_run = WritingAgentRun(
        project_id=project.id,
        goal="阻塞的直接章节执行",
        status="blocked",
        entrypoint="api",
        input={},
    )
    db_session.add(blocked_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=blocked_run.id,
            project_id=project.id,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="blocked",
            input={"params": {"chapter_index": 2}},
            output={
                "status": "blocked",
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "source_tool": "execute_generate_chapter_with_approval",
                        "reason_code": "resource_binding_target_mismatch",
                        "next_tool": "prepare_generate_chapter_execution",
                        "next_params": {"chapter_index": 2},
                    }
                },
            },
        )
    )
    db_session.commit()

    plan = build_writing_agent_run_plan(db_session, project.id, goal="恢复上一轮阻塞")

    assert plan["status"] == "completed"
    assert plan["intent_class"] == "recover_blocked_run"
    assert _tool_names(plan) == ["describe_agent_tools", "plan_recovery_tools"]
    recovery_step = plan["steps"][1]
    assert recovery_step["params"] == {"run_id": blocked_run.id}
    assert recovery_step["mutability"] == "read"
    assert recovery_step["requires_confirmation"] is False
    assert plan["approval_contract"]["status"] == "not_required"
    assert plan["approval_contract"]["write_steps"] == []


def test_planner_marks_review_only_plan_as_not_requiring_approval(db_session):
    project = _seed_project(db_session, outline_chapters=[2], generated_chapters=[2])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="审稿第2章", chapter_index=2)

    assert plan["status"] == "completed"
    assert plan["intent_class"] == "review_chapter"
    assert _tool_names(plan) == [
        "describe_agent_tools",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
    ]
    assert plan["approval_contract"]["status"] == "not_required"
    assert plan["approval_contract"]["write_steps"] == []


def test_planner_adds_outline_expansion_when_target_outline_is_missing(db_session):
    project = _seed_project(db_session, outline_chapters=[1], generated_chapters=[1])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="继续写第2章", chapter_index=2)

    assert plan["status"] == "completed"
    assert _tool_names(plan) == [
        "describe_agent_tools",
        "expand_outline_window",
        "inspect_agent_knowledge_base_route",
        "summarize_longform_context",
        "preflight_writing",
        "generate_chapter",
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
    ]
    expansion = plan["steps"][1]
    assert expansion["params"] == {"start_chapter": 2, "end_chapter": 2}
    assert expansion["on_missing"] == "fallback_tool"


def test_planner_blocks_when_previous_chapter_is_missing(db_session):
    project = _seed_project(db_session, outline_chapters=[3], generated_chapters=[])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="继续写第3章", chapter_index=3)

    assert plan["status"] == "blocked"
    assert "generate_chapter" not in _tool_names(plan)
    assert any(item["code"] == "missing_previous_chapter" for item in plan["trace"]["missing_dependencies"])
    assert "missing_previous_chapter" in plan["trace"]["risk_flags"]


def test_planner_builds_setup_project_plan_for_bare_project(db_session):
    project = Project(name="Bare Planner Project")
    db_session.add(project)
    db_session.commit()

    plan = build_writing_agent_run_plan(db_session, project.id, goal="创建一个都市悬疑设定")

    assert plan["status"] == "completed"
    assert plan["intent_class"] == "setup_project"
    assert _tool_names(plan) == ["describe_agent_tools", "generate_setup"]


def _seed_project(db_session, *, outline_chapters: list[int], generated_chapters: list[int]) -> Project:
    project = Project(name="Planner Novel", genre="都市悬疑", target_chapter_count=600, target_word_count=1200000)
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港被记忆异常影响。"},
            characters=[{"name": "林深", "goals": "查明真相"}],
            core_concept={"hook": "雾会回放记忆"},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查记忆异常", "milestones": []}],
            foreshadowing=[],
        )
    )
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=600,
            status="generated",
            chapters=[
                {
                    "chapter_index": index,
                    "title": f"雾港线索{index}",
                    "summary": f"林深继续调查第{index}条线索。",
                    "scenes": ["诊所追问"],
                    "characters": ["林深"],
                    "purpose": "推进主线",
                }
                for index in outline_chapters
            ],
            plotlines=[],
            foreshadowing=[],
        )
    )
    for index in generated_chapters:
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"雾港线索{index}",
                content=f"林深在第{index}章发现雾港记忆异常的新证据。",
                word_count=2200,
                status="generated",
            )
        )
    db_session.commit()
    db_session.refresh(project)
    return project


def _tool_names(plan: dict) -> list[str]:
    return [step["tool_name"] for step in plan["steps"]]
