# Phase132 Chapter Target Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support shorter continuation phrases such as `下一章` and expose whether the chapter target came from user text or system inference.

**Architecture:** Extend deterministic intent matching only for chapter continuation phrases. Keep database-backed target inference in the dialog API, and add a small `chapter_index_source` field to candidate/pending params so later Agent trace and UI can explain why a chapter was selected.

**Tech Stack:** IntentRouter, dialog API, pytest.

---

## Scope

This phase continues the low-detail input cleanup from Phase130/131. It does not introduce an LLM planner and does not change generated chapter content.

## Files

- Modify: `backend/app/core/intent_router.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase132-chapter-target-source.md`

## Validation Level

T1:

- Targeted router and dialog endpoint tests.
- Full `test_dialogs.py` regression because intent output shape changes.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_intent_router_next_chapter_phrase_uses_chapter_when_outline_ready backend\tests\test_dialogs.py::test_intent_router_projection_marks_explicit_chapter_source backend\tests\test_dialogs.py::test_chat_text_next_chapter_uses_inferred_chapter_source -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Add router test for `下一章`**

```python
def test_intent_router_next_chapter_phrase_uses_chapter_when_outline_ready():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=["content"],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("下一章", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_chapter"
    assert candidate.params["chapter_index"] == 1
    assert candidate.params["chapter_index_source"] == "router_default"
```

- [ ] **Step 2: Add projection test for explicit source**

Update `test_intent_router_projection_explains_chapter_route` to expect:

```python
assert projection["candidate"] == {
    "type": "preview_chapter",
    "params": {"chapter_index": 3, "chapter_index_source": "explicit_user"},
}
assert projection["extracted_params"] == {
    "chapter_index": 3,
    "chapter_index_source": "explicit_user",
}
```

- [ ] **Step 3: Add dialog endpoint test for inferred source**

Add a test where chapter 1 exists, user says `下一章`, and pending params show chapter 2 plus `chapter_index_source == "inferred_next_unwritten"`.

```python
def test_chat_text_next_chapter_uses_inferred_chapter_source(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=2,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雨夜证词", "summary": "林舟追查新的证词。"},
            ],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=pid,
            chapter_index=1,
            title="旧灯塔",
            content="第一章正文",
            status="generated",
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "下一章",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["params"]["chapter_index"] == 2
    assert body["pending_action"]["params"]["chapter_index_source"] == "inferred_next_unwritten"
```

- [ ] **Step 4: Run RED**

Expected:

- `下一章` currently does not match.
- projection does not expose `chapter_index_source`.
- pending params do not expose inferred source.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add chapter source helper in `IntentRouter`**

Use explicit parse result once:

```python
parsed_chapter_index = parse_chapter_index(text)
chapter_index = parsed_chapter_index or 1
chapter_index_source = "explicit_user" if parsed_chapter_index is not None else "router_default"
```

Include `chapter_index_source` in `candidate.params` and `extracted_params` for both explicit chapter rule and low-detail chapter rule.

- [ ] **Step 2: Extend low-detail continuation phrases**

Update `_is_low_detail_chapter_continue` so these exact inputs match:

```text
继续吧
继续写吧
开始写吧
开写吧
往下写
推进吧
继续推进
可以开始了
开始吧
下一章
接着写
继续下一章
```

- [ ] **Step 3: Mark inferred source in dialog API**

In `_chapter_action_params_for_project(...)`, when no explicit chapter number exists and `_first_unwritten_outline_chapter_index(...)` returns a value, set:

```python
params["chapter_index"] = inferred
params["chapter_index_source"] = "inferred_next_unwritten"
```

If there is an explicit chapter number, preserve `explicit_user`.

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests and confirm they pass.
- [ ] Run `backend\tests\test_dialogs.py` regression.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/core/intent_router.py backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase132-chapter-target-source.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase132-chapter-target-source.md
git commit -m "feat: explain chapter target source"
git push origin main
```
