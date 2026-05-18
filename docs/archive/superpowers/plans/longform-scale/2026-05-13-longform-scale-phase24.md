# Longform Scale Phase 24 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent dialog message APIs from returning an unbounded full chat history when `limit` is omitted.

**Architecture:** Keep explicit pagination behavior stable. Add a service-level default limit so both Hermes and Athena message endpoints return the latest bounded page by default, in ascending display order.

**Tech Stack:** FastAPI, SQLAlchemy, Pytest.

---

### Task 1: Bound Default Dialog Message Reads

**Files:**
- Modify: `backend/app/services/dialog/messages.py`
- Test: `backend/tests/test_dialog_messages_pagination.py`

- [x] **Step 1: Write failing default-limit test**

Add a test that creates 250 Hermes messages, calls `/api/v1/dialog/projects/{project_id}/messages` without a `limit`, and asserts only the latest 80 messages are returned in ascending order.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_dialog_messages_pagination.py::test_dialog_messages_without_limit_returns_latest_default_page -q`

Expected: FAIL because current service returns all messages when `limit` is omitted.

- [x] **Step 3: Implement minimal default limit**

In `DialogMessageService.list_messages`, introduce `DEFAULT_DIALOG_MESSAGE_LIMIT = 80` and use it whenever `limit is None`. Keep the existing latest-first query with final ascending display order.

- [x] **Step 4: Run focused dialog pagination tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_dialog_messages_pagination.py -q`

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/services/dialog/messages.py`, `backend/tests/test_dialog_messages_pagination.py`, and this plan document.

- [x] **Step 1: Run full verification**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest`
- `cd frontend; npm run test:unit`
- `cd frontend; npx vue-tsc --noEmit`
- `cd frontend; npm run build`
- `git diff --check`
- exact DeepSeek key scan
- broad secret scan

Expected: all pass; exact key absent; broad scan only contains existing fake sanitizer fixtures.

- [x] **Step 2: Commit**

Commit message: `perf: bound default dialog message history`
