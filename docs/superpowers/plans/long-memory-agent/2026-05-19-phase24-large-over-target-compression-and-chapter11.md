# Phase 24 Large Over-Target Compression and Chapter 11 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the compression tool repair larger over-target chapters, then use it to clear Chapter 10 before continuing generation.

**Architecture:** Extend the deterministic trim fallback with a safer large-overage mode. The model still gets first chance to produce a valid compression; if it returns an over-target candidate, the fallback removes low-signal sentences while protecting opening, ending, dialogue, named plot terms, and target lower bound.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `compress_chapter_to_target`, model-call traces, chapter revision/version models, chapter quality review, pytest.

---

## Phase Metadata

- **Phase:** 24
- **Date:** 2026-05-19
- **Verification Tier:** T1 for compression behavior; T2 for Chapter 10 dogfood repair and optional Chapter 11 continuation.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 10 over-target cleanup, then Chapter 11 generation only if gates are clear.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, traces, or logs.

## Starting State

- Branch state: local `main` is ahead of `origin/main` by 2 Phase23 commits because GitHub push currently fails with connection reset / port 443 timeout.
- Generated chapters: 10.
- Pending actionable world-model proposals: 0.
- Target range: 2000-2300 words per chapter.
- Immediate blocker:
  - Chapter 10 `空白信纸`: 2878 words.
  - Review blocker: `chapter_over_target`.
  - Phase23 compression failed after 3 attempts; best candidate remained 2822 words.
- Current stable recent chapters:
  - Chapter 7: 2025.
  - Chapter 8: 2142.
  - Chapter 9: 2015.

## Problem

Phase23 solved near-target repair but Chapter 10 showed a larger failure mode: the model can repeatedly return a candidate still far above target. Sentence-level trimming exists, but its threshold is intentionally limited to avoid damaging content. Longform generation needs a bounded, testable repair path for chapters around 2800 words that must land near 2200 words without requiring manual editing every time.

This phase should:

- keep model-first compression;
- improve retry instructions for large over-target candidates;
- add a deterministic large-overage trim that removes low-signal sentences only when it can remain inside target range;
- keep all guards that prevent out-of-range writes;
- use Chapter 10 as the real dogfood validation target.

## Success Criteria

- Compression tests cover a 2800+ word over-target candidate that the model returns unchanged.
- Large-overage deterministic trim can reduce that candidate to 2000-2300 words.
- The trim preserves first and last sentences.
- The trim avoids deleting dialogue and high-signal protected terms when enough other sentences exist.
- The output includes `deterministic_trim_applied=True` and still creates exactly one completed revision/version pair.
- Existing compression retry, skip, pending-proposal, under-target repair, and near-over-target trim tests still pass.
- Dogfood Chapter 10 is compressed into 2000-2300 words or a stronger blocker is recorded with evidence.
- Chapter 11 is generated only if Chapter 10 has no review blocker and pending proposal count is 0.

## Explicit Non-Goals

- Do not change database schema.
- Do not add frontend UI.
- Do not compress older Chapters 1-3 and 5 in this phase.
- Do not relax the final target-range write guard.
- Do not let deterministic trim remove the first or last sentence.
- Do not run frontend verification unless backend contracts change.

## Files

- Modify: `backend/app/core/chapter_compression.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase24-large-over-target-compression-and-chapter11.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase24-large-over-target-compression-and-chapter11.md`

## Task 1: Add Large-Overage Compression Test

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing large-overage trim test**

Add near the Phase23 compression tests:

```python
def test_agent_compress_chapter_to_target_trims_large_over_target_candidate(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    opening = "林深推开第三研究所的铁门，确认门缝里还压着空白信纸。"
    protected_dialogue = "“别碰那张纸。”苏晚晴按住他的手，“雾晶反应还在。”"
    ending = "门后的红灯重新亮起，林深知道名单上的下一个名字已经出现。"
    low_signal = [f"潮湿走廊里回声第{i}次拉长，墙皮落下细小灰尘。" for i in range(160)]
    candidate = opening + protected_dialogue + "".join(low_signal) + ending
    chapter.content = candidate
    chapter.word_count = 2878
    project.current_word_count = 2878
    db_session.commit()
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": candidate, "change_summary": "模型返回仍然超长的候选。"}, ensure_ascii=False)
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
            "goal": "压缩大幅超长章节",
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["deterministic_trim_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert opening in patched.content
    assert protected_dialogue in patched.content
    assert ending in patched.content
    assert revision_count == 1
    assert version_count == 2
    assert len(calls) == 1
```

- [ ] **Step 2: Run RED test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_large_over_target_candidate -q
```

Expected: fail because current trim threshold rejects large over-target candidates.

## Task 2: Implement Safer Large-Overage Trim

**Files:**

- Modify: `backend/app/core/chapter_compression.py`

- [ ] **Step 1: Add large-overage threshold**

Add:

```python
LARGE_OVER_TRIM_MAX_OVERAGE = 900
TRIM_PROTECTED_EDGE_SENTENCE_COUNT = 2
```

- [ ] **Step 2: Broaden `_trim_over_target_candidate` safely**

Update `_trim_over_target_candidate`:

- allow overage up to `LARGE_OVER_TRIM_MAX_OVERAGE`;
- protect the first and last `TRIM_PROTECTED_EDGE_SENTENCE_COUNT` sentences;
- keep dialogue and protected terms high-ranked for retention;
- remove low-ranked sentences until `target_min <= count <= target_max`;
- if trimming would fall below `target_min`, keep the sentence and try another;
- return unchanged candidate if it cannot land in range.

- [ ] **Step 3: Improve over-target retry prompt**

When `prior_direction == "over_target"` and `prior_word_count` exists, include required cut size:

```text
上一次候选仍高于目标上限，约{prior_word_count}字，需要至少删减{prior_word_count - target_max}字。禁止原样返回候选稿；必须合并或删除低信息密度句子。
```

- [ ] **Step 4: Run GREEN large-overage test**

Run the large-overage test again.

Expected: pass.

## Task 3: Regression Verification

**Files:**

- Modify: `backend/app/core/chapter_compression.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Run compression regression suite**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_then_review_clears_over_target_warning tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_near_target_candidate_from_source tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_near_over_target_candidate tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_large_over_target_candidate -q
```

Expected: all pass.

## Task 4: Dogfood Chapter 10 and Chapter 11

**Files:**

- Create report under `docs/superpowers/notes/long-memory-agent/`.

- [ ] **Step 1: Compress Chapter 10**

Run:

```json
[
  {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 10}}
]
```

Expected:

- completed with 2000-2300 words, or blocked with stronger evidence;
- if completed, output includes revision id and deterministic/model attempt metadata.

- [ ] **Step 2: Review and analyze Chapter 10**

If compression completed, run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 10}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 10}}
]
```

Expected:

- no `chapter_over_target`;
- blocker count 0;
- if Athena creates proposals, resolve them before continuing.

- [ ] **Step 3: Generate Chapter 11 only if clear**

If Chapter 10 is within target, no blockers, and pending proposals are 0:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 11}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 11}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 11}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 11}}
]
```

Expected:

- Chapter 11 generated or blocked with recorded reason.
- Proposal pressure and review blockers are recorded and handled when safe.

## Task 5: Verification, Report, Commit, Push

**Files:**

- Modify all Phase24 files.

- [ ] **Step 1: Run T2 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [ ] **Step 2: Write Phase24 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase24-large-over-target-compression-and-chapter11.md` with:

- code changes;
- RED/GREEN evidence;
- Chapter 10 compression result;
- Chapter 10 review/analyze result;
- Chapter 11 generation result or blocker;
- verification commands;
- remote push status;
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
- only intended Phase24 files are changed.

- [ ] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase24-large-over-target-compression-and-chapter11.md
git commit -m "docs: plan long memory agent phase 24"
```

Commit implementation/report after verification:

```powershell
git add backend/app/core/chapter_compression.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase24-large-over-target-compression-and-chapter11.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase24-large-over-target-compression-and-chapter11.md
git commit -m "feat: trim large over-target chapters"
git push origin main
```
