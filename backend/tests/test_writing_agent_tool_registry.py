from app.models import ChapterContent, Outline, Project, Setup, Storyline
from app.services.writing_agent.tool_registry import (
    allowed_tool_names,
    build_agent_tool_plan,
    get_agent_tool_descriptor,
    list_agent_tool_descriptors,
    non_blocking_report_tool_names,
    target_type_for_tool,
)


def test_agent_tool_registry_has_unique_names_and_contracts():
    descriptors = list_agent_tool_descriptors()
    names = [descriptor.name for descriptor in descriptors]

    assert len(names) == len(set(names))
    assert {
        "generate_chapter",
        "preflight_writing",
        "describe_agent_tools",
        "plan_writing_agent_run",
        "plan_recovery_tools",
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "inspect_longform_chapter_batch",
        "inspect_agent_job_projection",
        "inspect_agent_knowledge_base_route",
        "execute_longform_chapter_batch_preflight",
        "prepare_longform_chapter_batch_execution",
        "execute_longform_chapter_batch",
        "review_longform_chapter_batch_execution",
        "route_longform_chapter_batch_after_review",
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "inspect_agent_world_model_route",
        "summarize_longform_context",
        "repair_longform_maintenance",
    }.issubset(set(names))
    assert allowed_tool_names() == set(names)
    assert target_type_for_tool("describe_agent_tools") == "agent_tool_plan"
    assert target_type_for_tool("plan_writing_agent_run") == "agent_tool_plan"
    assert target_type_for_tool("plan_recovery_tools") == "agent_tool_plan"
    assert target_type_for_tool("plan_longform_chapter_batch") == "longform_batch_plan"
    assert target_type_for_tool("enqueue_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("inspect_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("inspect_agent_job_projection") == "agent_job_projection"
    assert target_type_for_tool("inspect_agent_knowledge_base_route") == "agent_knowledge_base_route"
    assert target_type_for_tool("execute_longform_chapter_batch_preflight") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_execution") == "background_task"
    assert target_type_for_tool("execute_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("review_longform_chapter_batch_execution") == "background_task"
    assert target_type_for_tool("route_longform_chapter_batch_after_review") == "background_task"
    assert target_type_for_tool("inspect_agent_trace_audit") == "agent_trace_audit"
    assert target_type_for_tool("inspect_agent_memory_route") == "agent_memory_route"
    assert target_type_for_tool("inspect_agent_world_model_route") == "agent_world_model_route"
    assert target_type_for_tool("summarize_longform_context") == "longform_context_summary"
    assert target_type_for_tool("repair_longform_maintenance") == "longform_maintenance"
    assert "review_chapter_quality" in non_blocking_report_tool_names()
    assert "plan_recovery_tools" in non_blocking_report_tool_names()
    assert "plan_longform_chapter_batch" in non_blocking_report_tool_names()
    assert "inspect_longform_chapter_batch" in non_blocking_report_tool_names()
    assert "inspect_agent_job_projection" in non_blocking_report_tool_names()
    assert "inspect_agent_knowledge_base_route" in non_blocking_report_tool_names()
    assert "summarize_longform_context" in non_blocking_report_tool_names()

    for descriptor in descriptors:
        assert descriptor.category
        assert descriptor.module
        assert descriptor.description
        assert descriptor.input_schema["type"] == "object"
        assert descriptor.output_schema["type"] == "object"
        assert get_agent_tool_descriptor(descriptor.name) == descriptor


def test_agent_tool_registry_includes_plan_recovery_tools():
    descriptor = get_agent_tool_descriptor("plan_recovery_tools")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_tool_plan"
    assert "plan_recovery_tools" in allowed_tool_names()
    assert "plan_recovery_tools" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_plan_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("plan_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "longform_batch_plan"
    assert descriptor.input_schema["properties"]["batch_size"]["minimum"] == 1
    assert "plan_longform_chapter_batch" in allowed_tool_names()
    assert "plan_longform_chapter_batch" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_enqueue_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("enqueue_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["batch_size"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["confirm_enqueue"]["type"] == "boolean"
    assert "enqueue_longform_chapter_batch" in allowed_tool_names()
    assert "enqueue_longform_chapter_batch" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("inspect_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert "inspect_longform_chapter_batch" in allowed_tool_names()
    assert "inspect_longform_chapter_batch" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_job_projection():
    descriptor = get_agent_tool_descriptor("inspect_agent_job_projection")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "agent_job_projection"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert "inspect_agent_job_projection" in allowed_tool_names()
    assert "inspect_agent_job_projection" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_knowledge_base_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_knowledge_base_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "knowledge_base"
    assert descriptor.target_type == "agent_knowledge_base_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert "inspect_agent_knowledge_base_route" in allowed_tool_names()
    assert "inspect_agent_knowledge_base_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_execute_longform_chapter_batch_preflight():
    descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch_preflight")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["max_chapters"]["minimum"] == 1
    assert "execute_longform_chapter_batch_preflight" in allowed_tool_names()
    assert "execute_longform_chapter_batch_preflight" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_prepare_longform_chapter_batch_execution():
    descriptor = get_agent_tool_descriptor("prepare_longform_chapter_batch_execution")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert "prepare_longform_chapter_batch_execution" in allowed_tool_names()
    assert "prepare_longform_chapter_batch_execution" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_execute_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert descriptor.input_schema["properties"]["attempt_manifest_hash"]["type"] == "string"
    assert descriptor.input_schema["properties"]["approval_contract_hash"]["type"] == "string"
    assert set(descriptor.input_schema["required"]) == {
        "task_id",
        "confirm_execute",
        "attempt_manifest_hash",
        "approval_contract_hash",
    }
    assert "execute_longform_chapter_batch" in allowed_tool_names()
    assert "execute_longform_chapter_batch" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_review_longform_chapter_batch_execution():
    descriptor = get_agent_tool_descriptor("review_longform_chapter_batch_execution")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["lookback"]["minimum"] == 1
    assert set(descriptor.input_schema["required"]) == {"task_id"}
    assert "review_longform_chapter_batch_execution" in allowed_tool_names()
    assert "review_longform_chapter_batch_execution" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_route_longform_chapter_batch_after_review():
    descriptor = get_agent_tool_descriptor("route_longform_chapter_batch_after_review")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["expected_post_generation_review_hash"]["type"] == "string"
    assert descriptor.input_schema["properties"]["next_batch_size"]["minimum"] == 1
    assert set(descriptor.input_schema["required"]) == {"task_id"}
    assert "route_longform_chapter_batch_after_review" in allowed_tool_names()
    assert "route_longform_chapter_batch_after_review" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_memory_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_memory_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["include_context_summary"]["type"] == "boolean"
    assert "inspect_agent_memory_route" in allowed_tool_names()
    assert "inspect_agent_memory_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_trace_audit():
    descriptor = get_agent_tool_descriptor("inspect_agent_trace_audit")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "trace"
    assert descriptor.target_type == "agent_trace_audit"
    assert descriptor.input_schema["properties"]["run_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert "inspect_agent_trace_audit" in allowed_tool_names()
    assert "inspect_agent_trace_audit" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_world_model_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_world_model_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "athena_world_model"
    assert descriptor.target_type == "agent_world_model_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["subject_ref"]["type"] == "string"
    assert "inspect_agent_world_model_route" in allowed_tool_names()
    assert "inspect_agent_world_model_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_summarize_longform_context():
    descriptor = get_agent_tool_descriptor("summarize_longform_context")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "longform_context_summary"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert "summarize_longform_context" in allowed_tool_names()
    assert "summarize_longform_context" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_repair_longform_maintenance():
    descriptor = get_agent_tool_descriptor("repair_longform_maintenance")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "maintenance"
    assert descriptor.target_type == "longform_maintenance"
    assert descriptor.input_schema["properties"]["repair_limit"]["minimum"] == 1
    assert "repair_longform_maintenance" in allowed_tool_names()


def test_agent_tool_plan_hides_chapter_generation_until_dependencies_are_ready(db_session):
    project = Project(name="Tool Plan Missing Dependencies")
    db_session.add(project)
    db_session.commit()

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)

    assert plan["status"] == "completed"
    assert _tool_names(plan["visible_tools"]) >= {"generate_setup", "preflight_writing"}
    assert "generate_chapter" in _tool_names(plan["hidden_tools"])
    chapter_diagnostics = _diagnostic_codes(plan, "generate_chapter")
    assert {"missing_setup", "missing_outline_chapter", "missing_previous_chapter"}.issubset(chapter_diagnostics)


def test_agent_tool_plan_shows_chapter_generation_when_required_inputs_are_ready(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)

    assert "generate_chapter" in _tool_names(plan["visible_tools"])
    assert "review_chapter_quality" in _tool_names(plan["hidden_tools"])
    assert "missing_generated_chapter" in _diagnostic_codes(plan, "review_chapter_quality")
    chapter_diagnostics = [item for item in plan["diagnostics"] if item["tool_name"] == "generate_chapter"]
    assert any(item["code"] == "missing_world_model_profile" and item["severity"] == "warning" for item in chapter_diagnostics)


def _seed_ready_project(db_session) -> Project:
    project = Project(name="Tool Plan Ready", genre="都市悬疑", target_chapter_count=600, target_word_count=1200000)
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
                    "chapter_index": 2,
                    "title": "雾港线索2",
                    "summary": "林深继续调查记忆异常。",
                    "scenes": ["诊所追问"],
                    "characters": ["林深"],
                    "purpose": "推进主线",
                }
            ],
            plotlines=[],
            foreshadowing=[],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="雾港线索1",
            content="林深在雾港旧灯塔发现记忆异常的第一条线索。",
            word_count=60,
            status="generated",
        )
    )
    db_session.commit()
    db_session.refresh(project)
    return project


def _tool_names(items: list[dict]) -> set[str]:
    return {str(item["name"]) for item in items}


def _diagnostic_codes(plan: dict, tool_name: str) -> set[str]:
    return {str(item["code"]) for item in plan["diagnostics"] if item["tool_name"] == tool_name}
