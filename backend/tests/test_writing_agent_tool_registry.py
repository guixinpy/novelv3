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
    assert {"generate_chapter", "preflight_writing", "describe_agent_tools", "plan_writing_agent_run"}.issubset(set(names))
    assert allowed_tool_names() == set(names)
    assert target_type_for_tool("describe_agent_tools") == "agent_tool_plan"
    assert target_type_for_tool("plan_writing_agent_run") == "agent_tool_plan"
    assert "review_chapter_quality" in non_blocking_report_tool_names()

    for descriptor in descriptors:
        assert descriptor.category
        assert descriptor.module
        assert descriptor.description
        assert descriptor.input_schema["type"] == "object"
        assert descriptor.output_schema["type"] == "object"
        assert get_agent_tool_descriptor(descriptor.name) == descriptor


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
