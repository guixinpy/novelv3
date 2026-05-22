# Phase127 Agent Trace Event Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified, read-only `event_chain` to `inspect_agent_trace_audit` so the Agent can inspect approval, dispatch, tool, trace, and result boundaries in order.

**Architecture:** Reuse existing summaries from `run`, `steps`, `traces`, `approval_events`, and `dialog_events`. Do not create tables or mutate runtime behavior. The chain is a bounded audit projection, not a new source of truth.

**Tech Stack:** Existing Writing Agent trace audit service and pytest.

---

## Scope

Phase127 turns the Phase125/126 data into one ordered list:

1. `approval_decision`
2. `run_dispatched`
3. `tool_step`
4. `trace_attached`
5. `result_message`

It does not expose raw prompt/context/action data and does not implement start/complete event persistence yet.

## Files

- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
  - Build `event_chain`.
  - Add `event_chain_count` to `audit`.
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
  - Extend approval trace test to verify event chain order and sanitized fields.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase127-agent-trace-event-chain.md`

## Validation Level

T1:

- Single backend read projection.

Commands:

- Targeted:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Test

**Files:**
- Modify: `backend/tests/test_writing_agent_trace_audit.py`

- [ ] **Step 1: Add trace and step fixtures to approval test**

Create an `AIModelCallTrace` and a `WritingAgentStep` for the run, then assert:

```python
assert [event["event_type"] for event in output["event_chain"]] == [
    "approval_decision",
    "run_dispatched",
    "tool_step",
    "trace_attached",
    "result_message",
]
assert output["event_chain"][0]["decision_label"] == "已确认"
assert output["event_chain"][1]["run_id"] == run.id
assert output["event_chain"][2]["tool_name"] == "generate_chapter"
assert output["event_chain"][3]["trace_id"] == "trace-chain"
assert output["event_chain"][4]["message_id"] == result_message.id
assert "approval:secret-hash" not in str(output["event_chain"])
assert output["audit"]["event_chain_count"] == 5
```

- [ ] **Step 2: Run RED**

Expected: FAIL because `event_chain` is missing.

## Task 2: Minimal Implementation

**Files:**
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`

- [ ] **Step 1: Add `_event_chain(...)` helper**

Inputs: `run`, `steps`, `trace_items`, `approval_events`, `dialog_events`.

Output event dictionaries:

- approval decision: `event_type/message_id/action_type/decision/decision_label`
- run dispatched: `event_type/run_id/status/entrypoint/background_task_id`
- tool step: `event_type/step_id/step_index/tool_name/status/trace_id/target_type/target_id/chapter_index`
- trace attached: `event_type/trace_id/trace_type/status/chapter_index/context_block_count`
- result message: `event_type/message_id/action_type/action_status`

- [ ] **Step 2: Include in output and audit**

Add top-level `event_chain` and `audit.event_chain_count`.

## Task 3: Verify, Document, Commit

- [ ] Run targeted and regression tests.
- [ ] Run hygiene checks.
- [ ] Write report.
- [ ] Commit:

```powershell
git add backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_writing_agent_trace_audit.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase127-agent-trace-event-chain.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase127-agent-trace-event-chain.md
git commit -m "feat: add agent trace event chain"
git push origin main
```
