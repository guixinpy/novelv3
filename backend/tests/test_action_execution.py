"""v2 动作执行测试（v1 绞杀：generate 动作统一走 athena 路径后不再 ImportError）。"""
from __future__ import annotations

import pytest

from app.models import Project, WritingAgentRun
from app.services.actions.action_execution_service import ActionExecutionService


@pytest.mark.asyncio
async def test_generate_setup_action_records_run(db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    result = await ActionExecutionService(db_session).execute("generate_setup", project.id)
    assert result["status"] == "success"

    run = (
        db_session.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project.id)
        .order_by(WritingAgentRun.created_at.desc())
        .first()
    )
    assert run is not None
    assert (run.output or {}).get("control_plane", {}).get("action_type") == "generate_setup"


@pytest.mark.asyncio
async def test_generate_storyline_action_records_run(db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    result = await ActionExecutionService(db_session).execute("generate_storyline", project.id)
    assert result["status"] == "success"

    run = (
        db_session.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project.id)
        .order_by(WritingAgentRun.created_at.desc())
        .first()
    )
    assert run is not None
    assert (run.output or {}).get("control_plane", {}).get("action_type") == "generate_storyline"


@pytest.mark.asyncio
async def test_generate_outline_action_records_run(db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    result = await ActionExecutionService(db_session).execute("generate_outline", project.id)
    assert result["status"] == "success"

    run = (
        db_session.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project.id)
        .order_by(WritingAgentRun.created_at.desc())
        .first()
    )
    assert run is not None
    assert (run.output or {}).get("control_plane", {}).get("action_type") == "generate_outline"


@pytest.mark.asyncio
async def test_missing_project_fails_gracefully(db_session):
    result = await ActionExecutionService(db_session).execute("generate_setup", "no-such-project")
    assert result["status"] == "failed"
