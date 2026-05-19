# Phase 22 Agent Chapter Compression and Chapter 9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Agent-owned compression tool for over-target chapters, then use it to bring the active dogfood novel back toward the 2000-2300 word target range before continuing generation.

**Architecture:** Add a conservative async Writing Agent tool, `compress_chapter_to_target`, parallel to `expand_chapter_to_target`. It compresses only existing generated chapters above the project target max, versions before/after, writes a trace, rejects output outside the target range, and requires `review_chapter_quality` before any further chapter generation.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `WritingAgentRunService`, DeepSeek-backed `AIService`, chapter revision/version models, model-call trace, chapter quality review, pytest.

---

## Phase Metadata

- **Phase:** 22
- **Date:** 2026-05-19
- **Verification Tier:** T1 for compression behavior; T2 for dogfood compression, world-model queue cleanup, and optional Chapter 9 generation.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 7/8 over-target cleanup, then Chapter 9 generation only if gates are clear.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, traces, or logs.

## Starting State

- Generated chapters: 8
- Pending world-model proposals: 0
- Target range: 2000-2300 words per chapter.
- Current over-target chapters:
  - Chapter 7 `苏晚晴的梦境`: 2670
  - Chapter 8 `废弃实验室`: 2647
- Current broader length risk:
  - Chapter 1: 3735
  - Chapter 2: 3511
  - Chapter 3: 3080
  - Chapter 5: 2482

## Problem

Phase21 fixed the under-target failure mode but exposed the opposite risk: the Agent can now overshoot the upper target, and the longform project already has multiple over-target chapters. Continuing generation without a compression tool will accumulate scale drift and make 600+ chapters harder to stabilize.

This phase should add a repair path for `chapter_over_target`:

- compress existing prose rather than regenerating a fresh chapter;
- preserve plot facts, character intent, chapter title, and ending hook;
- remove repetition, redundant explanation, and overlong internal monologue;
- reject model output outside the 2000-2300 target range;
- version and trace the change;
- force a review before continuing.

## Success Criteria

- Writing Agent supports `compress_chapter_to_target`.
- The tool only operates on existing generated chapters.
- The tool skips chapters already inside the target range.
- The tool blocks if unresolved world-model proposals exist.
- The tool creates a completed `ChapterRevision`.
- The tool creates base and result `Version` rows.
- The tool records an `AIModelCallTrace`.
- The tool updates `ChapterContent.content`, `word_count`, and `Project.current_word_count`.
- The tool reindexes chapter retrieval after writing.
- The tool returns `should_generate_next_chapter=False` and recommends `review_chapter_quality`.
- Tests prove a successful compression lands inside the target range and clears `chapter_over_target` after review.
- Tests prove direct follow-up generation is blocked until review.
- Dogfood Chapter 7 and Chapter 8 no longer have `chapter_over_target`.
- Chapter 9 is generated only after current world-model proposal pressure is clear and latest reviewed chapters have no blockers.

## Explicit Non-Goals

- Do not build a general rewrite engine.
- Do not change database schema.
- Do not add frontend UI.
- Do not compress old Chapters 1-3 in this phase unless required by gates.
- Do not merge world-model proposals from the compression tool.
- Do not run full frontend verification unless backend contracts change.

## Files

- Create: `backend/app/core/chapter_compression.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase22-agent-chapter-compression-and-chapter9.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase22-agent-chapter-compression-and-chapter9.md`

## Task 1: Add Agent-Owned Compression Tool

**Files:**

- Create: `backend/app/core/chapter_compression.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing compression test**

Add this test near the Phase21 expansion tests in `backend/tests/test_writing_agent_runs.py`:

```python
def test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "废弃实验室"
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()

    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            assert "压缩到目标字数范围" in messages[-1]["content"]
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章到目标字数",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    versions = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).all()
    db_session.refresh(project)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["previous_word_count"] == 3000
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content == compressed_content.strip()
    assert 2000 <= patched.word_count <= 2300
    assert project.current_word_count == patched.word_count
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert len(versions) == 2
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["review_chapter_quality"]
```

- [x] **Step 2: Run RED compression test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review -q
```

Expected: fail because `app.core.chapter_compression` does not exist.

Actual: failed as expected with `ModuleNotFoundError: No module named 'app.core.chapter_compression'`.

- [x] **Step 3: Implement `chapter_compression.py`**

Create `compress_chapter_to_target` with this public signature:

```python
async def compress_chapter_to_target(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    target_max_word_count: int | None = None,
    extra_instruction: str = "",
) -> dict[str, Any]:
    ...
```

Required behavior:

- Load `Project` and `ChapterContent`.
- Resolve target range from `project_chapter_word_range(project)`.
- Block `missing_project`, `missing_chapter`, `chapter_not_generated`, or `missing_word_target`.
- If current word count is already `<= target_max`, return `status="skipped"`, `reason="chapter_already_within_target"`, and avoid model calls.
- Block with `pending_world_model_proposals` if actionable world-model proposals exist.
- Build prompt containing chapter title, current content, target range, outline chapter, and constraints:
  - preserve plot facts and chapter ending hook;
  - do not add world-model facts;
  - do not reveal future outline content;
  - remove repetition, redundant exposition, and overlong monologue;
  - output JSON with `content` and `change_summary`.
- Create `AIModelCallTrace` before calling the model.
- Call `AIService().complete(..., response_format={"type": "json_object"})`.
- Parse JSON with `parse_json_safely`.
- Count words using `count_words`.
- If output word count is outside `[target_min, target_max]`, mark trace failed and return blocked without changing chapter.
- Create completed `ChapterRevision`, base `Version`, update chapter content/word count, update `Project.current_word_count`, create result `Version`, mark trace success, and commit.
- Reindex chapter retrieval after commit; store warning if indexing fails.

- [x] **Step 4: Register Writing Agent tool**

In `backend/app/services/writing_agent/run_service.py`:

- Add `compress_chapter_to_target` to `ALLOWED_TOOLS` and `INTERNAL_TOOLS`.
- Add async execution branch:

```python
if tool.tool_name == "compress_chapter_to_target":
    from app.core.chapter_compression import compress_chapter_to_target

    chapter_index = int(tool.params.get("chapter_index") or 1)
    target_max_word_count = _optional_int(tool.params.get("target_max_word_count"))
    extra_instruction = str(tool.params.get("extra_instruction") or "")
    return await compress_chapter_to_target(
        self.db,
        project_id,
        chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=extra_instruction,
    )
```

- Add target type `revision`.
- Add it to `_should_stop_after_report`.
- Allow follow-up `("compress_chapter_to_target", "review_chapter_quality")`.
- Add block message: `章节压缩后尚未复审，已停止后续写作工具。`

- [x] **Step 5: Run GREEN compression test**

Run the same test and confirm it passes.

Actual: focused compression behavior passed as part of the five-test GREEN run below.

## Task 2: Verify Compression Gate Behavior

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add review-after-compression and stop tests**

Add:

```python
def test_agent_compress_chapter_to_target_then_review_clears_over_target_warning(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "废弃实验室"
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    db_session.commit()
    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
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
            "goal": "压缩并复审",
            "tools": [
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_over_target" not in codes
    assert "chapter_under_target" not in codes
    assert review["blocker_count"] == 0


def test_agent_compress_chapter_to_target_blocks_direct_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    db_session.commit()
    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩后直接生成下一章",
            "tools": [
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["compress_chapter_to_target"]
    assert calls == []
```

- [x] **Step 2: Add skip and pending-proposal tests**

Add:

```python
def test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    chapter.word_count = 2100
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called for an already-target chapter")

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩已达标章节",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_within_target"
    assert calls == []


def test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase22.pending",
        predicate="role",
        subject_ref="char.林深",
    )
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called when world proposals are pending")

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "存在世界模型提案时压缩",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "pending_world_model_proposals"
    assert output["pending_world_model_proposal_count"] == 1
    assert calls == []
```

- [x] **Step 3: Run GREEN gate tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_then_review_clears_over_target_warning tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals -q
```

Expected: all pass.

Actual: `5 passed in 0.61s`.

## Task 3: Dogfood Chapter 7/8 Compression and Chapter 9 Continuation

**Files:**

- Create report under `docs/superpowers/notes/long-memory-agent/`.

- [x] **Step 1: Compress Chapter 7 and Chapter 8**

Run Writing Agent twice:

```json
[
  {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 7}}
]
```

```json
[
  {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 8}}
]
```

Expected:

- both runs `completed`;
- both previous word counts above 2300;
- both new word counts in `2000-2300`;
- each creates completed revision and base/result versions.

Actual:

- Chapter 7 first compression was safely blocked because the model output was below target (`29f9ebd9-24f7-42b4-81fb-c4ce2b950bbc`), then succeeded after prompt tightening (`7f2d9d05-d9d3-48c1-a56b-d4adfb891d51`), reducing 2670 -> 2025.
- Chapter 8 compression succeeded (`7c91d6d6-7db8-4606-a92f-c351405ed011`), reducing 2647 -> 2142.

- [x] **Step 2: Review and analyze compressed chapters**

Run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 7}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 8}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 7}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 8}}
]
```

Expected:

- no `chapter_over_target` for Chapters 7 and 8;
- no blockers;
- if Athena creates proposals, resolve them with existing `draft_world_model_proposal_resolution_decisions` and `apply_world_model_proposal_resolution`.

Actual: review/analyze run `b1915d63-6144-47d4-8b9e-e4b9555d3073`; Chapter 7/8 reviews were ready, blocker count 0, and analysis created no new actionable proposals.

- [x] **Step 3: Generate Chapter 9 only if clear**

If pending world-model proposal count is 0 and Chapter 7/8 have no blockers, run:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 9}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 9}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 9}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 9}}
]
```

Expected:

- Chapter 9 generated or blocked with recorded reason;
- review blocker count is 0 or blockers are recorded and generation stops;
- if Chapter 9 is over target, record it as Phase23 input.

Actual:

- Initial Chapter 9 preflight was blocked because the outline lacked Chapter 9 (`ce3ffd85-227a-41ed-ac90-fc0791e8fdc4`).
- Outline window expansion added Chapter 9 (`76b5e6a3-e912-492c-b922-60d28b1bd221`).
- Chapter 9 was generated as `暗河引路` (`6a28efb8-7fe1-4dd6-9d81-1c468da4ecfa`) at 2433 words, with no blockers but an over-target warning and 6 world-model proposals.
- The 6 proposals were drafted and applied (`59db2d5f-884b-4c38-9c54-3dd4071af287`, `1c6b7fec-be96-4457-8d43-ad3cf3b4dd6d`), leaving 0 actionable proposals.
- Chapter 9 compression attempts were blocked without writing because model outputs were under target (`7294b2f4-000d-4efb-9daa-7f4439306611`, `6f9b42ca-c36b-41c6-8ba8-71b3efdb22b8`). This is recorded as Phase23 input.

## Task 4: Verification, Report, Commit, Push

**Files:**

- Modify all Phase22 files.

- [x] **Step 1: Run T2 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

Actual: `138 passed in 9.74s`.

- [x] **Step 2: Write Phase22 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase22-agent-chapter-compression-and-chapter9.md` with:

- code changes;
- RED/GREEN evidence;
- dogfood compression run ids;
- Chapter 7/8 review/analyze results;
- Chapter 9 generation/review result or blocker reason;
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
- only intended Phase22 files are changed.

Actual:

- `git diff --check`: exit 0; Git reported only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`: no matches.
- `git status --short --branch`: only intended Phase22 files changed, plus the prior Phase22 plan commit ahead of origin.

- [x] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase22-agent-chapter-compression-and-chapter9.md
git commit -m "docs: plan long memory agent phase 22"
```

Commit implementation/report after verification:

```powershell
git add backend/app/core/chapter_compression.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase22-agent-chapter-compression-and-chapter9.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase22-agent-chapter-compression-and-chapter9.md
git commit -m "feat: compress over-target chapters"
git push origin main
```
