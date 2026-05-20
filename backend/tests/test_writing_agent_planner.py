from app.models import ChapterContent, Outline, Project, Setup, Storyline
from app.services.writing_agent.planner import build_writing_agent_run_plan


def test_planner_builds_ready_next_chapter_tool_chain(db_session):
    project = _seed_project(db_session, outline_chapters=[2], generated_chapters=[1])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="继续写下一章", chapter_index=2)

    assert plan["status"] == "completed"
    assert plan["intent_class"] == "continue_next_chapter"
    assert plan["chapter_index"] == 2
    assert _tool_names(plan) == [
        "describe_agent_tools",
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
    generate_request = next(tool for tool in plan["tools"] if tool["tool_name"] == "generate_chapter")
    assert generate_request["planner"] == {
        "step_index": 4,
        "reason": "依赖满足后生成第2章正文。",
        "on_missing": "stop",
        "on_failure": "stop",
        "expected_output": "章节正文。",
        "post_generation": False,
        "planner_version": "phase53.context_gate.v1",
    }
    quality_review = next(tool for tool in plan["tools"] if tool["tool_name"] == "review_chapter_quality")
    assert quality_review["planner"]["post_generation"] is True


def test_planner_adds_outline_expansion_when_target_outline_is_missing(db_session):
    project = _seed_project(db_session, outline_chapters=[1], generated_chapters=[1])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="继续写第2章", chapter_index=2)

    assert plan["status"] == "completed"
    assert _tool_names(plan) == [
        "describe_agent_tools",
        "expand_outline_window",
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
