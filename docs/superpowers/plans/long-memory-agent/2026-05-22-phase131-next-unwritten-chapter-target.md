# Phase131 Next Unwritten Chapter Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When users say low-detail writing commands such as `继续吧` or run `/chapter` without an explicit chapter number, select the first unwritten outline chapter instead of always defaulting to chapter 1.

**Architecture:** Keep `IntentRouter` deterministic and database-free. Resolve natural language into `preview_chapter`, then let the dialog API enrich chapter params from persisted project state before creating the pending action. Explicit chapter numbers always win.

**Tech Stack:** FastAPI dialog endpoint, SQLAlchemy models, pytest.

---

## Scope

This phase fixes the next blocking autonomy issue from Phase130: low-detail continuation can now enter chapter generation, but still targets chapter 1 when some chapters already exist.

This phase does not change LLM prompts, chapter generation, or the project diagnosis policy.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase131-next-unwritten-chapter-target.md`

## Validation Level

T1:

- Dialog endpoint tests for text intent and slash command behavior.
- Full `test_dialogs.py` regression because dialog routing is shared.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter backend\tests\test_dialogs.py::test_chapter_command_without_index_uses_first_unwritten_outline_chapter -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Add text intent test**

Add a test where outline chapters 1-3 exist and chapter 1 already has generated content. Sending text `继续吧` should create `preview_chapter` for chapter 2.

```python
def test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=3,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雨夜证词", "summary": "林舟追查新的证词。"},
                {"chapter_index": 3, "title": "回声", "summary": "林舟发现回声。"},
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
        "text": "继续吧",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 2
```

- [ ] **Step 2: Add slash command test**

Add a test where `/chapter` has no args and chapter 1 already exists. It should target chapter 2, while existing explicit chapter tests continue to prove explicit numbers win.

```python
def test_chapter_command_without_index_uses_first_unwritten_outline_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
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
        "input_type": "command",
        "command_name": "chapter",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["params"]["chapter_index"] == 2
```

- [ ] **Step 3: Run RED**

Run the targeted command. Expected: both tests fail because preview chapter params still default to chapter 1.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add first-unwritten helper in `backend/app/api/dialogs.py`**

Add private helpers near `_chapter_action_params`:

```python
def _generated_chapter_indexes(db: Session, project_id: str) -> set[int]:
    rows = (
        db.query(ChapterContent.chapter_index)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.content != "",
        )
        .all()
    )
    return {int(row[0]) for row in rows if row[0]}


def _outline_chapter_indexes(db: Session, project_id: str) -> list[int]:
    outline = (
        db.query(Outline)
        .filter(Outline.project_id == project_id, Outline.status == "generated")
        .order_by(Outline.updated_at.desc(), Outline.id.desc())
        .first()
    )
    if outline is None or not isinstance(outline.chapters, list):
        return []
    indexes: list[int] = []
    for chapter in outline.chapters:
        if not isinstance(chapter, dict):
            continue
        value = chapter.get("chapter_index")
        if isinstance(value, int) and value > 0:
            indexes.append(value)
    return indexes


def _first_unwritten_outline_chapter_index(db: Session, project_id: str) -> int | None:
    generated = _generated_chapter_indexes(db, project_id)
    for chapter_index in _outline_chapter_indexes(db, project_id):
        if chapter_index not in generated:
            return chapter_index
    if generated:
        return max(generated) + 1
    return None
```

- [ ] **Step 2: Add project-aware chapter params helper**

```python
def _chapter_action_params_for_project(
    db: Session,
    project_id: str,
    command_args: str | None = None,
    candidate_params: dict | None = None,
) -> dict:
    params = _chapter_action_params(command_args, candidate_params)
    if parse_chapter_index(command_args) is not None:
        return params
    inferred = _first_unwritten_outline_chapter_index(db, project_id)
    if inferred is not None:
        params["chapter_index"] = inferred
    return params
```

- [ ] **Step 3: Use helper in command flow**

Replace:

```python
params.update(_chapter_action_params(parsed_command.args))
```

with:

```python
params.update(_chapter_action_params_for_project(db, payload.project_id, parsed_command.args))
```

- [ ] **Step 4: Use helper in text intent flow**

Replace:

```python
params.update(_chapter_action_params(effective_text, candidate.params))
```

with:

```python
params.update(_chapter_action_params_for_project(db, payload.project_id, effective_text, candidate.params))
```

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests and confirm they pass.
- [ ] Run `backend\tests\test_dialogs.py` regression.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase131-next-unwritten-chapter-target.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase131-next-unwritten-chapter-target.md
git commit -m "feat: infer next unwritten chapter"
git push origin main
```
