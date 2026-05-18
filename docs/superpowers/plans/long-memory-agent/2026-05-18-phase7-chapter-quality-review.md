# Phase 7 Chapter Quality Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight Agent chapter-quality review tool so the system can record and block obvious manuscript quality risks before generating Chapter 4.

**Architecture:** Phase 7 adds deterministic review signals first. The review tool returns structured findings in Agent step output and reuses existing outline, chapter, longform maintenance, and world proposal queue data without creating a new persistence schema.

**Tech Stack:** FastAPI service layer, SQLAlchemy, existing Writing Agent run service, existing outline JSON storage, pytest, runtime dogfood through Agent API.

---

## Phase Metadata

- **Phase:** 7
- **Date:** 2026-05-18
- **Verification Tier:** T1 for review tool tests; T2 for runtime dogfood review on Chapters 2 and 3.
- **Primary Output:** Agent tool `review_chapter_quality`.
- **Dogfood Output:** Review `《雾港回声》` Chapters 2 and 3, record findings, and keep Chapter 4 blocked until review/revision decisions are explicit.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`.

## Phase 7 Success Criteria

- Agent supports `review_chapter_quality`.
- Review output includes `status`, `chapter_index`, `finding_count`, `blocker_count`, `findings`, and `recommended_actions`.
- The tool flags a generic fallback chapter title such as `第2章`.
- The tool flags over-target word count.
- The tool flags future-outline overlap when a chapter appears to consume later chapter material.
- The tool reports pending world-model proposal pressure.
- Runtime dogfood reviews Chapters 2 and 3 and records why Chapter 4 should remain blocked.

## Explicit Non-Goals

- Do not auto-rewrite Chapters 2 or 3 in this phase.
- Do not add a new database table for review findings yet.
- Do not auto-approve world-model proposals.
- Do not build frontend review UI.
- Do not call a model for semantic review in this phase; use deterministic checks so behavior is testable.

## Files

- Create: `backend/app/core/chapter_quality_review.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md`

## Task 1: Add Deterministic Review Core

**Files:**
- Create: `backend/app/core/chapter_quality_review.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing generic-title/length review test**

Add:

```python
def test_agent_review_chapter_quality_flags_generic_title_and_length(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第2章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert {finding["code"] for finding in output["findings"]} >= {"generic_chapter_title", "chapter_over_target"}
    assert "revise_chapter" in output["recommended_actions"]
```

- [x] **Step 2: Implement `review_chapter_quality`**

Create:

```python
def review_chapter_quality(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    ...
```

Initial deterministic findings:

- `missing_chapter`: blocker.
- `missing_outline_chapter`: blocker.
- `generic_chapter_title`: warning, blocker for dogfood continuation.
- `chapter_over_target`: blocker when above target max.
- `chapter_under_target`: warning when below target min.
- `pending_world_model_proposals`: warning when proposal queue has pending items.

Output contract:

```json
{
  "status": "ready|warning|blocked",
  "chapter_index": 2,
  "finding_count": 2,
  "blocker_count": 1,
  "findings": [],
  "recommended_actions": []
}
```

- [x] **Step 3: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_generic_title_and_length -q
```

Expected: pass.

## Task 2: Add Future Outline Overlap Check

**Files:**
- Modify: `backend/app/core/chapter_quality_review.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing future-overlap test**

Add:

```python
def test_agent_review_chapter_quality_flags_future_outline_overlap(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=3).one()
    chapter.title = "雾中童谣"
    chapter.content = "顾衍出现在地下实验室，警告他们不要靠近黑市雾晶。"
    chapter.word_count = 2000
    outline = db_session.query(Outline).filter_by(project_id=project.id).one()
    outline.chapters[3]["title"] = "顾衍的警告"
    outline.chapters[3]["summary"] = "顾衍现身并警告主角不要继续调查。"
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第3章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert output["status"] == "blocked"
    assert any(finding["code"] == "future_outline_overlap" for finding in output["findings"])
```

- [x] **Step 2: Implement overlap extraction**

Rule:

- Look at the next 5 outline chapters after the current chapter.
- Extract title tokens and short summary tokens with length >= 2.
- If current chapter content contains a future chapter title token or multiple future summary tokens, emit `future_outline_overlap`.

Keep this conservative and transparent; false positives are acceptable as warnings/blockers for review, not as automatic rewrites.

- [x] **Step 3: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_future_outline_overlap -q
```

Expected: pass.

## Task 3: Wire Agent Tool

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add tool to Agent**

Add `review_chapter_quality` to:

- `ALLOWED_TOOLS`.
- `INTERNAL_TOOLS`.
- `_execute_tool`.
- `_target_type_for_tool`.

Tool params:

```json
{"chapter_index": 3}
```

- [x] **Step 2: Decide run behavior**

The review tool should complete its step even when output status is `blocked`; it is a review report, not a failed tool.

Do not use run-level `blocked` for this tool in Phase 7. Downstream generation remains blocked by explicit preflight/length gates and by operator policy.

- [x] **Step 3: Run Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: pass.

## Task 4: Runtime Dogfood Reviews

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no secrets.

- [x] **Step 2: Review Chapter 2**

Use Agent run:

```json
{
  "goal": "审稿《雾港回声》第2章，记录质量风险。",
  "tools": [
    {"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}
  ]
}
```

Expected:

- generic title finding.
- over-target finding.
- pending proposal warning if queue remains pending.

- [x] **Step 3: Review Chapter 3**

Use Agent run:

```json
{
  "goal": "审稿《雾港回声》第3章，检查是否消耗后续章节内容。",
  "tools": [
    {"tool_name": "review_chapter_quality", "params": {"chapter_index": 3}}
  ]
}
```

Expected:

- over-target finding.
- future-outline overlap finding if Chapter 3 contains Chapter 4-8 material.
- pending proposal warning if queue remains pending.

- [x] **Step 4: Write Phase 7 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md` with:

```markdown
# Phase 7 Chapter Quality Review

## Runtime
## Implementation
## Chapter 2 Review
## Chapter 3 Review
## Issues Found
## Issues Fixed
## Verification
## Next Phase Recommendation
```

## Task 5: Commit Phase 7

- [x] **Step 1: Commit code**

```powershell
git add backend/app/core/chapter_quality_review.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py
git commit -m "feat: add chapter quality review tool"
```

- [x] **Step 2: Commit docs**

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md docs/superpowers/notes/long-memory-agent/2026-05-18-phase7-chapter-quality-review.md
git commit -m "docs: record long memory agent phase 7"
```

## Self-Review

- Spec coverage: This phase turns dogfood quality findings into Agent-visible review output before continuing longform generation.
- Placeholder scan: No `TBD` markers.
- Scope check: This plan avoids automatic rewriting and persistent review schema until the review signal proves useful.
