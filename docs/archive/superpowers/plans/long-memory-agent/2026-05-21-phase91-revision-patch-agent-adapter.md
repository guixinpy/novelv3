# Phase91 Revision Patch Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `apply_planner_revision_patch` 从 `WritingAgentRunService` special-case 分支迁移为 Agent-native 静态工具 adapter，并为该写入工具提供可投影的结构化输出契约。

**Architecture:** 本阶段沿用 Phase90 的工具化模式：新增一个 focused writing-agent tool service 包装已有 core 逻辑，`tool_executor` 负责参数清洗、统一调度和 adapter metadata 暴露。`run_service` 继续收缩为通用执行管线，不再承载修订补丁领域分支。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, existing `writing_agent` tool registry/executor.

---

## Phase Context

- 阶段编号：Phase91
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段继续补齐长篇创作中的自动修订闭环。
- 系统能力改进：让 Agent 能统一调用“应用 planner 修订补丁”，并通过 contract snapshot 判断补丁结果、版本写入、复审建议和恢复路径。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/core/chapter_revision_apply.py`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行与 run_service 回归。
- 不做范围：不扩展 deterministic patch 支持动作；不迁移 `expand_chapter_to_target`、`compress_chapter_to_target`；不引入新的确认门禁策略。

## Reference Patterns

- `openhuman`：领域功能通过 domain/controller schema/registry 暴露，调度层不加领域分支。
- `hermes-agent`：工具通过 registry 发现并进入统一调用入口，主 Agent 循环不硬编码每个工具。
- `openclaw`：用 runtime tool fixture 思路锁定工具可见性、参数传递和结果形状。

对应到 novelv3：`apply_planner_revision_patch` 需要同时成为静态 adapter 和结构化工具契约，便于后续 Agent 自动执行“修订草稿 -> 应用补丁 -> 复审”的链路。

## File Structure

- Create: `backend/app/services/writing_agent/revision_patch_tool.py`
  - 负责调用 `app.core.chapter_revision_apply.apply_planner_revision_patch()`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_apply_planner_revision_patch()` handler。
  - 注册 `apply_planner_revision_patch` 静态 adapter。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_REVISION_PATCH_OUTPUT`。
  - 将 `apply_planner_revision_patch.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `apply_planner_revision_patch` special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 新增/更新 adapter names、metadata、migration tracking、contract snapshot、executor dispatch 测试。
- Verify: `backend/tests/test_writing_agent_runs.py`
  - 用既有 apply patch 测试确认 API 行为保持。

## Task 1: Lock Adapter And Contract With Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Add static adapter expectation**

```python
assert {
    ...
    "create_revision_draft",
    "apply_planner_revision_patch",
    ...
}.issubset(names)
```

- [ ] **Step 2: Mark migration tracking as handled**

```python
assert "apply_planner_revision_patch" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_apply_planner_revision_patch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("apply_planner_revision_patch")

    assert metadata == {
        "tool_name": "apply_planner_revision_patch",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "write",
        "handler_name": "_apply_planner_revision_patch",
    }
```

- [ ] **Step 4: Extend contract snapshot assertions**

```python
assert tools_by_name["apply_planner_revision_patch"]["adapter_type"] == "static"
assert tools_by_name["apply_planner_revision_patch"]["mutability"] == "guarded_write"
assert "missing_agent_native_adapter" not in tools_by_name["apply_planner_revision_patch"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["apply_planner_revision_patch"]["gap_codes"]
```

- [ ] **Step 5: Add executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_apply_planner_revision_patch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Revision Patch")
    db_session.add(project)
    db_session.commit()
    calls = []

    def fake_revision_patch_tool(db, project_id: str, *, chapter_index: int, revision_id: str | None):
        calls.append((project_id, chapter_index, revision_id))
        return {"status": "completed", "chapter_index": chapter_index, "revision_id": revision_id}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_tool.apply_planner_revision_patch_tool",
        fake_revision_patch_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="apply_planner_revision_patch",
            params={"chapter_index": "8", "revision_id": " rev-8 "},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 8, "revision_id": "rev-8"}
    assert calls == [(project.id, 8, "rev-8")]
```

- [ ] **Step 6: Run RED**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_planner_revision_patch or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: FAIL because adapter, metadata, structured output schema, and service wrapper do not exist yet.

## Task 2: Implement Adapter And Structured Output Schema

**Files:**
- Create: `backend/app/services/writing_agent/revision_patch_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`

- [ ] **Step 1: Add focused tool service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_revision_apply import apply_planner_revision_patch


def apply_planner_revision_patch_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    revision_id: str | None = None,
) -> dict[str, Any]:
    return apply_planner_revision_patch(db, project_id, chapter_index, revision_id=revision_id)
```

- [ ] **Step 2: Add executor handler**

```python
def _apply_planner_revision_patch(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.revision_patch_tool import apply_planner_revision_patch_tool

    revision_id = str(tool.params.get("revision_id") or "").strip() or None
    return apply_planner_revision_patch_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
        revision_id=revision_id,
    )
```

- [ ] **Step 3: Register static adapter**

```python
"apply_planner_revision_patch": WritingAgentToolAdapter(
    "apply_planner_revision_patch",
    _apply_planner_revision_patch,
    category="revision",
    mutability="write",
),
```

- [ ] **Step 4: Add structured output schema**

```python
_REVISION_PATCH_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "reason": {"type": "string"},
        "message": {"type": "string"},
        "chapter_index": {"type": "integer"},
        "chapter_id": {"type": "string"},
        "revision_id": {"type": ["string", "null"]},
        "revision_index": {"type": "integer"},
        "base_version_id": {"type": "string"},
        "result_version_id": {"type": "string"},
        "applied_replacement_count": {"type": "integer"},
        "applied_replacements": {"type": "array"},
        "word_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
        "unsupported_actions": {"type": "array"},
    }
)
```

Then use:

```python
output_schema=_REVISION_PATCH_OUTPUT,
```

- [ ] **Step 5: Run GREEN for executor slice**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_planner_revision_patch or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: PASS.

## Task 3: Remove Legacy Run Service Branch

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Delete only the `apply_planner_revision_patch` branch**

Remove:

```python
if tool.tool_name == "apply_planner_revision_patch":
    ...
```

Leave `expand_chapter_to_target` and `compress_chapter_to_target` untouched.

- [ ] **Step 2: Run existing run_service regression slice**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "apply_planner_revision_patch" -q
```

Expected: PASS.

## Task 4: Stage Report And Verification

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase91-revision-patch-agent-adapter.md`

- [ ] **Step 1: Write phase report**

Include actual changes, novel progress, findings, fixes, validation commands, and next recommendation.

- [ ] **Step 2: Run T1 verification**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "apply_planner_revision_patch or unhandled_internal_tools or inspect_agent_tool_contracts" -q
git diff --check
rg -l 'sk-[A-Za-z0-9]{20,}' backend docs --glob '!docs/archive/**'
```

Expected:

- pytest exits `0`
- `git diff --check` exits `0`
- secret scan prints no files; `rg` may exit `1` when no match is found.

- [ ] **Step 3: Commit and push**

```powershell
git add backend/app/services/writing_agent/revision_patch_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase91-revision-patch-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase91-revision-patch-agent-adapter.md
git commit -m "feat: adapt revision patch as agent tool"
git push origin main
```

## Self-Review

- Spec coverage: 本计划服务“模块工具化”“工具契约”“Agent 自主修订闭环”“分层验证”要求。
- Placeholder scan: 无 TBD/TODO/implement later。
- Type consistency: handler、adapter metadata、schema 和测试均使用 `apply_planner_revision_patch` / `_apply_planner_revision_patch` / `revision` / `write`。
