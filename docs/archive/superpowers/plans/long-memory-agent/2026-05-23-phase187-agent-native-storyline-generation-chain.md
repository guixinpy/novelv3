# Phase187 Agent-Native Storyline Generation Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `generate_storyline` 增加 Agent-native preview / prepare / execute 受控执行链，保留旧 legacy fallback。

**Architecture:** 复用 Phase186 的审批 wrapper 模式：计划步骤绑定到底层写入意图 `generate_storyline`，并通过 `approval_executor_tool_name` 指向 `execute_generate_storyline_with_approval`。preview 和 prepare 只读；execute 必须通过审批契约校验后，才调用现有 `app.api.storylines.generate_storyline`。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/storyline_generation_tool_descriptors.py`
  - Export `STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS`.
- Create: `backend/app/services/writing_agent/storyline_generation_tool_adapters.py`
  - Export `build_storyline_generation_agent_tool_adapters(...)`.
- Create: `backend/app/services/writing_agent/storyline_generation_execution.py`
  - Export `preview_generate_storyline_execution(...)`, `prepare_generate_storyline_execution(...)`, `execute_generate_storyline_with_approval(...)`.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread storyline generation descriptors after Hermes legacy descriptors.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Merge storyline generation adapters with approval metadata provider.
- Modify: `backend/app/services/writing_agent/mutation_fingerprint.py`
  - Recognize `generate_storyline` / `execute_generate_storyline_with_approval` as `storyline:{project_id}` mutation targets.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary and registry assertions.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter boundary, metadata, preview/prepare/blocked execute/ready execute tests.

## Success Criteria

- New tools:
  - `preview_generate_storyline_execution`: read, non-blocking, no writes.
  - `prepare_generate_storyline_execution`: read, non-blocking, returns approval contract.
  - `execute_generate_storyline_with_approval`: write, internal, requires confirmation/hash/contract.
- `execute_generate_storyline_with_approval` blocks without confirmation or approval contract.
- Ready execution calls existing storyline generation path and returns trace evidence.
- `generate_storyline` legacy fallback remains unhandled by static executor.

## Non-Scope

- Do not remove or rename legacy `generate_storyline`.
- Do not switch slash commands/dialog routes to the new chain yet.
- Do not migrate `generate_outline` in this phase.
- Do not refactor Phase186 setup-specific modules into a generic abstraction in this phase.

## Tasks

### Task 1: RED Registry Tests

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.storyline_generation_tool_descriptors import STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS
```

- [x] Add module boundary test:

```python
def test_storyline_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "preview_generate_storyline_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
    ]
    assert {descriptor.category for descriptor in STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(descriptor.internal for descriptor in STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_generate_storyline_execution") == "storyline_generation_preview"
    assert target_type_for_tool("prepare_generate_storyline_execution") == "storyline_generation_approval"
    assert target_type_for_tool("execute_generate_storyline_with_approval") == "storyline"
    assert "prepare_generate_storyline_execution" in non_blocking_report_tool_names()
    assert "execute_generate_storyline_with_approval" not in non_blocking_report_tool_names()
```

- [x] Add registry contract test for `execute_generate_storyline_with_approval`:

```python
def test_agent_tool_registry_includes_approved_storyline_generation_tools():
    execute_descriptor = get_agent_tool_descriptor("execute_generate_storyline_with_approval")

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "generation"
    assert execute_descriptor.target_type == "storyline"
    assert set(execute_descriptor.input_schema["required"]) == {
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"
```

- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "storyline_generation" -q
```

Expected: import failure for missing `storyline_generation_tool_descriptors`.

### Task 2: RED Executor Tests

- [x] Add imports in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.storyline_generation_execution import prepare_generate_storyline_execution
from app.services.writing_agent.storyline_generation_tool_adapters import build_storyline_generation_agent_tool_adapters
```

- [x] Add adapter boundary test:

```python
def test_storyline_generation_tool_adapters_live_in_dedicated_module():
    adapters = build_storyline_generation_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "preview_generate_storyline_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
    ]
    assert adapters["preview_generate_storyline_execution"].mutability == "read"
    assert adapters["prepare_generate_storyline_execution"].mutability == "read"
    assert adapters["execute_generate_storyline_with_approval"].mutability == "write"
    assert adapters["execute_generate_storyline_with_approval"].handler.__name__ == "_execute_generate_storyline_with_approval"
```

- [x] Add preview / prepare / blocked / ready execute tests:

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_preview_generate_storyline_execution(db_session):
    project = Project(name="Preview Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, world_building={}, characters=[], core_concept={}))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preview_generate_storyline_execution", command_args="双线叙事"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["target_type"] == "storyline"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_storyline"]}
    assert result.output["recommended_next_tools"] == ["prepare_generate_storyline_execution"]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_generate_storyline_execution(db_session):
    project = Project(name="Prepare Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, world_building={}, characters=[], core_concept={}))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="prepare_generate_storyline_execution", command_args="双线叙事"),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "generate_storyline"
    assert plan_step["approval_executor_tool_name"] == "execute_generate_storyline_with_approval"
    assert result.output["agent_plan_approval_contract_hash"]
    assert result.output["agent_plan_approval_contract"]["write_steps"][0]["tool_name"] == "generate_storyline"
    assert result.output["required_confirmation"]["confirm_execute"] is True
    assert result.output["recommended_next_tools"] == ["execute_generate_storyline_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_execute_generate_storyline_without_confirmation(db_session):
    project = Project(name="Blocked Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, world_building={}, characters=[], core_concept={}))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="execute_generate_storyline_with_approval"),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "confirmation_required"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_storyline"]}


@pytest.mark.asyncio
async def test_tool_executor_executes_generate_storyline_with_approval(db_session, monkeypatch):
    project = Project(name="Execute Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, world_building={}, characters=[], core_concept={}))
    db_session.commit()
    prepare = prepare_generate_storyline_execution(db_session, project.id, command_args="双线叙事")
    calls: list[dict] = []

    async def fake_generate_storyline(project_id: str, db, command_args=None):
        calls.append({"project_id": project_id, "command_args": command_args})

    monkeypatch.setattr("app.api.storylines.generate_storyline", fake_generate_storyline)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_generate_storyline_with_approval",
            command_args="双线叙事",
            params={
                "confirm_execute": True,
                "approval_contract_hash": prepare["agent_plan_approval_contract_hash"],
                "approval_contract": prepare["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["execute_version"]
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["expected"]["tool_name"] == "generate_storyline"
    assert result.output["side_effects"] == {"executed": ["generate_storyline"], "skipped": []}
    assert calls == [{"project_id": project.id, "command_args": "双线叙事"}]
```

- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "storyline_generation or generate_storyline_with_approval" -q
```

Expected: import failure for missing `storyline_generation_tool_adapters`.

### Task 3: Implement Storyline Generation Execution

- [x] Create `storyline_generation_execution.py`.
- [x] Implement `_direct_generate_storyline_agent_plan(project_id, command_args)`:
  - `tool_name`: `generate_storyline`
  - `approval_executor_tool_name`: `execute_generate_storyline_with_approval`
  - `target_type`: from mutation fingerprint `storyline:{project_id}`
- [x] `preview_generate_storyline_execution` must fail with `Setup not generated yet` if setup is missing.
- [x] `prepare_generate_storyline_execution` must return `agent_plan_approval_contract_hash`.
- [x] `execute_generate_storyline_with_approval` must call `app.api.storylines.generate_storyline` only after approval verification and resource binding verification.

### Task 4: Wire Descriptors and Adapters

- [x] Create descriptor module.
- [x] Create adapter module with approval metadata provider.
- [x] Import/spread descriptors in `tool_registry.py`.
- [x] Merge adapters in `tool_executor.py`.
- [x] Add mutation fingerprint targets for `generate_storyline` and `execute_generate_storyline_with_approval`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "storyline_generation" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "storyline_generation or generate_storyline_with_approval" -q
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
python -m compileall backend/app/services/writing_agent
```

### Task 6: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase187-agent-native-storyline-generation-chain.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/storyline_generation_tool_descriptors.py backend/app/services/writing_agent/storyline_generation_tool_adapters.py backend/app/services/writing_agent/storyline_generation_execution.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/mutation_fingerprint.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase187-agent-native-storyline-generation-chain.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase187-agent-native-storyline-generation-chain.md
git commit -m "feat: add agent-native storyline generation gate"
git push origin main
```
