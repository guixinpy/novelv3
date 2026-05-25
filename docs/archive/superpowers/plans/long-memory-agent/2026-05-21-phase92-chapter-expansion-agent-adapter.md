# Phase92 Chapter Expansion Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `expand_chapter_to_target` 从 `WritingAgentRunService` special-case 分支迁移为 Agent-native 静态工具 adapter，并为扩写结果提供结构化输出契约。

**Architecture:** 本阶段继续收缩 `run_service` 的领域分支，把异步章节扩写封装到 focused writing-agent tool service。`tool_executor` 负责参数解析、异步调用和 adapter metadata 暴露，`tool_registry` 负责 Agent 可投影 schema。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, async writing-agent tool executor.

---

## Phase Context

- 阶段编号：Phase92
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段增强长篇创作中的修订扩写工具链。
- 系统能力改进：让 Agent 能统一调用“章节扩写到目标篇幅”，并通过 contract snapshot 判断扩写结果、版本写入、复审建议和世界模型阻断状态。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/core/chapter_expansion.py`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行与 run_service 回归。
- 不做范围：不改变扩写 prompt；不改变 AI 调用策略；不迁移 `compress_chapter_to_target`；不新增确认门禁。

## Reference Patterns

- `hermes-agent`：工具实现通过 registry 被发现并由统一工具调用入口执行，主 Agent loop 不硬编码每个工具。
- `openhuman`：参考 controller-only exposure，领域逻辑留在 domain/service，transport/dispatch 层只做泛化调度。
- `openclaw`：参考 runtime tool fixture，用测试锁定工具可见性、参数传递和结果形状。

对应到 novelv3：`expand_chapter_to_target` 需要从 `run_service` 分支迁到静态 adapter，并补结构化 schema，便于后续 Agent 自动执行“扩写 -> 复审 -> 继续生成/恢复”的链路。

## File Structure

- Create: `backend/app/services/writing_agent/chapter_expansion_tool.py`
  - 异步包装 `app.core.chapter_expansion.expand_chapter_to_target()`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 async `_expand_chapter_to_target()` handler。
  - 注册 `expand_chapter_to_target` 静态 adapter。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_CHAPTER_EXPANSION_OUTPUT`。
  - 将 `expand_chapter_to_target.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
  - 在 input schema 中显式暴露 `extra_instruction`。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `expand_chapter_to_target` special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 新增/更新 adapter names、metadata、migration tracking、contract snapshot、executor dispatch 测试。
- Verify: `backend/tests/test_writing_agent_runs.py`
  - 用既有 expand tests 确认 API 行为保持。

## Task 1: Lock Adapter And Contract With Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Add static adapter expectation**

```python
assert {
    ...
    "apply_planner_revision_patch",
    "expand_chapter_to_target",
    ...
}.issubset(names)
```

- [ ] **Step 2: Mark migration tracking as handled**

```python
assert "expand_chapter_to_target" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_expand_chapter_to_target_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("expand_chapter_to_target")

    assert metadata == {
        "tool_name": "expand_chapter_to_target",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "write",
        "handler_name": "_expand_chapter_to_target",
    }
```

- [ ] **Step 4: Extend contract snapshot assertions**

```python
assert tools_by_name["expand_chapter_to_target"]["adapter_type"] == "static"
assert tools_by_name["expand_chapter_to_target"]["mutability"] == "write"
assert "missing_agent_native_adapter" not in tools_by_name["expand_chapter_to_target"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["expand_chapter_to_target"]["gap_codes"]
```

- [ ] **Step 5: Add async executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_expand_chapter_to_target_adapter(db_session, monkeypatch):
    project = Project(name="Executor Chapter Expansion")
    db_session.add(project)
    db_session.commit()
    calls = []

    async def fake_expansion_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        min_word_count: int | None,
        extra_instruction: str,
    ):
        calls.append((project_id, chapter_index, min_word_count, extra_instruction))
        return {"status": "completed", "chapter_index": chapter_index, "word_count": 2200}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_expansion_tool.expand_chapter_to_target_tool",
        fake_expansion_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="expand_chapter_to_target",
            params={"chapter_index": "9", "min_word_count": "2100", "extra_instruction": "补足动作细节"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 9, "word_count": 2200}
    assert calls == [(project.id, 9, 2100, "补足动作细节")]
```

- [ ] **Step 6: Run RED**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "expand_chapter_to_target or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: FAIL because adapter, metadata, wrapper module, and structured schema do not exist yet.

## Task 2: Implement Adapter And Structured Output Schema

**Files:**
- Create: `backend/app/services/writing_agent/chapter_expansion_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`

- [ ] **Step 1: Add focused tool service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_expansion import expand_chapter_to_target


async def expand_chapter_to_target_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    min_word_count: int | None = None,
    extra_instruction: str = "",
) -> dict[str, Any]:
    return await expand_chapter_to_target(
        db,
        project_id,
        chapter_index,
        min_word_count=min_word_count,
        extra_instruction=extra_instruction,
    )
```

- [ ] **Step 2: Add async executor handler**

```python
async def _expand_chapter_to_target(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_expansion_tool import expand_chapter_to_target_tool

    return await expand_chapter_to_target_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
        min_word_count=_optional_int(tool.params.get("min_word_count")),
        extra_instruction=str(tool.params.get("extra_instruction") or ""),
    )
```

- [ ] **Step 3: Register static adapter**

```python
"expand_chapter_to_target": WritingAgentToolAdapter(
    "expand_chapter_to_target",
    _expand_chapter_to_target,
    category="revision",
    mutability="write",
),
```

- [ ] **Step 4: Add structured output schema**

```python
_CHAPTER_EXPANSION_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "reason": {"type": "string"},
        "message": {"type": "string"},
        "chapter_index": {"type": "integer"},
        "chapter_id": {"type": "string"},
        "revision_id": {"type": "string"},
        "revision_index": {"type": "integer"},
        "base_version_id": {"type": "string"},
        "result_version_id": {"type": "string"},
        "trace_id": {"type": "string"},
        "previous_word_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "target_min_word_count": {"type": "integer"},
        "target_max_word_count": {"type": ["integer", "null"]},
        "change_summary": {"type": "string"},
        "warnings": {"type": "array"},
        "pending_world_model_proposal_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)
```

Then use:

```python
input_schema=_object_schema(
    {
        "chapter_index": {"type": "integer", "minimum": 1},
        "min_word_count": {"type": "integer"},
        "extra_instruction": {"type": "string"},
    }
),
output_schema=_CHAPTER_EXPANSION_OUTPUT,
```

- [ ] **Step 5: Run GREEN for executor slice**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "expand_chapter_to_target or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: PASS.

## Task 3: Remove Legacy Run Service Branch

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Delete only the `expand_chapter_to_target` branch**

Remove:

```python
if tool.tool_name == "expand_chapter_to_target":
    ...
```

Leave `compress_chapter_to_target` untouched.

- [ ] **Step 2: Run existing run_service regression slice**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "expand_chapter_to_target" -q
```

Expected: PASS.

## Task 4: Stage Report And Verification

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase92-chapter-expansion-agent-adapter.md`

- [ ] **Step 1: Write phase report**

Include actual changes, novel progress, findings, fixes, validation commands, and next recommendation.

- [ ] **Step 2: Run T1 verification**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "expand_chapter_to_target or unhandled_internal_tools or inspect_agent_tool_contracts" -q
git diff --check
rg -l 'sk-[A-Za-z0-9]{20,}' backend docs --glob '!docs/archive/**'
```

Expected:

- pytest exits `0`
- `git diff --check` exits `0`
- secret scan prints no files; `rg` may exit `1` when no match is found.

- [ ] **Step 3: Commit and push**

```powershell
git add backend/app/services/writing_agent/chapter_expansion_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase92-chapter-expansion-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase92-chapter-expansion-agent-adapter.md
git commit -m "feat: adapt chapter expansion as agent tool"
git push origin main
```

## Self-Review

- Spec coverage: 本计划服务“模块工具化”“工具契约”“Agent 自主修订闭环”“分层验证”要求。
- Placeholder scan: 无 TBD/TODO/implement later。
- Type consistency: handler、adapter metadata、schema 和测试均使用 `expand_chapter_to_target` / `_expand_chapter_to_target` / `revision` / `write`。
