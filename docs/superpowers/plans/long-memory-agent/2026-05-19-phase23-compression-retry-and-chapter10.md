# Phase 23 Compression Retry and Chapter 10 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chapter compression recover from out-of-range model candidates before continuing the dogfood novel.

**Architecture:** Extend `compress_chapter_to_target` with a bounded retry loop. Each model attempt gets its own trace; failed out-of-range candidates are recorded but not written, and a later in-range candidate is committed with revision/version records. If all attempts miss the range, the tool still blocks without modifying the chapter.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `WritingAgentRunService`, DeepSeek-backed `AIService`, chapter revision/version models, model-call trace, chapter quality review, pytest.

---

## Phase Metadata

- **Phase:** 23
- **Date:** 2026-05-19
- **Verification Tier:** T1 for retry behavior; T2 for dogfood Chapter 9 repair and optional Chapter 10 continuation.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 9 over-target cleanup, then Chapter 10 generation only if gates are clear.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, traces, or logs.

## Starting State

- Generated chapters: 9.
- Pending actionable world-model proposals: 0.
- Target range: 2000-2300 words per chapter.
- Current immediate issue:
  - Chapter 9 `暗河引路`: 2433 words.
  - Phase22 compression attempts produced under-target candidates and were safely rejected.
- Older known length debt:
  - Chapter 1: 3735.
  - Chapter 2: 3511.
  - Chapter 3: 3080.
  - Chapter 5: 2482.

## Problem

Phase22 proved the safety guard works: bad compression candidates are not written. It also exposed a scale problem: prompt-only compression is unreliable for mild over-target chapters. At 600+ chapters, a tool that only fails safely but cannot repair common out-of-range candidates will stall longform generation.

This phase should add a bounded repair loop:

- under-target compression candidate -> ask the model to restore scene density into range;
- over-target compression candidate -> ask the model to trim only enough into range;
- each failed candidate remains traceable;
- only the first in-range candidate can update the chapter;
- all attempts missing the range still block without changing content.

## Success Criteria

- `compress_chapter_to_target` retries out-of-range candidates up to a bounded attempt count.
- The retry prompt includes the prior failed word count and tells the model whether it undershot or overshot.
- Each attempt creates an `AIModelCallTrace`.
- Failed attempts are marked failed and kept in output metadata.
- A later in-range retry creates exactly one completed `ChapterRevision` and base/result `Version` pair.
- If all attempts are outside range, no `ChapterRevision` or `Version` is created and the chapter remains unchanged.
- Tool output includes attempt count and failed attempt summaries.
- Existing compression skip, pending proposal, stop-after-compression, and review behavior still pass.
- Dogfood Chapter 9 is compressed into 2000-2300 words or its blocker is recorded with evidence.
- Chapter 10 is generated only if Chapter 9 has no blocker and world-model proposal pressure is clear.

## Explicit Non-Goals

- Do not build a general rewrite engine.
- Do not change database schema.
- Do not add frontend UI.
- Do not compress Chapters 1-3 and 5 in this phase unless Chapter 10 is blocked by policy.
- Do not allow under-target or over-target candidates to overwrite current chapter content.
- Do not run full frontend verification unless backend contracts change.

## Files

- Modify: `backend/app/core/chapter_compression.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md`

## Task 1: Add Retry Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write retry-success failing test**

Add this test near the Phase22 compression tests:

```python
def test_agent_compress_chapter_to_target_repairs_under_target_retry(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗河引路"
    chapter.content = "林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()

    too_short = "林深和苏晚晴沿着暗河追查线索。 " * 80
    repaired = "林深和苏晚晴沿着暗河追查雾晶管线，确认警报来源。 " * 100
    calls = []

    class FakeAIResult:
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

        def __init__(self, content):
            self.content = json.dumps({"content": content, "change_summary": "压缩并恢复场景密度。"}, ensure_ascii=False)

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult(too_short if len(calls) == 1 else repaired)

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并修复过短候选",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    traces = (
        db_session.query(AIModelCallTrace)
        .filter_by(project_id=project.id, trace_type="chapter_compression", chapter_index=1)
        .order_by(AIModelCallTrace.created_at.asc())
        .all()
    )
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 2
    assert len(output["failed_attempts"]) == 1
    assert output["failed_attempts"][0]["direction"] == "under_target"
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content == repaired.strip()
    assert revision_count == 1
    assert version_count == 2
    assert len(calls) == 2
    assert "上一次压缩结果低于目标下限" in calls[1]
    assert [trace.status for trace in traces] == ["failed", "success"]
```

- [ ] **Step 2: Write retry-failure failing test**

Add:

```python
def test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    original_content = "林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120
    chapter.content = original_content
    chapter.word_count = 3000
    db_session.commit()

    too_short = "林深和苏晚晴沿着暗河追查线索。 " * 80
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": too_short, "change_summary": "仍然过短。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章但候选持续过短",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "compressed_content_outside_target"
    assert output["compression_attempt_count"] == 3
    assert len(output["failed_attempts"]) == 3
    assert len(calls) == 3
    assert patched.content == original_content
    assert revision_count == 0
    assert version_count == 0
```

- [ ] **Step 3: Run RED retry tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion -q
```

Expected: fail because the current implementation stops after the first out-of-range candidate.

## Task 2: Implement Bounded Compression Retry

**Files:**

- Modify: `backend/app/core/chapter_compression.py`

- [ ] **Step 1: Add retry constants and helpers**

Add:

```python
MAX_COMPRESSION_ATTEMPTS = 3


def _target_direction(word_count: int, target_min: int, target_max: int) -> str:
    if word_count < target_min:
        return "under_target"
    if word_count > target_max:
        return "over_target"
    return "within_target"
```

- [ ] **Step 2: Build retry-aware messages**

Extend `_compression_messages` with optional prior failure arguments:

```python
    attempt_index: int = 1,
    prior_candidate: str = "",
    prior_word_count: int | None = None,
    prior_direction: str = "",
```

When `prior_direction == "under_target"`, append:

```text
上一次压缩结果低于目标下限，只有{prior_word_count}字。请以候选稿为基础恢复必要场景密度、动作链、对话和情绪转折，必须回到目标范围。
```

When `prior_direction == "over_target"`, append:

```text
上一次压缩结果仍高于目标上限，约{prior_word_count}字。请只删除重复解释和可合并描写，不要改变剧情事实，必须回到目标范围。
```

Include the prior candidate after the current source text so the model can repair the candidate instead of starting blind.

- [ ] **Step 3: Replace single call with attempt loop**

Use this behavior:

- For each attempt from 1 to `MAX_COMPRESSION_ATTEMPTS`, build messages with prior failure context.
- Create one `AIModelCallTrace` per attempt.
- Call the model.
- Parse JSON and count candidate words.
- If candidate is inside `[target_min, target_max]`, write it once and return success.
- If outside range, mark the attempt trace failed, append a failed-attempt summary, and retry if attempts remain.
- If attempts are exhausted, return blocked with:
  - `reason="compressed_content_outside_target"`;
  - `compression_attempt_count`;
  - `failed_attempts`;
  - last `word_count`.

- [ ] **Step 4: Run GREEN retry tests**

Run the same two retry tests and confirm they pass.

## Task 3: Regression Verification

**Files:**

- Modify: `backend/app/core/chapter_compression.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Run all compression tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_then_review_clears_over_target_warning tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion -q
```

Expected: all pass.

## Task 4: Dogfood Chapter 9 and Chapter 10

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md`

- [ ] **Step 1: Compress Chapter 9**

Run Writing Agent:

```json
[
  {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 9}}
]
```

Expected:

- completed with 2000-2300 words, or blocked with retry evidence;
- if completed, output includes attempt metadata and a revision id.

- [ ] **Step 2: Review and analyze Chapter 9**

If compression completed, run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 9}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 9}}
]
```

Expected:

- no `chapter_over_target`;
- blocker count 0;
- if Athena creates proposals, resolve them before continuing.

- [ ] **Step 3: Generate Chapter 10 only if clear**

If Chapter 9 is within target, has no blockers, and pending proposal count is 0, run:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 10}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 10}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 10}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 10}}
]
```

Expected:

- Chapter 10 generated or blocked with recorded reason.
- Review blocker count is 0 or blockers are recorded and generation stops.
- Pending world-model proposals are recorded and resolved when safe.

## Task 5: Verification, Report, Commit, Push

**Files:**

- Modify all Phase23 files.

- [ ] **Step 1: Run T2 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [ ] **Step 2: Write Phase23 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md` with:

- code changes;
- RED/GREEN evidence;
- Chapter 9 compression result;
- Chapter 9 review/analyze result;
- Chapter 10 generation result or blocker;
- verification commands;
- next phase recommendation.

- [ ] **Step 3: Hygiene checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Expected:

- whitespace check passes;
- secret scan returns no matches;
- only intended Phase23 files are changed.

- [ ] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md
git commit -m "docs: plan long memory agent phase 23"
```

Commit implementation/report after verification:

```powershell
git add backend/app/core/chapter_compression.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase23-compression-retry-and-chapter10.md
git commit -m "feat: retry chapter compression repairs"
git push origin main
```
