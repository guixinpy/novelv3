"""v2 动作执行测试（stub 清理后：仅 generate_chapter 真生成路径 + 缺项目优雅失败）。"""
from __future__ import annotations

import pytest

from app.models import Project
from app.services.actions.action_execution_service import ActionExecutionService


@pytest.mark.asyncio
async def test_missing_project_fails_gracefully(db_session):
    result = await ActionExecutionService(db_session).execute("generate_chapter", "no-such-project")
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_unknown_action_returns_success_default(db_session):
    """已删动作（generate_setup 等）走默认分支：无副作用成功（既有行为）。"""
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    result = await ActionExecutionService(db_session).execute("generate_setup", project.id)
    assert result["status"] == "success"
