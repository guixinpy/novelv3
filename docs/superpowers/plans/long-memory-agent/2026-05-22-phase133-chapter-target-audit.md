# Phase133 Chapter Target Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry chapter target source from pending action confirmation into action result view and agent trace audit.

**Architecture:** Reuse existing approval decision metadata instead of adding a new event table. Store sanitized chapter target fields in `approval_decision`, render localized detail rows in `action_result_view`, and project the same fields in `inspect_agent_trace_audit`.

**Tech Stack:** Dialog approval flow, action result view service, agent trace audit service, pytest.

---

## Scope

This phase makes Phase132's `chapter_index_source` auditable after user confirmation. It does not change how chapter targets are selected.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/actions/action_result_view.py`
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
- Modify: `backend/tests/test_dialogs.py`
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase133-chapter-target-audit.md`

## Validation Level

T1:

- Dialog approval tests for metadata and localized view.
- Trace audit tests for approval event and event chain projection.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_writing_agent_trace_audit.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Extend dialog approval test**

In `test_resolve_chapter_action_confirm_dispatches_prepare_tool`, assert the approval decision contains:

```python
payload = confirmed.json()["action_result"]["data"]
decision = payload["approval_decision"]
assert decision["chapter_index"] == 2
assert decision["chapter_index_source"] == "explicit_user"
```

Also update `result_view["detail_items"]` to include:

```python
{"label": "目标章节", "value": "第2章"}
{"label": "章节来源", "value": "用户指定"}
```

- [ ] **Step 2: Extend trace audit fixture**

In `test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash`, add to the fixture approval decision:

```python
"chapter_index": 2,
"chapter_index_source": "inferred_next_unwritten",
```

Expect `approval_events[0]` and `event_chain[0]` to include both fields plus localized source label:

```python
"chapter_index": 2,
"chapter_index_source": "inferred_next_unwritten",
"chapter_index_source_label": "系统推断",
```

- [ ] **Step 3: Run RED**

Expected: tests fail because approval decision/view/audit do not expose chapter target fields.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add chapter target fields to `_approval_decision_metadata`**

Read from `pending.params`:

```python
chapter_index = params.get("chapter_index")
chapter_index_source = params.get("chapter_index_source")
```

If present, include sanitized fields:

```python
metadata["chapter_index"] = int(chapter_index)
metadata["chapter_index_source"] = str(chapter_index_source)
```

- [ ] **Step 2: Add localized detail rows**

In `action_result_view._detail_items(...)`, after approval mode, add:

```python
if chapter_index:
    items.append({"label": "目标章节", "value": f"第{chapter_index}章"})
if chapter_index_source:
    items.append({"label": "章节来源", "value": _chapter_source_label(chapter_index_source)})
```

Add `_chapter_source_label` mapping:

```python
explicit_user -> 用户指定
inferred_next_unwritten -> 系统推断
router_default -> 默认目标
```

- [ ] **Step 3: Add trace audit projection**

In `_approval_event_summary(...)`, include:

```python
"chapter_index": _optional_int(decision.get("chapter_index")),
"chapter_index_source": chapter_source,
"chapter_index_source_label": _chapter_source_label(chapter_source),
```

Only include source label when source is non-empty.

In `_event_chain(...)`, carry those fields onto the `approval_decision` event.

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests and confirm they pass.
- [ ] Run regression subset.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/app/services/actions/action_result_view.py backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_dialogs.py backend/tests/test_writing_agent_trace_audit.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase133-chapter-target-audit.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase133-chapter-target-audit.md
git commit -m "feat: audit chapter target source"
git push origin main
```
