# Writing Task Agent Provenance Phase70 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve Agent run provenance in continuous writing background task results.

**Architecture:** After Phase69, `build_generate_chapter_work()` and `build_retry_chapter_work()` call the direct chapter generation endpoint function, which now returns `agent_run_id` and `control_plane`. Keep existing `generate_chapter` task type and range progress behavior, but copy each chapter's Agent provenance into the background task result so long-running writing can be audited and resumed with visible Agent links.

**Tech Stack:** FastAPI background task service, pytest, existing chapter Agent entrypoint.

---

## Reference Assimilation

- `openclaw`: background work should expose the control-plane unit it executed.
- `hermes-agent`: long tasks should retain per-step/run provenance.
- `openhuman`: parent task summary should stay compact while preserving references to detailed runs.

## Files

- Modify `backend/app/api/writing.py`
  - Collect `agent_run_id` from generated chapters.
  - Add `agent_run_id` for single/latest generated chapter.
  - Add `agent_runs` list for range generation.
  - Apply the same provenance recording to retry work.
- Modify `backend/tests/test_writing.py`
  - Add focused tests for range work and retry work provenance.
- Add Phase70 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Range Provenance Test

- [x] Add test in `backend/tests/test_writing.py`:

```python
@pytest.mark.asyncio
async def test_generate_chapter_work_records_agent_run_provenance(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Agent Provenance Range", "target_chapter_count": 2})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=2,
        payload={"chapter_index": 1},
    )
    WritingStateService(db_session).run_chapter(pid, 1)

    async def fake_generate_chapter(project_id: str, chapter_index: int, db):
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {
            "chapter_index": chapter_index,
            "agent_run_id": f"run-{chapter_index}",
            "control_plane": {"source": "chapter_generate", "chapter_index": chapter_index},
        }

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate_chapter)
    from app.api.writing import build_generate_chapter_work

    result = await build_generate_chapter_work(pid, 1)(db_session, task)

    assert result["agent_run_id"] == "run-2"
    assert result["agent_runs"] == [
        {"chapter_index": 1, "agent_run_id": "run-1", "control_plane": {"source": "chapter_generate", "chapter_index": 1}},
        {"chapter_index": 2, "agent_run_id": "run-2", "control_plane": {"source": "chapter_generate", "chapter_index": 2}},
    ]
```

- [x] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "agent_run_provenance"
```

Expected before implementation: fails because result does not include `agent_run_id` or `agent_runs`.

## Task 2: RED Retry Provenance Test

- [x] Add test:

```python
@pytest.mark.asyncio
async def test_retry_chapter_work_records_agent_run_provenance(client, db_session, monkeypatch):
    project_id = client.post("/api/v1/projects", json={"name": "Retry Agent Provenance"}).json()["id"]
    task = BackgroundTaskService(db_session).create(
        project_id=project_id,
        task_type="retry_chapter",
        payload={"chapter_index": 3},
    )

    async def fake_generate_chapter(project_id: str, chapter_index: int, db):
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {
            "chapter_index": chapter_index,
            "agent_run_id": "run-retry-3",
            "control_plane": {"source": "chapter_generate", "chapter_index": 3},
        }

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate_chapter)
    from app.api.writing import build_retry_chapter_work

    result = await build_retry_chapter_work(project_id, 3)(db_session, task)

    assert result == {
        "chapter_index": 3,
        "agent_run_id": "run-retry-3",
        "control_plane": {"source": "chapter_generate", "chapter_index": 3},
    }
```

## Task 3: Implementation

- [x] Add helper in `backend/app/api/writing.py`:

```python
def _chapter_agent_provenance(chapter) -> dict | None:
    agent_run_id = chapter.get("agent_run_id") if isinstance(chapter, dict) else getattr(chapter, "agent_run_id", None)
    if not agent_run_id:
        return None
    chapter_index = _generated_chapter_index(chapter)
    control_plane = chapter.get("control_plane") if isinstance(chapter, dict) else getattr(chapter, "control_plane", None)
    item = {"chapter_index": chapter_index, "agent_run_id": str(agent_run_id)}
    if isinstance(control_plane, dict):
        item["control_plane"] = control_plane
    return item
```

- [x] In `build_generate_chapter_work()`, collect provenance:

```python
agent_runs: list[dict] = []
...
if provenance := _chapter_agent_provenance(chapter):
    agent_runs.append(provenance)
...
if agent_runs:
    result["agent_runs"] = agent_runs
    result["agent_run_id"] = agent_runs[-1]["agent_run_id"]
```

- [x] In `build_retry_chapter_work()`, return provenance fields when present.

## Task 4: Verification

- [x] Run focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "agent_run_provenance"
```

- [x] Run related T1/T2 backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py tests\test_chapters.py tests\test_background.py -q
```

- [x] Static checks and secret scan:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

- [x] Write Phase70 report.
- [x] Commit and push to `main`.

## Boundaries

Do:

- expose Agent provenance in continuous writing task results;
- preserve existing task type and range progress behavior;
- keep fake-generation tests compatible when no Agent metadata is returned.

Do not:

- change task type to `writing_agent_run` yet;
- rewrite queue/resume semantics;
- run real model generation in tests;
- add frontend display in this phase.
