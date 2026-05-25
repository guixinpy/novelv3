# Phase 21 Agent Chapter Expansion and Chapter 8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Writing Agent a versioned chapter-expansion tool so under-target chapters can be repaired before longform generation continues.

**Architecture:** Add a small internal async tool, `expand_chapter_to_target`, that uses the existing project word target, chapter review finding, chapter version model, revision model, model-call trace, retrieval indexing, and Writing Agent report-stop flow. The tool revises an existing chapter into a fuller complete chapter, refuses to write output that is still below target, and requires `review_chapter_quality` before any further chapter generation.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `WritingAgentRunService`, DeepSeek-backed `AIService`, chapter revision/version models, chapter quality review, pytest.

---

## Phase Metadata

- **Phase:** 21
- **Date:** 2026-05-19
- **Verification Tier:** T1 for expansion tool behavior; T2 for dogfood Chapter 7 expansion, world-model cleanup, and optional Chapter 8 generation.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 7 expansion to at least 2000 words, then Chapter 8 generation if all gates are clear.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, traces, or logs.

## Starting State

- Current branch: `main`
- Generated chapters: 7
- Latest generated chapter: Chapter 7 `苏晚晴的梦境`
- Chapter 7 word count: 1814
- Chapter 7 review status: `warning`
- Known Chapter 7 finding:
  - `chapter_under_target`: 1814 words, below 2000-word minimum.
- Remaining pending world-model proposals after Phase20: 0

## Problem

The system can detect under-target chapters but cannot yet repair them through Agent-owned tooling. Regenerating the full chapter with `generate_chapter` would overwrite the chapter without a revision-specific intent and could lose usable prose. Manual editing would break the goal of a self-orchestrating longform writing Agent.

This phase adds a controlled expansion path:

- Expand existing prose instead of replacing it with a fresh chapter draft.
- Preserve plot facts and chapter title.
- Add scene density, action/reaction beats, sensory detail, tension, and transitions.
- Version before and after the expansion.
- Reject model output that is still under the target minimum.
- Require a quality review before further chapter generation.

## Success Criteria

- Writing Agent supports `expand_chapter_to_target`.
- The tool only operates on existing generated chapters.
- The tool blocks if the chapter is already within target range.
- The tool blocks if unresolved world-model proposals exist.
- The tool creates a `ChapterRevision` row with `completed` status.
- The tool creates base and result `Version` rows.
- The tool records an `AIModelCallTrace` with sanitized prompt/messages and token metadata.
- The tool updates `ChapterContent.content`, `word_count`, and `Project.current_word_count`.
- The tool reindexes chapter retrieval after the update.
- The tool returns `should_generate_next_chapter=False` and recommends `review_chapter_quality`.
- Tests prove a successful expansion updates versions and clears `chapter_under_target` after review.
- Tests prove the Agent blocks direct generation after expansion unless review runs first.
- Dogfood Chapter 7 reaches `word_count >= 2000`.
- Dogfood Chapter 7 review has `blocker_count=0`.
- Chapter 8 is generated only after Chapter 7 has no blockers and world-model proposal pressure is clear.

## Explicit Non-Goals

- Do not build a general rewrite engine.
- Do not add frontend UI.
- Do not change database schema.
- Do not merge world-model proposals directly from the expansion tool.
- Do not let the tool invent new plot facts or future reveals.
- Do not run full frontend verification unless backend changes unexpectedly touch frontend contracts.

## Files

- Create: `backend/app/core/chapter_expansion.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase21-agent-chapter-expansion-and-chapter8.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase21-agent-chapter-expansion-and-chapter8.md`

## Task 1: Add Agent-Owned Chapter Expansion Tool

**Files:**

- Create: `backend/app/core/chapter_expansion.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing expansion test**

Add a test near the chapter revision agent tests:

```python
def test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "苏晚晴的梦境"
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    project.current_word_count = 600
    db_session.commit()

    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            assert "不要新增世界模型事实" in messages[-1]["content"]
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写第1章到目标字数",
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    versions = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["previous_word_count"] == 600
    assert output["word_count"] >= 2000
    assert patched.content == expanded_content
    assert patched.word_count >= 2000
    db_session.refresh(project)
    assert project.current_word_count == patched.word_count
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert len(versions) == 2
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["review_chapter_quality"]
```

- [x] **Step 2: Run RED expansion test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review -q
```

Expected: fail because `app.core.chapter_expansion` or `expand_chapter_to_target` does not exist.

Evidence: failed with `ModuleNotFoundError: No module named 'app.core.chapter_expansion'`.

- [x] **Step 3: Implement `chapter_expansion.py`**

Create `expand_chapter_to_target`:

```python
async def expand_chapter_to_target(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    min_word_count: int | None = None,
    extra_instruction: str = "",
) -> dict[str, Any]:
    ...
```

Required behavior:

- Load `Project` and `ChapterContent`.
- Resolve target minimum from explicit `min_word_count` or `project_chapter_word_range(project)[0]`.
- Return blocked `missing_project`, `missing_chapter`, or `missing_word_target` as needed.
- If current word count is already at or above target minimum, return `status="skipped"` and `should_generate_next_chapter=True`.
- Check pending actionable world-model proposals using `ProjectProfileVersion`, `WorldProposalItem`, and `ACTIONABLE_REVIEW_ITEM_STATUSES`; block with `reason="pending_world_model_proposals"` if count is greater than zero.
- Build an expansion prompt with chapter title, current word count, target minimum, outline chapter if available, current content, and constraints:
  - keep the same chapter title;
  - preserve current plot facts;
  - do not reveal future outline content;
  - do not add new world-model facts;
  - increase scene density and character reactions;
  - return JSON with `content` and `change_summary`.
- Create an `AIModelCallTrace` before the call.
- Call `AIService().complete(..., response_format={"type": "json_object"})`.
- Parse JSON via `parse_json_safely`.
- Count words using `count_words`.
- If expanded content is still below target minimum, mark trace failed and return blocked `expanded_content_under_target` without changing chapter content.
- Create a completed `ChapterRevision`, base `Version`, update chapter content/word count, reconcile `project.current_word_count`, create result `Version`, mark trace success, and commit.
- Reindex chapter retrieval with `index_chapter_retrieval`; record warning if it fails but do not fail the expansion.

- [x] **Step 4: Register Writing Agent tool**

In `backend/app/services/writing_agent/run_service.py`:

- Add `expand_chapter_to_target` to `ALLOWED_TOOLS` and `INTERNAL_TOOLS`.
- Add async execution branch:

```python
if tool.tool_name == "expand_chapter_to_target":
    from app.core.chapter_expansion import expand_chapter_to_target

    chapter_index = int(tool.params.get("chapter_index") or 1)
    min_word_count = _optional_int(tool.params.get("min_word_count"))
    extra_instruction = str(tool.params.get("extra_instruction") or "")
    return await expand_chapter_to_target(
        self.db,
        project_id,
        chapter_index,
        min_word_count=min_word_count,
        extra_instruction=extra_instruction,
    )
```

- Add target type `revision`.
- Add it to `_should_stop_after_report`.
- Allow follow-up `("expand_chapter_to_target", "review_chapter_quality")`.
- Add block message: `章节扩写后尚未复审，已停止后续写作工具。`

- [x] **Step 5: Run GREEN expansion test**

Run the same test and confirm it passes.

Evidence: focused Phase21 expansion/gate tests passed with `5 passed in 0.60s`.

## Task 2: Verify Expansion Gate Behavior

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add review-after-expansion test**

Add:

```python
def test_agent_expand_chapter_to_target_then_review_clears_under_target_warning(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "苏晚晴的梦境"
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    db_session.commit()
    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写并复审",
            "tools": [
                {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_under_target" not in codes
    assert review["blocker_count"] == 0
```

- [x] **Step 2: Add direct-generation stop test**

Add:

```python
def test_agent_expand_chapter_to_target_blocks_direct_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    db_session.commit()
    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写后直接生成下一章",
            "tools": [
                {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["expand_chapter_to_target"]
    assert calls == []
```

- [x] **Step 3: Run GREEN gate tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_then_review_clears_under_target_warning tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_blocks_direct_followup_generation -q
```

Expected: all pass.

Evidence: `5 passed in 0.60s`, including expansion success, review follow-up, direct generation stop, already-at-target skip, and pending world-model proposal block.

## Task 3: Dogfood Chapter 7 Expansion and Chapter 8 Continuation

**Files:**

- Create report under `docs/superpowers/notes/long-memory-agent/`.

- [x] **Step 1: Expand Chapter 7**

Run Writing Agent:

```json
[
  {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 7}}
]
```

Expected:

- status `completed`;
- previous word count `1814`;
- new word count `>= 2000`;
- revision status `completed`;
- base/result versions populated;
- no pending world-model proposals before expansion.

Evidence: run `8f1dbbf6-7908-4a00-a659-ac6b5dadfd83` completed revision `d4e593ef-7117-4390-8251-3d47ec21035f`, trace `b93eb4ab-bae6-48a7-8d07-3f97e6b36b10`, and expanded Chapter 7 from 1814 to 2670 words. This cleared the lower bound but produced an upper-bound warning for later tuning.

- [x] **Step 2: Review and analyze Chapter 7**

Run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 7}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 7}}
]
```

Expected:

- `chapter_under_target` absent;
- `blocker_count=0`;
- if Athena creates world-model proposals, resolve them through existing `draft_world_model_proposal_resolution_decisions` and `apply_world_model_proposal_resolution`.

Evidence: run `450fea79-f230-4103-80fa-2fa50ac2dcfc` returned `blocker_count=0`, no `chapter_under_target`, no new world-model proposals, and duplicate analysis skips only.

- [x] **Step 3: Generate Chapter 8 only if clear**

If Chapter 7 has no blockers and pending world-model proposal count is 0, run:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 8}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 8}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 8}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 8}}
]
```

Expected:

- Chapter 8 generated;
- review blocker count is 0 or blockers are recorded and generation stops;
- word count is at least 2000 or a Phase22 follow-up is recorded.

Evidence: run `2efb467b-08e5-4378-82a1-edfa99839927` generated Chapter 8 `废弃实验室` at 2647 words with `blocker_count=0`; world-model queue of 7 proposals was cleared by runs `cd4606a1-ee15-4e92-9f36-be41e5e66bed` and `2def5806-d5a2-4fe8-96eb-1832a16306a1`.

## Task 4: Verification, Report, Commit, Push

**Files:**

- Modify all Phase21 files.

- [x] **Step 1: Run T2 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

Evidence: `133 passed in 9.94s`.

- [x] **Step 2: Write Phase21 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase21-agent-chapter-expansion-and-chapter8.md` with:

- code changes;
- RED/GREEN evidence;
- dogfood Chapter 7 expansion run id;
- Chapter 7 review/analyze result;
- Chapter 8 generation/review result or blocker reason;
- verification commands;
- next phase recommendation.

- [x] **Step 3: Hygiene checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Expected:

- whitespace check passes;
- secret scan returns no matches;
- only intended Phase21 files are changed.

Evidence: `git diff --check` passed, secret scan returned no matches, and `git status --short --branch` showed only intended Phase21 code/test/docs files.

- [x] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase21-agent-chapter-expansion-and-chapter8.md
git commit -m "docs: plan long memory agent phase 21"
```

Commit implementation/report after verification:

```powershell
git add backend/app/core/chapter_expansion.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase21-agent-chapter-expansion-and-chapter8.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase21-agent-chapter-expansion-and-chapter8.md
git commit -m "feat: expand under-target chapters"
git push origin main
```

Evidence: implementation/report committed as `d26a7d4 feat: expand under-target chapters` before this checklist update was amended into the same implementation commit, then pushed to `origin/main`.
