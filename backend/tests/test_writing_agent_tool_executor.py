import pytest

from app.models import Project
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_executor import WritingAgentToolContext, execute_writing_agent_tool


@pytest.mark.asyncio
async def test_tool_executor_handles_describe_agent_tools(db_session):
    project = Project(name="Executor Tool Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-1"),
        WritingAgentToolRequest(tool_name="describe_agent_tools", params={"chapter_index": 1}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert "visible_tools" in result.output
    assert "hidden_tools" in result.output


@pytest.mark.asyncio
async def test_tool_executor_handles_planner_tool(db_session):
    project = Project(name="Executor Planner")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="plan_writing_agent_run",
            params={"goal": "创建一个都市悬疑项目", "chapter_index": 1, "intent": "setup_project"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_class"] == "setup_project"
    assert result.output["steps"][0]["tool_name"] == "describe_agent_tools"


@pytest.mark.asyncio
async def test_tool_executor_handles_preflight_with_injected_callback(db_session):
    project = Project(name="Executor Preflight")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, dict]] = []

    def fake_preflight(project_id: str, params: dict):
        calls.append((project_id, params))
        return {"status": "ready", "chapter_index": params["chapter_index"]}

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preflight_writing", params={"chapter_index": 3}),
        preflight_writing=fake_preflight,
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "chapter_index": 3}
    assert calls == [(project.id, {"chapter_index": 3})]


@pytest.mark.asyncio
async def test_tool_executor_leaves_legacy_generation_tools_unhandled(db_session):
    project = Project(name="Executor Legacy")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="generate_setup", command_args="城市悬疑"),
    )

    assert result.handled is False
    assert result.output is None
