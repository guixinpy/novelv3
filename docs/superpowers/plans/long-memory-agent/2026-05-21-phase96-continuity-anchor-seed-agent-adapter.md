# Phase96 Continuity Anchor Seed Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `seed_continuity_anchor_proposals` 从 `WritingAgentRunService` legacy 分支迁移为 Agent-native 静态工具 adapter，并为连续性锚点提案生成结果提供结构化输出契约。

**Architecture:** 本阶段继续把 Athena / 世界模型维护能力工具化：领域写入仍复用 `app.core.continuity_anchor_proposals.seed_continuity_anchor_proposals()`，新增 focused writing-agent adapter service 负责统一 tool entrypoint。`tool_executor` 负责 dispatch，`tool_registry` 负责 schema，`run_service` 不再硬编码该工具。

**Tech Stack:** FastAPI backend, SQLAlchemy Session, pytest, async writing-agent tool executor.

---

## Phase Context

- 阶段编号：Phase96
- 总目标依据：`docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- 本阶段小说内容：不生成新章节；本阶段增强 Agent 在审稿和世界模型维护阶段自动补齐关键连续性锚点提案的能力。
- 系统能力改进：Agent 可通过统一工具层生成稳定连续性锚点提案，后续再交由 `apply_world_model_proposal_resolution` 审批处理，减少长篇创作中父名、编号、日期等高显著事实漂移。
- 涉及模块：`backend/app/services/writing_agent/`, `backend/app/core/continuity_anchor_proposals.py`, `backend/tests/`
- 验证层级：T1，局部 backend 工具执行、registry 契约与 Agent run 回归。
- 不做范围：不改变锚点 seed 内容；不改变审批策略；不新增确认门禁；不迁移其他 `_STATUS_OUTPUT` 工具。

## Reference Patterns

- `hermes-agent`：维护类能力也应通过统一 tool-call 入口执行，不能在主 run service 中散落特殊分支。
- `openhuman`：长期记忆和事实维护动作应有 typed tool 输出，便于 Agent 在后续循环中判断是否继续、审批或恢复。
- `openclaw`：用契约测试锁定工具可见性、执行入口、结果形状和 migration gap，避免 Agent loop 依赖隐式实现细节。

对应到 novelv3：`seed_continuity_anchor_proposals` 是世界模型稳定性维护工具，迁入 Agent-native adapter 后，`WritingAgentRunService` 中当前已知 internal legacy special-case 可被清空。

## File Structure

- Create: `backend/app/services/writing_agent/continuity_anchor_seed_tool.py`
  - 包装 `seed_continuity_anchor_proposals(db, project_id)`。
  - 保留领域函数返回的 `recommended_actions`、`should_generate_next_chapter` 和统计字段。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_seed_continuity_anchor_proposals()` handler。
  - 注册 `seed_continuity_anchor_proposals` 静态 adapter。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_CONTINUITY_ANCHOR_SEED_OUTPUT`。
  - 将 `seed_continuity_anchor_proposals.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - 删除 `seed_continuity_anchor_proposals` legacy special-case 分支。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 新增/更新 adapter names、metadata、migration tracking、contract snapshot、executor dispatch 测试。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 新增连续性锚点 seed 工具输出 schema 断言。
- Verify: `backend/tests/test_writing_agent_runs.py`
  - 用既有 Agent run 测试确认提案生成行为保持。

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
    "seed_continuity_anchor_proposals",
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
assert "seed_continuity_anchor_proposals" not in names
```

- [ ] **Step 3: Add adapter metadata test**

```python
def test_tool_executor_exposes_seed_continuity_anchor_proposals_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("seed_continuity_anchor_proposals")

    assert metadata == {
        "tool_name": "seed_continuity_anchor_proposals",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "write",
        "handler_name": "_seed_continuity_anchor_proposals",
    }
```

- [ ] **Step 4: Extend contract snapshot assertions**

```python
assert tools_by_name["seed_continuity_anchor_proposals"]["adapter_type"] == "static"
assert tools_by_name["seed_continuity_anchor_proposals"]["mutability"] == "write"
assert "missing_agent_native_adapter" not in tools_by_name["seed_continuity_anchor_proposals"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["seed_continuity_anchor_proposals"]["gap_codes"]
```

- [ ] **Step 5: Add executor dispatch test**

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_seed_continuity_anchor_proposals_adapter(db_session, monkeypatch):
    project = Project(name="Executor Continuity Anchor Seed")
    db_session.add(project)
    db_session.commit()
    calls = []

    def fake_seed_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "blocked",
            "project_id": project_id,
            "profile_version": 1,
            "proposal_bundle_id": "bundle-1",
            "created_item_count": 2,
            "created_items": [
                {"proposal_item_id": "item-1", "claim_id": "claim-1", "subject_ref": "林深", "predicate": "father_name"}
            ],
            "pending_anchor_count": 2,
            "should_generate_next_chapter": False,
            "recommended_actions": ["apply_world_model_proposal_resolution"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.continuity_anchor_seed_tool.seed_continuity_anchor_proposals_tool",
        fake_seed_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="seed_continuity_anchor_proposals", params={}),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["created_item_count"] == 2
    assert calls == [project.id]
```

- [ ] **Step 6: Add registry output schema test**

```python
def test_agent_tool_registry_seed_continuity_anchor_proposals_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("seed_continuity_anchor_proposals")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {
        "status",
        "project_id",
        "profile_version",
        "proposal_bundle_id",
        "created_item_count",
        "created_items",
        "pending_anchor_count",
        "should_generate_next_chapter",
        "recommended_actions",
    }.issubset(properties)
    assert properties["created_items"]["type"] == "array"
    assert properties["recommended_actions"]["type"] == "array"
```

- [ ] **Step 7: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "seed_continuity_anchor_proposals or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

Expected: FAIL because `seed_continuity_anchor_proposals` has no static adapter and still uses generic output schema.

## Task 2: Implement Agent-Native Continuity Anchor Seed Adapter

**Files:**
- Create: `backend/app/services/writing_agent/continuity_anchor_seed_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [ ] **Step 1: Add focused wrapper service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.continuity_anchor_proposals import seed_continuity_anchor_proposals


def seed_continuity_anchor_proposals_tool(db: Session, project_id: str) -> dict[str, Any]:
    return seed_continuity_anchor_proposals(db, project_id)
```

- [ ] **Step 2: Add executor handler**

```python
def _seed_continuity_anchor_proposals(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.continuity_anchor_seed_tool import seed_continuity_anchor_proposals_tool

    return seed_continuity_anchor_proposals_tool(context.db, context.project_id)
```

- [ ] **Step 3: Register static adapter**

```python
"seed_continuity_anchor_proposals": WritingAgentToolAdapter(
    "seed_continuity_anchor_proposals",
    _seed_continuity_anchor_proposals,
    category="maintenance",
    mutability="write",
),
```

- [ ] **Step 4: Run focused executor tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "seed_continuity_anchor_proposals or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

Expected: executor adapter assertions pass except any schema-only failure still pending in registry tests.

## Task 3: Add Structured Registry Contract And Remove Legacy Branch

**Files:**
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: Add output schema**

```python
_CONTINUITY_ANCHOR_SEED_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "project_id": {"type": "string"},
        "profile_version": {"type": ["integer", "null"]},
        "proposal_bundle_id": {"type": ["string", "null"]},
        "created_item_count": {"type": "integer"},
        "created_items": {"type": "array"},
        "pending_anchor_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_actions": {"type": "array"},
    }
)
```

- [ ] **Step 2: Use schema in descriptor**

```python
output_schema=_CONTINUITY_ANCHOR_SEED_OUTPUT,
```

- [ ] **Step 3: Remove run_service legacy branch**

Remove:

```python
if tool.tool_name == "seed_continuity_anchor_proposals":
    from app.core.continuity_anchor_proposals import seed_continuity_anchor_proposals

    return seed_continuity_anchor_proposals(self.db, project_id)
```

- [ ] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "seed_continuity_anchor_proposals or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

Expected: PASS.

## Task 4: Regression, Review, Report, Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase96-continuity-anchor-seed-agent-adapter.md`

- [ ] **Step 1: Run Agent run regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "seed_continuity_anchor_proposals" -q
```

Expected: PASS, proving API-level Agent run still creates continuity anchor proposal items.

- [ ] **Step 2: Run diff and secret checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected: no whitespace errors and no leaked API keys in touched source/docs.

- [ ] **Step 3: Request subagent review**

Ask a reviewer to inspect the Phase96 diff for:

- adapter registration and metadata consistency;
- no remaining `run_service` legacy branch for `seed_continuity_anchor_proposals`;
- structured output schema coverage;
- test scope aligned with T1 verification;
- whether `run_service` still has any internal special-case branches after this migration.

- [ ] **Step 4: Write phase report**

Report must include:

- changed files;
- RED/GREEN command evidence;
- regression evidence;
- reviewer findings;
- remaining gaps from `inspect_agent_tool_contracts`.

- [ ] **Step 5: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/continuity_anchor_seed_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase96-continuity-anchor-seed-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase96-continuity-anchor-seed-agent-adapter.md
git diff --cached --check
git commit -m "feat: adapt continuity anchor seed as agent tool"
git push origin main
```

Expected: commit pushed to `origin/main`, worktree clean, long goal remains active.
