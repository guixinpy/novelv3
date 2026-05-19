# Phase34 Revision Postconditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent chapter compression/revision tools from reporting `completed` when the revised content still contains explicitly forbidden terms.

**Architecture:** Keep the existing compression pipeline and retry loop. Add an optional `forbidden_terms` tool parameter that becomes a deterministic postcondition: every candidate must be in the target length range and must remove all forbidden terms before it can be written back.

**Tech Stack:** FastAPI Writing Agent tool layer, `backend/app/core/chapter_compression.py`, SQLAlchemy models, pytest.

---

## Context

Phase33 exposed a concrete dogfood failure:

- Chapter 19 needed the hard N-07 reveal removed.
- The compression tool returned `completed` even though the revised candidate still contained explicitly forbidden reveal phrases.
- Manual deterministic correction was needed after the tool claimed success.

This phase adds a small tool-contract improvement so the Agent can pass exact forbidden phrases and the tool can enforce them before writing a revision.

## Scope

In scope:

- Add `forbidden_terms` support to `compress_chapter_to_target`.
- Thread `forbidden_terms` through the Writing Agent internal tool call.
- Retry when a candidate still contains forbidden terms.
- Block without writing if all attempts still violate forbidden terms.
- Add focused backend tests.

Out of scope:

- Full semantic contradiction detection.
- General natural-language instruction parsing.
- Frontend controls for forbidden terms.
- Retrofitting `expand_chapter_to_target`.

## Files

- Modify: `backend/app/core/chapter_compression.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase34-revision-postconditions.md`
- Update: this plan file as steps complete.

## Task 1: TDD Forbidden Term Postcondition

- [x] **Step 1: Add failing retry test**

Add a test in `backend/tests/test_writing_agent_runs.py` near compression tests:

```python
def test_agent_compress_chapter_to_target_retries_when_forbidden_terms_remain(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗网迷途"
    chapter.content = ("林深追踪N-07线索。苏晚晴低声说我就是N-07。" * 90)
    chapter.word_count = 3600
    db_session.commit()

    calls = []

    class FakeAIResult:
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

        def __init__(self, content):
            self.content = content

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            if len(calls) == 1:
                return FakeAIResult(json.dumps({"content": "林深追踪N-07线索。我就是N-07。" * 80, "change_summary": "仍有残留。"}, ensure_ascii=False))
            return FakeAIResult(json.dumps({"content": "林深追踪N-07线索，确认这只是未验证编号。" * 90, "change_summary": "移除硬确认。"}, ensure_ascii=False))

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩并移除禁用词",
            "tools": [
                {
                    "tool_name": "compress_chapter_to_target",
                    "params": {
                        "chapter_index": 1,
                        "forbidden_terms": ["我就是N-07"],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert output["status"] == "completed"
    assert output["postcondition_retry_count"] == 1
    assert output["remaining_forbidden_terms"] == []
    assert len(calls) == 2
    assert "我就是N-07" not in patched.content
```

- [x] **Step 2: Add failing blocked test**

Add:

```python
def test_agent_compress_chapter_to_target_blocks_when_forbidden_terms_survive_all_attempts(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗网迷途"
    original_content = "林深追踪N-07线索。苏晚晴低声说我就是N-07。" * 90
    chapter.content = original_content
    chapter.word_count = 3600
    db_session.commit()

    class FakeAIResult:
        content = json.dumps({"content": "林深追踪N-07线索。我就是N-07。" * 80, "change_summary": "仍有残留。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩并移除禁用词",
            "tools": [
                {
                    "tool_name": "compress_chapter_to_target",
                    "params": {
                        "chapter_index": 1,
                        "forbidden_terms": ["我就是N-07"],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert output["reason"] == "forbidden_terms_remaining"
    assert output["remaining_forbidden_terms"] == ["我就是N-07"]
    assert patched.content == original_content
```

- [x] **Step 3: Run RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_retries_when_forbidden_terms_remain tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_when_forbidden_terms_survive_all_attempts -q
```

Expected: fail because `forbidden_terms` is ignored and violating candidates can complete.

Result: failed as expected. The retry test had no `postcondition_retry_count`, and the blocked test returned `completed` instead of `blocked`.

- [x] **Step 4: Implement minimal postcondition**

In `backend/app/services/writing_agent/run_service.py`, pass:

```python
forbidden_terms = [str(item).strip() for item in (tool.params.get("forbidden_terms") or []) if str(item).strip()]
...
forbidden_terms=forbidden_terms,
```

In `backend/app/core/chapter_compression.py`:

- Add parameter:

```python
forbidden_terms: list[str] | None = None,
```

- Normalize once:

```python
forbidden_terms = _normalise_forbidden_terms(forbidden_terms)
```

- After length direction is within target, check:

```python
remaining_forbidden_terms = _remaining_forbidden_terms(compressed_content, forbidden_terms)
if compressed_content and direction == "within_target" and not remaining_forbidden_terms:
    break
```

- Record failed attempts with `remaining_forbidden_terms`.
- Before returning blocked, prefer reason `forbidden_terms_remaining` if length is valid but forbidden terms remain.
- Add helpers:

```python
def _normalise_forbidden_terms(terms: list[str] | None) -> list[str]:
    return sorted({str(term).strip() for term in (terms or []) if str(term).strip()})

def _remaining_forbidden_terms(content: str, forbidden_terms: list[str]) -> list[str]:
    return [term for term in forbidden_terms if term in (content or "")]
```

- Add retry guidance in `_compression_messages` when `prior_direction == "forbidden_terms_remaining"`.

- [x] **Step 5: Run GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_retries_when_forbidden_terms_remain tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_when_forbidden_terms_survive_all_attempts -q
```

Expected: both pass.

Result: `2 passed in 0.32s`.

## Task 2: Regression and Dogfood Check

- [x] **Step 1: Run focused regression**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "compress_chapter_to_target or premature_mystery_reveal or review_chapter_quality"
```

Result: `26 passed, 85 deselected in 2.59s`.

- [x] **Step 2: Run current dogfood state check**

Use a read-only script to verify project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

- latest chapter index is at least `19`;
- Chapter 19 has no Phase33 forbidden reveal terms;
- pending world proposals are `0`;
- longform maintenance status is `current`.

Result:

- latest chapter index: `19`;
- Chapter 19 word count: `2322`;
- forbidden reveal terms present: `[]`;
- pending world proposals: `0`;
- longform maintenance: `current`, `ready_for_writing=True`, issue count `0`, latest synced chapter `19`.
- A PowerShell codepage rendering check briefly printed the latest title as mojibake; direct `repr` and codepoint inspection confirmed the stored title is `暗网迷途`.

## Task 3: Report and Commit

- [x] **Step 1: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase34-revision-postconditions.md` with:

- problem observed in Phase33;
- implementation summary;
- validation evidence;
- dogfood state;
- next recommendation.

- [x] **Step 2: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Results:

- Targeted postcondition suite: `2 passed in 0.36s`.
- Focused compression/review regression: `26 passed, 85 deselected in 2.24s`.
- `git diff --check`: passed with only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- Secret scan: no matches.

- [x] **Step 3: Commit and push if checks pass**

Commit and push `main` only after tests and static checks pass.

Result:

- Commit `2a846f7` pushed to `origin/main`.
