# Phase150 Direct Recovery Prepare-Only Safety Plan

> **For agentic workers:** Follow document-driven execution. This phase extends Phase149's recovery execution safety coverage to direct chapter generation.

**Goal:** Prove that executing a direct single-chapter resource-binding recovery plan runs only `prepare_generate_chapter_execution` and does not generate chapter content.

**Architecture:** Direct chapter writes already require `prepare_generate_chapter_execution` followed by explicit `execute_generate_chapter_with_approval`. Recovery execution may refresh the prepare contract, but must not call `execute_generate_chapter_with_approval` or `generate_chapter` without a fresh explicit approval.

**Tech Stack:** Python, pytest, existing Writing Agent run service and recovery planner.

---

## Scope

In scope:
- Add an integration regression for a blocked `execute_generate_chapter_with_approval` run with `resource_binding_target_mismatch`.
- Assert recovery preview returns exactly one `prepare_generate_chapter_execution` tool.
- Assert recovery execution runs only the prepare tool.
- Assert no `generate_chapter` call and no `ChapterContent` write.

Out of scope:
- Changing direct chapter execution guard logic.
- Adding UI confirmation flow.
- Changing chapter generation prompts.

## Files

- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase150-direct-recovery-prepare-only.md`

## Task 1: Direct Binding Recovery Execute Safety Regression

- [x] **Step 1: Add regression test**

Add `test_agent_run_auto_plan_executes_direct_binding_recovery_prepare_only_after_hash_confirmation`:
- seed a longform project with chapter 1 generated and chapter 2 outlined.
- create a direct generate approval contract via `prepare_generate_chapter_execution`.
- force `execute_generate_chapter_with_approval` to block on `resource_binding_target_mismatch`.
- preview recovery tools and capture `plan_hash`.
- execute recovery with `auto_plan`, `execute_recovery`, `confirm_execute`, and `recovery_plan_hash`.
- assert:
  - recovery run input planner mode is `execute`
  - selected tools are only `prepare_generate_chapter_execution`
  - prepare output is `approval_required`
  - `generate_chapter` is not called
  - chapter 2 content does not exist.

- [x] **Step 2: Run targeted test**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_direct_binding_recovery_prepare_only_after_hash_confirmation -q
```

Expected: if current recovery execution is already safe, the test passes without production changes.

## Task 2: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_direct_binding_recovery_prepare_only_after_hash_confirmation backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q
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

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase150-direct-recovery-prepare-only.md`.

- [x] **Step 4: Commit and push**

Commit message:

```text
test: guard direct recovery prepare execution
```
