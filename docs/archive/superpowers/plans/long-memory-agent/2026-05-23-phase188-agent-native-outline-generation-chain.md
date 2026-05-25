# Phase188 Agent-Native Outline Generation Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `generate_outline` 增加 Agent-native preview / prepare / execute 受控执行链，保留旧 legacy fallback。

**Architecture:** 复用 Phase186/187 的审批 wrapper 模式：计划步骤绑定到底层写入意图 `generate_outline`，并通过 `approval_executor_tool_name` 指向 `execute_generate_outline_with_approval`。preview 和 prepare 只读；execute 必须通过审批契约校验后，才调用现有 `app.api.outlines.generate_outline`。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/outline_generation_tool_descriptors.py`
- Create: `backend/app/services/writing_agent/outline_generation_tool_adapters.py`
- Create: `backend/app/services/writing_agent/outline_generation_execution.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/mutation_fingerprint.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

## Success Criteria

- New tools:
  - `preview_generate_outline_execution`: read, non-blocking, no writes.
  - `prepare_generate_outline_execution`: read, non-blocking, returns approval contract.
  - `execute_generate_outline_with_approval`: write, internal, requires confirmation/hash/contract.
- Ready execution calls existing outline generation path and returns trace evidence.
- `generate_outline` legacy fallback remains unhandled by static executor.
- Missing setup or storyline blocks before approval execution.

## Non-Scope

- Do not remove or rename legacy `generate_outline`.
- Do not switch slash commands/dialog routes to the new chain yet.
- Do not refactor setup/storyline/outline wrappers into a generic abstraction in this phase.

## Tasks

### Task 1: RED Registry Tests

- [x] Add import:

```python
from app.services.writing_agent.outline_generation_tool_descriptors import OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS
```

- [x] Add `test_outline_generation_tool_descriptors_live_in_dedicated_module` expecting:
  - tool names: `preview_generate_outline_execution`, `prepare_generate_outline_execution`, `execute_generate_outline_with_approval`
  - target types: `outline_generation_preview`, `outline_generation_approval`, `outline`
  - prepare is non-blocking report, execute is not.
- [x] Add `test_agent_tool_registry_includes_approved_outline_generation_tools` with required fields:
  - `confirm_execute`
  - `approval_contract_hash`
  - `approval_contract`
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "outline_generation" -q
```

### Task 2: RED Executor Tests

- [x] Add imports:

```python
from app.services.writing_agent.outline_generation_execution import prepare_generate_outline_execution
from app.services.writing_agent.outline_generation_tool_adapters import build_outline_generation_agent_tool_adapters
```

- [x] Add adapter boundary test expecting three adapters.
- [x] Add preview / prepare / blocked / ready execute tests using a project with generated `Setup` and `Storyline`.
- [x] Add metadata assertions for the three adapters.
- [x] Extend legacy unhandled/static adapter assertions for `generate_outline`.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "outline_generation or generate_outline_with_approval or preview_generate_outline or prepare_generate_outline" -q
```

### Task 3: Implement Outline Generation Chain

- [x] Create `outline_generation_execution.py`.
- [x] Implement readiness check:
  - project missing -> `Project not found`
  - setup missing -> `Setup not generated yet`
  - storyline missing -> `Storyline not generated yet`
- [x] Implement `_direct_generate_outline_agent_plan(project_id, command_args)`:
  - `tool_name`: `generate_outline`
  - `approval_executor_tool_name`: `execute_generate_outline_with_approval`
  - target: `outline:{project_id}`
- [x] Execute through `app.api.outlines.generate_outline` only after approval and binding verification.

### Task 4: Wire Descriptors and Adapters

- [x] Create descriptor module.
- [x] Create adapter module.
- [x] Import/spread descriptors in `tool_registry.py`.
- [x] Merge adapters in `tool_executor.py`.
- [x] Add mutation fingerprint targets for `generate_outline` and `execute_generate_outline_with_approval`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "outline_generation" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "outline_generation or generate_outline_with_approval or preview_generate_outline or prepare_generate_outline" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase188-agent-native-outline-generation-chain.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/outline_generation_tool_descriptors.py backend/app/services/writing_agent/outline_generation_tool_adapters.py backend/app/services/writing_agent/outline_generation_execution.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/mutation_fingerprint.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase188-agent-native-outline-generation-chain.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase188-agent-native-outline-generation-chain.md
git commit -m "feat: add agent-native outline generation gate"
git push origin main
```
