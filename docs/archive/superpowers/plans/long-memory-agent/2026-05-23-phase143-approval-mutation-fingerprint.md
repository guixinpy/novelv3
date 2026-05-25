# Phase143 Approval Mutation Fingerprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind Writing Agent approval contracts to stable mutation fingerprints for write steps.

**Architecture:** Extend approval contract construction so write steps can carry a deterministic `mutation_fingerprint` generated from project id, tool name, and write target. Direct chapter generation prepare output will expose the same fingerprint, while verification reports fingerprint readiness drift before execution.

**Tech Stack:** Python, pytest, existing Writing Agent approval contract, direct chapter generation approval path, Phase142 mutation fingerprint service.

---

## Scope

This phase moves Phase142 from a read-only inspection tool into the approval surface. It does not add a new database column, does not persist fingerprints on `WritingAgentStep`, and does not enforce a separate execution-time lock beyond the existing approval contract verification.

## Files

- Modify: `backend/app/services/writing_agent/approval_contract.py`
- Modify: `backend/app/services/writing_agent/chapter_generation_execution.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/tests/test_writing_agent_approval_contract.py`
- Modify: `backend/tests/test_writing_agent_chapter_generation_execution.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase143-approval-mutation-fingerprint.md`

## Task 1: Approval Contract Fingerprint Tests

- [ ] **Step 1: Add failing approval contract tests**

In `backend/tests/test_writing_agent_approval_contract.py`, add:

```python
def test_approval_contract_attaches_mutation_fingerprint_to_write_steps():
    plan = _write_plan(project_id="project-1")

    contract = build_agent_plan_approval_contract(plan)

    fingerprint = contract["write_steps"][0]["mutation_fingerprint"]
    assert fingerprint["status"] == "ready"
    assert fingerprint["components"]["target_id"] == "chapter:2"
    assert len(fingerprint["fingerprint"]) == 64
```

Add:

```python
def test_verify_approval_contract_blocks_when_mutation_fingerprint_not_ready():
    plan = _write_plan(project_id="project-1")
    plan["steps"][0]["params"] = {}
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "mutation_fingerprint_not_ready"
    assert result["drift"]["mutation_fingerprint_drift_count"] == 1
    assert result["recommended_next_tools"] == ["inspect_agent_mutation_fingerprints"]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py::test_approval_contract_attaches_mutation_fingerprint_to_write_steps backend\tests\test_writing_agent_approval_contract.py::test_verify_approval_contract_blocks_when_mutation_fingerprint_not_ready -q
```

Expected: fails because approval write steps do not include `mutation_fingerprint`.

- [ ] **Step 3: Implement approval contract fingerprint enrichment**

Modify `backend/app/services/writing_agent/approval_contract.py`:
- import `build_mutation_fingerprint`
- pass `project_id` into `_approval_step`
- attach `mutation_fingerprint` for mutating supported tools
- add `mutation_fingerprint_checked`, `mutation_fingerprint_drift_count`, and `mutation_fingerprints` to verification drift
- block with reason `mutation_fingerprint_not_ready` when fingerprint status is not ready and no earlier drift check has already blocked

- [ ] **Step 4: Run GREEN for approval contract tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py -q
```

Expected: approval contract tests pass.

## Task 2: Direct Chapter Prepare Surface

- [ ] **Step 1: Add failing prepare test expectations**

Update `backend/tests/test_writing_agent_chapter_generation_execution.py` so `test_prepare_generate_chapter_execution_returns_agent_approval_contract` asserts:

```python
step = output["agent_plan"]["steps"][0]
assert step["mutation_fingerprint"]["status"] == "ready"
assert step["mutation_fingerprint"]["components"]["target_id"] == "chapter:2"
assert output["mutation_fingerprint"] == step["mutation_fingerprint"]
assert output["agent_plan_approval_contract"]["write_steps"][0]["mutation_fingerprint"] == step["mutation_fingerprint"]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_prepare_generate_chapter_execution_returns_agent_approval_contract -q
```

Expected: fails because direct prepare output does not expose the fingerprint.

- [ ] **Step 3: Add direct generate plan fingerprint**

Modify `backend/app/services/writing_agent/chapter_generation_execution.py`:
- attach `build_mutation_fingerprint(project_id, "generate_chapter", {"chapter_index": chapter_index})` to the direct write step
- expose the same value as top-level `mutation_fingerprint`

- [ ] **Step 4: Run GREEN for chapter prepare**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py -q
```

Expected: chapter generation execution tests pass.

## Task 3: Registry Schema and Regression

- [ ] **Step 1: Add output schema assertion**

Update `backend/tests/test_writing_agent_tool_registry.py` so `test_agent_tool_registry_generate_chapter_has_structured_output_contract` or the prepare descriptor test asserts:

```python
assert prepare_descriptor.output_schema["properties"]["mutation_fingerprint"]["type"] == "object"
```

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_generate_chapter_has_structured_output_contract -q
```

Expected: fails until the descriptor schema is updated.

- [ ] **Step 3: Update schema**

Modify `backend/app/services/writing_agent/tool_registry.py` to include `mutation_fingerprint` in `prepare_generate_chapter_execution` output schema.

- [ ] **Step 4: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_mutation_fingerprint.py -q
```

Expected: all selected tests pass.

## Task 4: Hygiene, Report, Commit

- [ ] **Step 1: Run hygiene checks**

Run:

```powershell
git diff --check
```

Run:

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: no whitespace errors and no committed API key leaks.

- [ ] **Step 2: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase143-approval-mutation-fingerprint.md` with:
- objective
- implementation summary
- TDD evidence
- verification evidence
- novel progress
- known limits
- next recommendation

- [ ] **Step 3: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/approval_contract.py backend/app/services/writing_agent/chapter_generation_execution.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_chapter_generation_execution.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase143-approval-mutation-fingerprint.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase143-approval-mutation-fingerprint.md
git commit -m "feat: bind approvals to mutation fingerprints"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
