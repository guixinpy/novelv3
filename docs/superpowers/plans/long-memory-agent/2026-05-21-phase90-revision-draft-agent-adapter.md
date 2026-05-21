# Phase90 Revision Draft Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `create_revision_draft` 从 `WritingAgentRunService` 的 special-case 分支迁移为 Agent-native 静态工具 adapter。

**Architecture:** 本阶段继续“模块工具化”路线，把修订草稿生成封装为独立 writing-agent 工具服务，再由 `tool_executor` 统一调度。`run_service` 只负责通用执行管线，具体修订草稿逻辑不再留在 `_execute_tool()` 分支里。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, existing `writing_agent` tool registry/executor.

---

## Phase Context

- 阶段编号：Phase90
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段是创作链路工具化基础设施改造。
- 系统能力改进：让 Agent 可直接枚举、审计、执行修订草稿工具，为后续“审稿 -> 修订计划 -> 修订草稿 -> 应用补丁 -> 复审”工具链打基础。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/core/chapter_revision_*`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行与 run_service 回归。
- 不做范围：不迁移 `apply_planner_revision_patch`、`expand_chapter_to_target`、`compress_chapter_to_target`；不改变修订草稿业务规则；不跑全量前后端验证。

## Reference Patterns

本阶段从参考项目提取的直接工程原则：

- `openhuman` 的 controller-only exposure 规则：领域能力通过 registry/schema 暴露，避免在传输层或调度层新增领域分支。
- `hermes-agent` 的工具 registry 思路：工具应有可发现的名称、schema、工具集归属和统一执行入口。
- `openclaw` 的 runtime tool fixture 思路：工具可见性和执行面应可被测试锁定。

对应到 novelv3：修订草稿生成应从 `run_service._execute_tool()` 移到 `tool_executor` 静态 adapter，并通过 contract snapshot 暴露 adapter 元数据。

## File Structure

- Create: `backend/app/services/writing_agent/revision_draft_tool.py`
  - 负责组合 `plan_chapter_revision()` 与 `create_revision_draft_from_plan()`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_create_revision_draft()` handler。
  - 在 `_STATIC_TOOL_ADAPTERS` 注册 `create_revision_draft`。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `create_revision_draft` special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 先写失败测试，覆盖 adapter names、metadata、migration tracking、contract snapshot、executor dispatch。
- Verify: `backend/tests/test_writing_agent_runs.py`
  - 用既有 create_revision_draft run_service 测试确认行为保持。

## Task 1: Lock Adapter Contract With Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Update static adapter names expectation**

Add `create_revision_draft` to the expected static adapter subset:

```python
assert {
    ...
    "plan_chapter_revision",
    "create_revision_draft",
    ...
}.issubset(names)
```

- [ ] **Step 2: Update unhandled migration tracking expectation**

Change `create_revision_draft` from unhandled to handled:

```python
assert "create_revision_draft" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_create_revision_draft_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("create_revision_draft")

    assert metadata == {
        "tool_name": "create_revision_draft",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "write",
        "handler_name": "_create_revision_draft",
    }
```

- [ ] **Step 4: Add executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_create_revision_draft_adapter(db_session, monkeypatch):
    project = Project(name="Executor Revision Draft")
    db_session.add(project)
    db_session.commit()
    calls = []

    def fake_revision_draft_tool(db, project_id: str, *, chapter_index: int):
        calls.append((project_id, chapter_index))
        return {"status": "drafted", "chapter_index": chapter_index, "revision_id": "rev-1"}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_draft_tool.create_revision_draft_tool",
        fake_revision_draft_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="create_revision_draft", params={"chapter_index": "7"}),
    )

    assert result.handled is True
    assert result.output == {"status": "drafted", "chapter_index": 7, "revision_id": "rev-1"}
    assert calls == [(project.id, 7)]
```

- [ ] **Step 5: Update contract snapshot assertions**

In `test_tool_executor_handles_inspect_agent_tool_contracts`, assert:

```python
assert tools_by_name["create_revision_draft"]["adapter_type"] == "static"
assert tools_by_name["create_revision_draft"]["mutability"] == "write"
assert "missing_agent_native_adapter" not in tools_by_name["create_revision_draft"]["gap_codes"]
```

- [ ] **Step 6: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "create_revision_draft or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: FAIL because `create_revision_draft` has no static adapter or metadata yet.

## Task 2: Implement Minimal Adapter

**Files:**
- Create: `backend/app/services/writing_agent/revision_draft_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [ ] **Step 1: Add focused tool service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_revision_drafts import create_revision_draft_from_plan
from app.core.chapter_revision_planner import plan_chapter_revision


def create_revision_draft_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
) -> dict[str, Any]:
    plan = plan_chapter_revision(db, project_id, chapter_index)
    return create_revision_draft_from_plan(db, project_id, chapter_index, plan)
```

- [ ] **Step 2: Add executor handler**

```python
def _create_revision_draft(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.revision_draft_tool import create_revision_draft_tool

    return create_revision_draft_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
    )
```

- [ ] **Step 3: Register static adapter**

```python
"create_revision_draft": WritingAgentToolAdapter(
    "create_revision_draft",
    _create_revision_draft,
    category="revision",
    mutability="write",
),
```

- [ ] **Step 4: Run GREEN for executor slice**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "create_revision_draft or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: PASS.

## Task 3: Remove Legacy Run Service Branch

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Delete only the `create_revision_draft` branch**

Remove this branch:

```python
if tool.tool_name == "create_revision_draft":
    ...
```

Leave later revision branches untouched:

```python
if tool.tool_name == "apply_planner_revision_patch":
    ...
if tool.tool_name == "expand_chapter_to_target":
    ...
if tool.tool_name == "compress_chapter_to_target":
    ...
```

- [ ] **Step 2: Run existing run_service regression slice**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "create_revision_draft" -q
```

Expected: PASS.

## Task 4: Stage Report And Verification

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase90-revision-draft-agent-adapter.md`

- [ ] **Step 1: Write phase report**

The report must include:

- actual completed changes
- novel generation progress
- issues found/fixed
- validation level and commands
- next phase recommendation

- [ ] **Step 2: Run T1 verification**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "create_revision_draft or unhandled_internal_tools or inspect_agent_tool_contracts" -q
git diff --check
rg -l 'sk-[A-Za-z0-9]{20,}' backend docs --glob '!docs/archive/**'
```

Expected:

- pytest exits `0`
- `git diff --check` exits `0`
- secret scan prints no files; `rg` may exit `1` when no match is found.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/services/writing_agent/revision_draft_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase90-revision-draft-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase90-revision-draft-agent-adapter.md
git commit -m "feat: adapt revision draft as agent tool"
git push origin main
```

## Self-Review

- Spec coverage: 本计划直接服务“模块工具化”“工具契约”“统一执行入口”“分层验证”要求。
- Placeholder scan: 无 TBD/TODO/implement later。
- Type consistency: handler、adapter metadata、测试期望均使用 `create_revision_draft` / `_create_revision_draft` / `revision` / `write`。
