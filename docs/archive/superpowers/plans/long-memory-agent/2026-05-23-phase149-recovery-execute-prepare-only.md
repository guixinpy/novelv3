# Phase149 Recovery Execute Prepare-Only Safety Plan

> **For agentic workers:** Follow document-driven execution. This phase is a safety hardening phase after Phase148 binding recovery policy.

**Goal:** Prove that executing a resource-binding recovery plan runs only the fresh prepare tool and does not write chapter content.

**Architecture:** Keep recovery execution behind existing `confirm_execute + recovery_plan_hash` gates. Do not change write execution guards. Binding recovery execution may run prepare tools because prepare creates a new approval contract, but it must not directly run `execute_*` write tools or `generate_chapter`.

**Tech Stack:** Python, pytest, existing Writing Agent run service and recovery planner.

---

## Scope

In scope:
- Add an integration regression for `execute_recovery` on a binding-drift blocked longform batch run.
- Assert recovery preview returns exactly one `prepare_longform_chapter_batch_execution` tool.
- Assert recovery execution runs only the prepare tool.
- Assert no `generate_chapter` action is called and no `ChapterContent` is written.

Out of scope:
- Changing recovery planner execution policy.
- Adding frontend UI.
- Adding direct chapter recovery execution UI.

## Files

- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase149-recovery-execute-prepare-only.md`

## Task 1: Binding Recovery Execute Safety Regression

- [x] **Step 1: Add regression test**

Add `test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation`:
- seed a longform project with chapter 1 generated and chapter 2 ready.
- prepare a batch execution contract.
- force `execute_longform_chapter_batch` to block on `resource_binding_target_mismatch`.
- preview recovery tools and capture `plan_hash`.
- execute recovery with:
  - `auto_plan: True`
  - `recovery_run_id`
  - `execute_recovery: True`
  - `confirm_execute: True`
  - `recovery_plan_hash`
- assert:
  - recovery run input planner mode is `execute`
  - selected tools are only `prepare_longform_chapter_batch_execution`
  - prepare output is `approval_required`
  - `generate_chapter` is not called
  - chapter 2 content does not exist.

- [x] **Step 2: Run targeted test**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation -q
```

Expected: if existing behavior is already safe, the test passes without production changes. If it fails, make the smallest guardrail fix needed.

## Task 2: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q
```

- [x] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
```

Run:

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase149-recovery-execute-prepare-only.md`.

- [x] **Step 4: Commit and push**

Commit message:

```text
test: guard binding recovery prepare execution
```
