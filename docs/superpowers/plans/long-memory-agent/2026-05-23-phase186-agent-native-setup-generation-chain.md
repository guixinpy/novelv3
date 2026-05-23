# Phase186 Agent-Native Setup Generation Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `generate_setup` 增加 Agent-native preview / prepare / execute 受控执行链，保留旧 legacy fallback。

**Architecture:** 新增独立 `setup_generation_tool_descriptors.py` / `setup_generation_tool_adapters.py` / `setup_generation_execution.py`。preview 和 prepare 只读；execute 必须通过 `confirm_execute` + `approval_contract_hash` + `approval_contract` 门禁后，才调用现有 `app.api.setups.generate_setup` 底层生成逻辑。旧 `generate_setup` descriptor 和 action fallback 不移除。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/setup_generation_tool_descriptors.py`
  - Export `SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS`.
- Create: `backend/app/services/writing_agent/setup_generation_tool_adapters.py`
  - Export `build_setup_generation_agent_tool_adapters(...)`.
- Create: `backend/app/services/writing_agent/setup_generation_execution.py`
  - Export `preview_generate_setup_execution(...)`, `prepare_generate_setup_execution(...)`, `execute_generate_setup_with_approval(...)`.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread setup generation descriptors.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Merge setup generation adapters with approval metadata provider.
- Modify: `backend/app/services/writing_agent/mutation_fingerprint.py`
  - Recognize `generate_setup` / `execute_generate_setup_with_approval` as setup mutation targets.
- Modify: `backend/app/services/writing_agent/approval_tool_metadata.py`
  - Allow server-derived write plans to bind a legacy tool to an Agent approval wrapper.
- Modify: `backend/app/services/writing_agent/approval_contract.py`
  - Preserve `approval_executor_tool_name` in approval contracts.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary and registry assertions.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter boundary, metadata, preview/prepare/blocked execute/ready execute tests.

## Success Criteria

- New tools:
  - `preview_generate_setup_execution`: read, non-blocking, no writes.
  - `prepare_generate_setup_execution`: read, non-blocking, returns approval contract.
  - `execute_generate_setup_with_approval`: write, internal, requires confirmation/hash/contract.
- `execute_generate_setup_with_approval` blocks without confirmation or approval contract.
- Ready execution calls existing setup generation path and returns trace evidence.
- `generate_setup` legacy fallback remains unhandled by static executor.

## Non-Scope

- Do not remove or rename legacy `generate_setup`.
- Do not switch slash commands/dialog routes to the new chain yet.
- Do not migrate `generate_storyline` or `generate_outline` in this phase.

## Tasks

### Task 1: RED Registry Tests

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.setup_generation_tool_descriptors import SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_setup_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "preview_generate_setup_execution",
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
    ]
    assert {descriptor.category for descriptor in SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(descriptor.internal for descriptor in SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_generate_setup_execution") == "setup_generation_preview"
    assert target_type_for_tool("prepare_generate_setup_execution") == "setup_generation_approval"
    assert target_type_for_tool("execute_generate_setup_with_approval") == "setup"
    assert "prepare_generate_setup_execution" in non_blocking_report_tool_names()
    assert "execute_generate_setup_with_approval" not in non_blocking_report_tool_names()
```

- [x] Add registry contract test for `execute_generate_setup_with_approval` required fields.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "setup_generation" -q
```

### Task 2: RED Executor Tests

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.setup_generation_tool_adapters import build_setup_generation_agent_tool_adapters
```

- [x] Add adapter boundary test expecting three adapters.
- [x] Add metadata test for `execute_generate_setup_with_approval`.
- [x] Add preview/prepare dispatch tests.
- [x] Add execute blocked test without confirmation.
- [x] Add execute ready test monkeypatching `app.api.setups.generate_setup`.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "setup_generation or generate_setup_with_approval" -q
```

### Task 3: Implement Setup Generation Execution

- [x] Create `setup_generation_execution.py`.
- [x] Implement `_direct_generate_setup_agent_plan(project_id, command_args)`.
- [x] Use `build_agent_plan_approval_contract`, `verify_agent_plan_approval_contract`, `build_agent_step_binding`, `verify_resource_binding_target`.
- [x] Execute via existing `app.api.setups.generate_setup` only after approval verification.
- [x] Return blocked output with `side_effects.skipped == ["generate_setup"]` if gate fails.

### Task 4: Wire Descriptors and Adapters

- [x] Create descriptor module.
- [x] Create adapter module with approval metadata provider.
- [x] Import/spread descriptors in `tool_registry.py`.
- [x] Merge adapters in `tool_executor.py`.
- [x] Add `generate_setup` / `execute_generate_setup_with_approval` mutation fingerprint target `setup:project_id`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "setup_generation" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "setup_generation or generate_setup_with_approval" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase186-agent-native-setup-generation-chain.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/setup_generation_tool_descriptors.py backend/app/services/writing_agent/setup_generation_tool_adapters.py backend/app/services/writing_agent/setup_generation_execution.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/mutation_fingerprint.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase186-agent-native-setup-generation-chain.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase186-agent-native-setup-generation-chain.md
git commit -m "feat: add agent-native setup generation gate"
git push origin main
```
