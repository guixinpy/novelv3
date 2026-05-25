# Phase94 Outline Window Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `expand_outline_window` 从 `WritingAgentRunService` special-case 分支迁移为 Agent-native 静态工具 adapter，并为大纲窗口扩展结果提供结构化输出契约。

**Architecture:** 本阶段继续减少 `run_service` 内部工具硬编码，把大纲窗口扩展封装为 focused writing-agent tool service。`tool_executor` 只负责参数解析和 adapter dispatch，`tool_registry` 负责 Agent 可见 schema，现有 `app.api.outlines.expand_outline_window()` 行为暂不重写。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, async writing-agent tool executor.

---

## Phase Context

- 阶段编号：Phase94
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段增强 Agent 自主补齐章节规划的基础能力。
- 系统能力改进：当用户只给脑洞或高层目标时，Agent 可通过统一工具层补齐缺失章节大纲窗口，再继续 preflight/generation，而不是依赖 `run_service` 硬编码分支。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/api/outlines.py`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行与 run_service/outline 回归。
- 不做范围：不重写 `app.api.outlines.expand_outline_window()` 内部生成逻辑；不改变 outline merge 算法；不迁移 `import_setup_world_model` 或 `seed_continuity_anchor_proposals`。

## Reference Patterns

- `hermes-agent`：工具通过 registry 暴露并由统一 tool-call 入口执行，主 Agent loop 不硬编码每个工具。
- `openhuman`：参考 controller-only exposure，交互层不复制业务规则；本阶段先将 Agent dispatch 与 API 行为隔离，后续可继续把 API 内业务逻辑下沉到领域 service。
- `openclaw`：参考 runtime tool fixture，用测试锁定工具可见性、参数传递和结果形状。

对应到 novelv3：`expand_outline_window` 是长篇自主推进的关键恢复工具，必须成为 Agent-native adapter，便于 planner 从“缺第 N 章大纲”直接转译为可执行工具调用。

## File Structure

- Create: `backend/app/services/writing_agent/outline_window_tool.py`
  - 异步包装 `app.api.outlines.expand_outline_window()`。
  - 汇总 Outline 对象上的 expansion result、trace id 和基础字段为 Agent 工具输出 dict。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 async `_expand_outline_window()` handler。
  - 注册 `expand_outline_window` 静态 adapter。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_OUTLINE_WINDOW_OUTPUT`。
  - 将 `expand_outline_window.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `expand_outline_window` special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 新增/更新 adapter names、metadata、migration tracking、contract snapshot、executor dispatch 测试。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 新增大纲窗口工具输入/输出 schema 断言。
- Verify: `backend/tests/test_writing_agent_runs.py`, `backend/tests/test_outlines.py`
  - 用既有 endpoint 和 Agent run 测试确认大纲窗口扩展行为保持。

## Task 1: Lock Adapter And Contract With Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`

- [ ] **Step 1: Add static adapter expectation**

```python
assert {
    ...
    "expand_outline_window",
    ...
}.issubset(names)
```

- [ ] **Step 2: Mark migration tracking as handled**

```python
assert "expand_outline_window" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_expand_outline_window_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("expand_outline_window")

    assert metadata == {
        "tool_name": "expand_outline_window",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "write",
        "handler_name": "_expand_outline_window",
    }
```

- [ ] **Step 4: Extend contract snapshot assertions**

```python
assert tools_by_name["expand_outline_window"]["adapter_type"] == "static"
assert tools_by_name["expand_outline_window"]["mutability"] == "write"
assert "missing_agent_native_adapter" not in tools_by_name["expand_outline_window"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["expand_outline_window"]["gap_codes"]
```

- [ ] **Step 5: Add async executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_expand_outline_window_adapter(db_session, monkeypatch):
    project = Project(name="Executor Outline Window")
    db_session.add(project)
    db_session.commit()
    calls = []

    async def fake_outline_window_tool(
        db,
        project_id: str,
        *,
        start_chapter: int,
        end_chapter: int,
        command_args: str | None,
    ):
        calls.append((project_id, start_chapter, end_chapter, command_args))
        return {
            "status": "completed",
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "outline_id": "outline-3",
            "total_chapters": 600,
            "added_chapter_count": 1,
            "merge": {"added_chapter_count": 1},
            "trace_id": "trace-3",
            "recommended_next_tools": ["preflight_writing"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.outline_window_tool.expand_outline_window_tool",
        fake_outline_window_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="expand_outline_window",
            command_args="补齐第3章",
            params={"chapter_index": "3"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["start_chapter"] == 3
    assert result.output["end_chapter"] == 3
    assert calls == [(project.id, 3, 3, "补齐第3章")]
```

- [ ] **Step 6: Add registry schema test**

```python
def test_agent_tool_registry_expand_outline_window_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("expand_outline_window")

    assert descriptor is not None
    input_properties = descriptor.input_schema["properties"]
    output_properties = descriptor.output_schema["properties"]
    assert {"chapter_index", "start_chapter", "end_chapter", "command_args"}.issubset(input_properties)
    assert {
        "status",
        "start_chapter",
        "end_chapter",
        "outline_id",
        "total_chapters",
        "added_chapter_count",
        "merge",
        "trace_id",
        "recommended_next_tools",
    }.issubset(output_properties)
```

- [ ] **Step 7: Run RED**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "expand_outline_window or expand_outline_window_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: FAIL because adapter, wrapper module, metadata, and structured schema do not exist yet.

## Task 2: Implement Adapter And Structured Output Schema

**Files:**
- Create: `backend/app/services/writing_agent/outline_window_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`

- [ ] **Step 1: Add focused tool service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


async def expand_outline_window_tool(
    db: Session,
    project_id: str,
    *,
    start_chapter: int,
    end_chapter: int,
    command_args: str | None = None,
) -> dict[str, Any]:
    from app.api import outlines as outline_api

    outline = await outline_api.expand_outline_window(
        project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        db=db,
        command_args=command_args,
    )
    merge = getattr(outline, "outline_expansion_result", {}) or {}
    return {
        "status": "completed",
        "start_chapter": start_chapter,
        "end_chapter": end_chapter,
        "outline_id": outline.id,
        "total_chapters": outline.total_chapters,
        "added_chapter_count": int(merge.get("added_chapter_count") or 0),
        "merge": merge,
        "trace_id": getattr(outline, "last_expansion_trace_id", None),
        "recommended_next_tools": ["preflight_writing"],
    }
```

- [ ] **Step 2: Add async executor handler**

```python
async def _expand_outline_window(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.outline_window_tool import expand_outline_window_tool

    start_chapter = int(tool.params.get("start_chapter") or tool.params.get("chapter_index") or 1)
    end_chapter = int(tool.params.get("end_chapter") or start_chapter)
    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    return await expand_outline_window_tool(
        context.db,
        context.project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        command_args=command_args,
    )
```

- [ ] **Step 3: Register static adapter**

```python
"expand_outline_window": WritingAgentToolAdapter(
    "expand_outline_window",
    _expand_outline_window,
    category="generation",
    mutability="write",
),
```

- [ ] **Step 4: Add structured output schema**

```python
_OUTLINE_WINDOW_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "start_chapter": {"type": "integer"},
        "end_chapter": {"type": "integer"},
        "outline_id": {"type": "string"},
        "total_chapters": {"type": "integer"},
        "added_chapter_count": {"type": "integer"},
        "merge": {"type": "object"},
        "trace_id": {"type": ["string", "null"]},
        "recommended_next_tools": {"type": "array"},
    }
)
```

- [ ] **Step 5: Update descriptor output**

```python
output_schema=_OUTLINE_WINDOW_OUTPUT,
```

## Task 3: Remove Legacy Branch And Preserve API Behavior

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Delete the `expand_outline_window` special-case branch**

Remove only the branch that imports `app.api.outlines.expand_outline_window` and converts its Outline object into output dict. Keep `import_setup_world_model` and `seed_continuity_anchor_proposals` unchanged.

- [ ] **Step 2: Run GREEN executor and registry tests**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "expand_outline_window or expand_outline_window_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

- [ ] **Step 3: Run focused run_service and outline regressions**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "expand_outline_window or recovery_execute" -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_outlines.py -k "expand_outline_window" -q
```

Expected: PASS; existing API tests should prove merge behavior and Agent constraint injection remain unchanged.

## Task 4: Review, Document, And Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase94-outline-window-agent-adapter.md`

- [ ] **Step 1: Run a read-only subagent review**

Ask the reviewer to inspect the Phase94 diff for missed untracked files, old branch residue, schema gaps, parameter drift, and behavior regression.

- [ ] **Step 2: Run final T1 checks**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py backend/tests/test_outlines.py -k "expand_outline_window or expand_outline_window_has_structured_output_contract or recovery_execute or unhandled_internal_tools or inspect_agent_tool_contracts" -q
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected: pytest PASS; `git diff --check` no output; secret scan exits with no matches.

- [ ] **Step 3: Write phase report**

Report actual changes, reference absorption, validation evidence, novel progress, residual risks, and next recommendation.

- [ ] **Step 4: Commit and push**

```powershell
git add backend/app/services/writing_agent/outline_window_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase94-outline-window-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase94-outline-window-agent-adapter.md
git commit -m "feat: adapt outline window expansion as agent tool"
git push origin main
```
