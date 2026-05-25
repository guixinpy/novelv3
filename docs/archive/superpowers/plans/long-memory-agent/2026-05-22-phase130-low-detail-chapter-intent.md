# Phase130 Low Detail Chapter Intent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let low-detail natural language such as `继续吧` create a chapter pending action when the project is already ready for chapter writing.

**Architecture:** Extend the deterministic `IntentRouter` with a conservative low-detail chapter rule. The rule only fires when `outline` is completed; it rejects inputs that mention setup/storyline/outline to avoid stealing other intents. This accounts for the current diagnosis behavior where a project with outline but no chapter content may still suggest `preview_outline`.

**Tech Stack:** Existing dialog intent router, dialog chat API, pytest.

---

## Scope

This phase addresses a dogfood issue: `/chapter` reliably creates chapter pending actions, but low-detail natural language can fall back to free chat. The fix should improve Agent autonomy without requiring long user prompts.

This phase does not call an LLM and does not generate a chapter. It only improves intent-to-pending-action routing.

## Files

- Modify: `backend/app/core/intent_router.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase130-low-detail-chapter-intent.md`

## Validation Level

T1:

- Local deterministic router and dialog endpoint behavior only.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_intent_router_low_detail_continue_uses_chapter_when_outline_ready backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_creates_pending_chapter_action -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Add router test**

Add:

```python
def test_intent_router_low_detail_continue_uses_chapter_when_outline_ready():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=["content"],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("继续吧", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_chapter"
    assert candidate.params["chapter_index"] == 1
```

- [ ] **Step 2: Add dialog endpoint test**

Copy the existing project seeding pattern from `test_chat_text_start_writing_creates_pending_chapter_action`, but use text `继续吧`.

- [ ] **Step 3: Run RED**

Expected: tests fail because `继续吧` currently falls through to free chat.

## Task 2: Minimal Router Implementation

- [ ] **Step 1: Add low-detail helper**

Add helper functions:

```python
def _is_chapter_ready(diagnosis: ProjectDiagnosisOut) -> bool:
    return "outline" in diagnosis.completed_items


def _mentions_other_planning_layer(text: str) -> bool:
    return bool(re.search(r"(设定|世界观|故事线|主枝干|大纲)", text))
```

- [ ] **Step 2: Add low-detail rule after explicit chapter rule**

If `_is_chapter_ready(diagnosis)` and not `_mentions_other_planning_layer(text)` and text matches `继续吧|开始写吧|往下写|推进吧|开写吧|继续写吧`, return `preview_chapter` with `chapter_index = parse_chapter_index(text) or 1`.

Use `rule_id="chapter_intent"` and match evidence name `low_detail_continue_phrase`.

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests.
- [ ] Run dialog regression subset.
- [ ] Run hygiene checks.
- [ ] Write report.
- [ ] Commit:

```powershell
git add backend/app/core/intent_router.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase130-low-detail-chapter-intent.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase130-low-detail-chapter-intent.md
git commit -m "feat: route low detail chapter intents"
git push origin main
```
