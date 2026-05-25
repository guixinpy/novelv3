# Phase95 Setup World Model Import Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `import_setup_world_model` 从 `WritingAgentRunService` legacy 分支迁移为 Agent-native 静态工具 adapter，并为设定导入世界模型结果提供结构化输出契约。

**Architecture:** 本阶段继续把 Athena / 世界模型能力工具化：领域写入仍复用 `app.core.athena_longform.import_setup_to_world_model()`，新增 focused writing-agent adapter service 只负责 Agent 输出规范化和后续工具建议。`tool_executor` 负责 dispatch，`tool_registry` 负责 schema，`run_service` 不再硬编码该工具。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, async writing-agent tool executor.

---

## Phase Context

- 阶段编号：Phase95
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段增强 Agent 在项目初始化后自主建立世界模型事实层的能力。
- 系统能力改进：用户只给出脑洞、设定或世界观后，Agent 可通过统一工具层把 Setup 导入 Athena 世界模型，再继续 preflight、章节生成、世界模型分析或审稿。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/core/athena_longform.py`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行、registry 契约与 Agent run 回归。
- 不做范围：不改变 `import_setup_to_world_model()` 的领域导入逻辑；不重写 Setup 解析；不迁移 `seed_continuity_anchor_proposals`。

## Reference Patterns

- `hermes-agent`：工具通过统一入口和可配置能力暴露给 Agent；slash command 与 tool execution 不应绕过主编排层。
- `openhuman`：每个连接能力都应被暴露为 typed tool，结果进入长期记忆或工具上下文前需规范化。
- `openclaw`：用 runtime fixture / contract test 锁定工具可见性、参数形状和执行结果，避免 Agent loop 依赖隐式 special-case。

对应到 novelv3：`import_setup_world_model` 是世界模型初始化入口，必须成为 Agent-native adapter，才能让 Agent 从“缺世界模型 profile”恢复建议直接转译为可执行工具调用。

## File Structure

- Create: `backend/app/services/writing_agent/setup_world_model_import_tool.py`
  - 包装 `import_setup_to_world_model(db, project_id)`。
  - 标准化输出字段：`status`, `profile_version`, `project_profile_version_id`, `created`, `should_generate_next_chapter`, `recommended_next_tools`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_import_setup_world_model()` handler。
  - 注册 `import_setup_world_model` 静态 adapter。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_SETUP_WORLD_MODEL_IMPORT_OUTPUT`。
  - 将 `import_setup_world_model.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `import_setup_world_model` legacy special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 新增/更新 adapter names、metadata、migration tracking、contract snapshot、executor dispatch 测试。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 新增设定导入世界模型工具输出 schema 断言。
- Verify: `backend/tests/test_writing_agent_runs.py`
  - 用既有 Agent run 测试确认导入行为保持。

## Task 1: Lock Adapter And Contract With Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`

- [ ] **Step 1: Add static adapter expectation**

```python
assert {
    "describe_agent_tools",
    "generate_chapter",
    "plan_writing_agent_run",
    "plan_longform_chapter_batch",
    "enqueue_longform_chapter_batch",
    "inspect_longform_chapter_batch",
    "inspect_agent_job_projection",
    "inspect_agent_tool_contracts",
    "inspect_agent_knowledge_base_route",
    "record_agent_knowledge_base_candidate",
    "import_setup_world_model",
    "analyze_chapter_world_model",
    "expand_outline_window",
    "execute_longform_chapter_batch_preflight",
    "prepare_longform_chapter_batch_execution",
    "execute_longform_chapter_batch",
    "review_longform_chapter_batch_execution",
    "route_longform_chapter_batch_after_review",
    "inspect_agent_trace_audit",
    "inspect_agent_memory_route",
    "inspect_agent_world_model_route",
    "review_chapter_quality",
    "review_chapter_continuity",
    "plan_chapter_revision",
    "create_revision_draft",
    "apply_planner_revision_patch",
    "expand_chapter_to_target",
    "compress_chapter_to_target",
    "repair_longform_maintenance",
    "review_world_model_proposals",
    "plan_world_model_proposal_resolution",
    "preview_world_model_proposal_resolution",
    "apply_world_model_proposal_resolution",
    "draft_world_model_proposal_resolution_decisions",
}.issubset(names)
```

- [ ] **Step 2: Mark migration tracking as handled**

```python
assert "import_setup_world_model" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_import_setup_world_model_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("import_setup_world_model")

    assert metadata == {
        "tool_name": "import_setup_world_model",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "write",
        "handler_name": "_import_setup_world_model",
    }
```

- [ ] **Step 4: Extend contract snapshot assertions**

```python
assert tools_by_name["import_setup_world_model"]["adapter_type"] == "static"
assert tools_by_name["import_setup_world_model"]["mutability"] == "write"
assert "missing_agent_native_adapter" not in tools_by_name["import_setup_world_model"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["import_setup_world_model"]["gap_codes"]
```

- [ ] **Step 5: Add executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_import_setup_world_model_adapter(db_session, monkeypatch):
    project = Project(name="Executor Setup Import")
    db_session.add(project)
    db_session.commit()
    calls = []

    def fake_import_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "completed",
            "profile_version": 1,
            "project_profile_version_id": "profile-1",
            "created": {"profile": 1, "characters": 2, "locations": 1, "factions": 0, "artifacts": 0, "rules": 1},
            "should_generate_next_chapter": False,
            "recommended_next_tools": ["preflight_writing", "inspect_agent_world_model_route"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.setup_world_model_import_tool.import_setup_world_model_tool",
        fake_import_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="import_setup_world_model", params={}),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["profile_version"] == 1
    assert calls == [project.id]
```

- [ ] **Step 6: Add registry output schema test**

```python
def test_agent_tool_registry_import_setup_world_model_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("import_setup_world_model")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {
        "status",
        "profile_version",
        "project_profile_version_id",
        "created",
        "should_generate_next_chapter",
        "recommended_next_tools",
    }.issubset(properties)
    assert properties["created"]["type"] == "object"
    assert properties["recommended_next_tools"]["type"] == "array"
```

- [ ] **Step 7: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "import_setup_world_model or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

Expected: FAIL because `import_setup_world_model` has no static adapter and still uses generic output schema.

## Task 2: Implement Agent-Native Import Adapter

**Files:**
- Create: `backend/app/services/writing_agent/setup_world_model_import_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [ ] **Step 1: Add focused wrapper service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_longform import import_setup_to_world_model


def import_setup_world_model_tool(db: Session, project_id: str) -> dict[str, Any]:
    result = import_setup_to_world_model(db=db, project_id=project_id)
    return {
        **result,
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["preflight_writing", "inspect_agent_world_model_route"],
    }
```

- [ ] **Step 2: Add executor handler**

```python
def _import_setup_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.setup_world_model_import_tool import import_setup_world_model_tool

    return import_setup_world_model_tool(context.db, context.project_id)
```

- [ ] **Step 3: Register static adapter**

```python
"import_setup_world_model": WritingAgentToolAdapter(
    "import_setup_world_model",
    _import_setup_world_model,
    category="athena_world_model",
    mutability="write",
),
```

- [ ] **Step 4: Run focused executor tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "import_setup_world_model or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

Expected: executor adapter assertions pass except any schema-only failure still pending in registry tests.

## Task 3: Add Structured Registry Contract And Remove Legacy Branch

**Files:**
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Add output schema**

```python
_SETUP_WORLD_MODEL_IMPORT_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "profile_version": {"type": "integer"},
        "project_profile_version_id": {"type": "string"},
        "created": {"type": "object"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)
```

- [ ] **Step 2: Use schema in descriptor**

```python
output_schema=_SETUP_WORLD_MODEL_IMPORT_OUTPUT,
```

- [ ] **Step 3: Remove run_service legacy branch**

Remove:

```python
if tool.tool_name == "import_setup_world_model":
    from app.core.athena_longform import import_setup_to_world_model

    return import_setup_to_world_model(db=self.db, project_id=project_id)
```

- [ ] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "import_setup_world_model or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

Expected: PASS.

## Task 4: Regression, Review, Report, Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase95-setup-world-model-import-agent-adapter.md`

- [ ] **Step 1: Run Agent run regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "import_setup_world_model" -q
```

Expected: PASS, proving API-level Agent run still creates world model profile.

- [ ] **Step 2: Run diff and secret checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected: no whitespace errors and no leaked API keys in touched source/docs.

- [ ] **Step 3: Request subagent review**

Ask a reviewer to inspect the Phase95 diff for:

- adapter registration and metadata consistency;
- no remaining `run_service` legacy branch for `import_setup_world_model`;
- structured output schema coverage;
- test scope aligned with T1 verification.

- [ ] **Step 4: Write phase report**

Report must include:

- changed files;
- RED/GREEN command evidence;
- regression evidence;
- reviewer findings;
- remaining gaps, especially `seed_continuity_anchor_proposals` if still legacy.

- [ ] **Step 5: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/setup_world_model_import_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase95-setup-world-model-import-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase95-setup-world-model-import-agent-adapter.md
git diff --cached --check
git commit -m "feat: adapt setup world model import as agent tool"
git push origin main
```

Expected: commit pushed to `origin/main`, worktree clean, long goal remains active.
