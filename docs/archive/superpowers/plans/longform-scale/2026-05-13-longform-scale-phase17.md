# Longform Scale Phase 17 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound Athena manuscript progress context so long projects do not inject a full chapter list into every Athena chat prompt.

**Architecture:** Keep the existing `manuscript_summary` block contract. For small projects, continue listing all chapters. For large projects, list first chapters, fold the middle range, list latest chapters, and keep recent excerpts. Query summary columns separately from recent full content.

**Tech Stack:** SQLAlchemy, prompt context block builder, Pytest.

---

### Task 1: Bounded Manuscript Summary

**Files:**
- Modify: `backend/app/prompting/providers/dialog.py`
- Test: `backend/tests/test_athena_dialog.py`

- [x] **Step 1: Write failing test**

Create 250 generated chapters and build an Athena chat payload. Assert:
- The manuscript block still reports `已生成章节：250 / 目标 300`.
- It contains chapter 250.
- It contains a folded middle marker.
- It does not list chapter 120.
- `sources` are bounded.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_dialog.py::test_athena_chat_payload_bounds_manuscript_progress_for_long_projects -q`

Expected: FAIL because current context lists chapter 120 and includes all chapter sources.

- [x] **Step 3: Implement bounded context**

Add constants for full-list limit and edge counts. In `build_athena_manuscript_context_block`, fetch summary columns for all chapters, fetch recent full content separately, and render:
- all chapters when count is within limit
- first N, folded middle count, latest N when count exceeds limit

- [x] **Step 4: Run test to verify pass**

Run the same focused pytest command.

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/prompting/providers/dialog.py` and `backend/tests/test_athena_dialog.py`.

- [x] **Step 1: Run focused dialog tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_dialog.py -q`

Expected: PASS.

- [x] **Step 2: Run full verification**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest`
- `cd frontend; npm run test:unit`
- `cd frontend; npm run build`
- `git diff --check`
- exact DeepSeek key scan
- broad secret scan

Expected: all pass; exact key absent; broad scan only contains existing fake sanitizer fixtures.

- [x] **Step 3: Commit**

Commit message: `feat: bound athena manuscript context`
