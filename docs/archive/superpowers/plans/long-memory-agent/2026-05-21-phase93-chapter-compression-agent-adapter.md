# Phase93 Chapter Compression Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `compress_chapter_to_target` 从 `WritingAgentRunService` special-case 分支迁移为 Agent-native 静态工具 adapter，并为压缩结果提供结构化输出契约。

**Architecture:** 本阶段继续收缩 `run_service` 的领域分支，把异步章节压缩封装到 focused writing-agent tool service。`tool_executor` 负责参数解析、异步调用和 adapter metadata 暴露，`tool_registry` 负责 Agent 可投影 schema。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, async writing-agent tool executor.

---

## Phase Context

- 阶段编号：Phase93
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段增强长篇创作中的修订压缩工具链。
- 系统能力改进：让 Agent 能统一调用“压缩明显失控章节”，并通过 contract snapshot 判断压缩结果、禁用词重试、版本写入、复审建议和世界模型阻断状态。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/core/chapter_compression.py`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行与 run_service 回归。
- 不做范围：不改变压缩 prompt；不改变 AI 调用策略；不改变确定性裁剪/修复算法；不迁移 `import_setup_world_model`、`expand_outline_window` 或 `seed_continuity_anchor_proposals`。

## Reference Patterns

- `hermes-agent`：工具实现通过 registry 被发现并由统一工具调用入口执行，主 Agent loop 不硬编码每个工具。
- `openhuman`：参考 controller-only exposure，领域逻辑留在 domain/service，transport/dispatch 层只做泛化调度。
- `openclaw`：参考 runtime tool fixture，用测试锁定工具可见性、参数传递和结果形状。

对应到 novelv3：`compress_chapter_to_target` 需要从 `run_service` 分支迁到静态 adapter，并补结构化 schema，便于后续 Agent 自动执行“压缩 -> 复审 -> 继续生成/恢复”的链路。

## File Structure

- Create: `backend/app/services/writing_agent/chapter_compression_tool.py`
  - 异步包装 `app.core.chapter_compression.compress_chapter_to_target()`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 async `_compress_chapter_to_target()` handler。
  - 注册 `compress_chapter_to_target` 静态 adapter。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_CHAPTER_COMPRESSION_OUTPUT`。
  - 将 `compress_chapter_to_target.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
  - 在 input schema 中显式暴露 `extra_instruction` 与 `forbidden_terms`。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `compress_chapter_to_target` special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 新增/更新 adapter names、metadata、migration tracking、contract snapshot、executor dispatch 测试。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 新增压缩工具输入/输出 schema 断言。
- Verify: `backend/tests/test_writing_agent_runs.py`
  - 用既有 compress tests 确认 API 行为保持。

## Task 1: Lock Adapter And Contract With Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`

- [ ] **Step 1: Add static adapter expectation**

```python
assert {
    ...
    "expand_chapter_to_target",
    "compress_chapter_to_target",
    ...
}.issubset(names)
```

- [ ] **Step 2: Mark migration tracking as handled**

```python
assert "compress_chapter_to_target" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_compress_chapter_to_target_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("compress_chapter_to_target")

    assert metadata == {
        "tool_name": "compress_chapter_to_target",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "write",
        "handler_name": "_compress_chapter_to_target",
    }
```

- [ ] **Step 4: Extend contract snapshot assertions**

```python
assert tools_by_name["compress_chapter_to_target"]["adapter_type"] == "static"
assert tools_by_name["compress_chapter_to_target"]["mutability"] == "write"
assert "missing_agent_native_adapter" not in tools_by_name["compress_chapter_to_target"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["compress_chapter_to_target"]["gap_codes"]
```

- [ ] **Step 5: Add async executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_compress_chapter_to_target_adapter(db_session, monkeypatch):
    project = Project(name="Executor Chapter Compression")
    db_session.add(project)
    db_session.commit()
    calls = []

    async def fake_compression_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        target_max_word_count: int | None,
        extra_instruction: str,
        forbidden_terms: list[str],
    ):
        calls.append((project_id, chapter_index, target_max_word_count, extra_instruction, forbidden_terms))
        return {"status": "completed", "chapter_index": chapter_index, "word_count": 2200}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_compression_tool.compress_chapter_to_target_tool",
        fake_compression_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="compress_chapter_to_target",
            params={
                "chapter_index": "10",
                "target_max_word_count": "2300",
                "extra_instruction": "保留悬念",
                "forbidden_terms": ["  啰嗦  ", "", "重复"],
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 10, "word_count": 2200}
    assert calls == [(project.id, 10, 2300, "保留悬念", ["啰嗦", "重复"])]
```

- [ ] **Step 6: Add registry schema test**

```python
def test_agent_tool_registry_compress_chapter_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("compress_chapter_to_target")

    assert descriptor is not None
    input_properties = descriptor.input_schema["properties"]
    output_properties = descriptor.output_schema["properties"]
    assert {"chapter_index", "target_max_word_count", "extra_instruction", "forbidden_terms"}.issubset(input_properties)
    assert {
        "status",
        "reason",
        "chapter_index",
        "chapter_id",
        "revision_id",
        "revision_index",
        "base_version_id",
        "result_version_id",
        "trace_id",
        "previous_word_count",
        "word_count",
        "target_min_word_count",
        "target_max_word_count",
        "forbidden_terms",
        "remaining_forbidden_terms",
        "postcondition_retry_count",
        "compression_attempt_count",
        "failed_attempts",
        "deterministic_repair_applied",
        "deterministic_trim_applied",
        "change_summary",
        "warnings",
        "pending_world_model_proposal_count",
        "should_generate_next_chapter",
        "recommended_next_tools",
    }.issubset(output_properties)
```

- [ ] **Step 7: Run RED**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "compress_chapter_to_target or compress_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

Expected: FAIL because adapter, metadata, wrapper module, and structured schema do not exist yet.

## Task 2: Implement Adapter And Structured Output Schema

**Files:**
- Create: `backend/app/services/writing_agent/chapter_compression_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`

- [ ] **Step 1: Add focused tool service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_compression import compress_chapter_to_target


async def compress_chapter_to_target_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    target_max_word_count: int | None = None,
    extra_instruction: str = "",
    forbidden_terms: list[str] | None = None,
) -> dict[str, Any]:
    return await compress_chapter_to_target(
        db,
        project_id,
        chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=extra_instruction,
        forbidden_terms=forbidden_terms or [],
    )
```

- [ ] **Step 2: Add async executor handler**

```python
async def _compress_chapter_to_target(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_compression_tool import compress_chapter_to_target_tool

    forbidden_terms = [str(item).strip() for item in (tool.params.get("forbidden_terms") or []) if str(item).strip()]
    return await compress_chapter_to_target_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
        target_max_word_count=_optional_int(tool.params.get("target_max_word_count")),
        extra_instruction=str(tool.params.get("extra_instruction") or ""),
        forbidden_terms=forbidden_terms,
    )
```

- [ ] **Step 3: Register static adapter**

```python
"compress_chapter_to_target": WritingAgentToolAdapter(
    "compress_chapter_to_target",
    _compress_chapter_to_target,
    category="revision",
    mutability="write",
),
```

- [ ] **Step 4: Add structured output schema**

```python
_CHAPTER_COMPRESSION_OUTPUT = _object_schema(
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
        "target_max_word_count": {"type": "integer"},
        "forbidden_terms": {"type": "array"},
        "remaining_forbidden_terms": {"type": "array"},
        "postcondition_retry_count": {"type": "integer"},
        "compression_attempt_count": {"type": "integer"},
        "failed_attempts": {"type": "array"},
        "deterministic_repair_applied": {"type": "boolean"},
        "deterministic_trim_applied": {"type": "boolean"},
        "change_summary": {"type": "string"},
        "warnings": {"type": "array"},
        "pending_world_model_proposal_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)
```

- [ ] **Step 5: Update descriptor input/output**

```python
input_schema=_object_schema(
    {
        "chapter_index": {"type": "integer", "minimum": 1},
        "target_max_word_count": {"type": "integer"},
        "extra_instruction": {"type": "string"},
        "forbidden_terms": {"type": "array"},
    }
),
output_schema=_CHAPTER_COMPRESSION_OUTPUT,
```

## Task 3: Remove Legacy Branch And Preserve API Behavior

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Delete the `compress_chapter_to_target` special-case branch**

Remove only the branch that imports `app.core.chapter_compression.compress_chapter_to_target` and calls it directly. Keep guard/report follow-up logic unchanged.

- [ ] **Step 2: Run GREEN executor and registry tests**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "compress_chapter_to_target or compress_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

- [ ] **Step 3: Run focused run_service regression**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "compress_chapter_to_target" -q
```

Expected: PASS; existing API tests should still prove version writes, forbidden-term retry, skip path, world-model block, and review gating.

## Task 4: Review, Document, And Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase93-chapter-compression-agent-adapter.md`

- [ ] **Step 1: Run a read-only subagent review**

Ask the reviewer to inspect the Phase93 diff for missed untracked files, old branch residue, schema gaps, parameter drift, and behavior regression.

- [ ] **Step 2: Run final T1 checks**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py -k "compress_chapter_to_target or compress_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected: pytest PASS; `git diff --check` no output; secret scan exits with no matches.

- [ ] **Step 3: Write phase report**

Report actual changes, reference absorption, validation evidence, novel progress, residual risks, and next recommendation.

- [ ] **Step 4: Commit and push**

```powershell
git add backend/app/services/writing_agent/chapter_compression_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase93-chapter-compression-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase93-chapter-compression-agent-adapter.md
git commit -m "feat: adapt chapter compression as agent tool"
git push origin main
```
