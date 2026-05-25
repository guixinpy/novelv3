# Phase33 Post-Revision Summary Refresh and Chapter 19 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix stale post-revision `event_summary` handling, then continue Dogfood through Chapter 19.

**Architecture:** Keep `event_summary` out of canonical world truth unless reviewed, but allow Athena to create a fresh pending event summary when chapter content changes after a prior terminal summary review. This gives the Writing Agent a reviewable post-revision memory summary instead of forcing longform memory to fall back to raw chapter preview.

**Tech Stack:** FastAPI backend, SQLAlchemy, Athena world proposal extraction, longform memory/retrieval, Writing Agent tools, pytest.

---

## Context

Phase32 ended with:

```text
latest_chapter: 18
latest_title: 黑市暗流
latest_word_count: 2082
pending_world_model_proposals: 0
longform_maintenance: current
latest_synced_chapter_index: 18
```

Phase32 exposed a specific memory weakness:

- Chapter 18 generated an initial `event_summary` proposal.
- The chapter then required compression and N-07 wording correction.
- The pre-revision `event_summary` was rejected to avoid stale memory.
- Running `analyze_chapter_world_model` after revision skipped the new summary as a duplicate because `_find_existing_candidate()` matched the old terminal item by `claim_id`.
- Chapter 18 memory therefore fell back to `source=chapter_content` instead of a reviewed summary.

User clarification during Phase33:

- `2000+` should be treated as an elastic writing target, not a hard instruction to hit exactly 2000 words.
- For the current longform target, `2000-3000` is the preferred default range.
- Length feedback should guide the model without suppressing narrative flow; moderate over-target drift should warn first, while only extreme drift should block.

## Scope

In scope:

- Add TDD coverage for post-revision `event_summary` refresh.
- Let Athena create a new pending `event_summary` candidate when the latest existing `event_summary` is terminal and the candidate payload has changed.
- Keep normal duplicate behavior for unchanged terminal summaries and for non-`event_summary` predicates.
- Continue Dogfood by generating Chapter 19 after the fix.
- Resolve Chapter 19 proposals and refresh longform memory/retrieval.

Out of scope:

- Database schema changes.
- General knowledge-base module implementation.
- Frontend changes.
- Retrofitting all old chapters.
- Automatically merging `event_summary` into truth facts.

## Files

- Modify: `backend/app/core/athena_longform.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase33-post-revision-summary-and-chapter19.md`
- Update: this plan file as steps complete.

## Task 1: TDD Post-Revision Event Summary Refresh

- [x] **Step 1: Add failing test**

Add a test near `test_refresh_longform_memory_prefers_reviewed_event_summary_proposal` in `backend/tests/test_writing_agent_runs.py`:

```python
def test_analyze_chapter_world_model_creates_new_event_summary_after_terminal_summary_goes_stale(db_session):
    from app.core.athena_longform import analyze_chapter_to_world_proposals
    from app.core.longform_memory import refresh_longform_memory_for_chapter
    from app.core.world_proposal_service import review_proposal_item

    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "蓝雾电梯"
    chapter.content = (
        "林深在旧站台发现蓝雾电梯启动。"
        "苏晚晴确认这不是普通出口。"
        + "墙上的灰蓝色雾晶回声像旧唱片一样反复刮擦。" * 8
    )
    chapter.word_count = 2400
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)
    analyze_chapter_to_world_proposals(db=db_session, project_id=project.id, chapter_index=1)
    old_item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .one()
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=old_item.id,
        reviewer_ref="test",
        action="mark_uncertain",
        reason="旧摘要先进入写作记忆候选",
        evidence_refs=["chapter:1"],
        commit=True,
    )

    chapter.content = (
        "林深在暗网密室找到回声稳定剂核心线索。"
        "顾衍确认完整配方被转移到第三研究所核心数据库。"
        + "蓝雾电梯的旧线索只剩下墙上的残影。" * 8
    )
    chapter.word_count = 2500
    db_session.commit()

    result = analyze_chapter_to_world_proposals(db=db_session, project_id=project.id, chapter_index=1)

    event_items = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .order_by(WorldProposalItem.created_at.asc())
        .all()
    )
    assert result["created"]["proposal_items"] >= 1
    assert len(event_items) == 2
    assert event_items[0].item_status == "uncertain"
    assert event_items[1].item_status == "pending"
    assert "第三研究所核心数据库" in event_items[1].object_ref_or_value["summary"]

    review_proposal_item(
        db=db_session,
        proposal_item_id=event_items[1].id,
        reviewer_ref="test",
        action="mark_uncertain",
        reason="修订后摘要作为写作记忆来源",
        evidence_refs=["chapter:1"],
        commit=True,
    )
    refresh_longform_memory_for_chapter(db_session, project.id, 1)

    memory = (
        db_session.query(LongformMemory)
        .filter_by(project_id=project.id, memory_type="chapter", scope_key="chapter:1")
        .one()
    )
    assert "第三研究所核心数据库" in memory.summary
    assert memory.memory_metadata["source"] == "reviewed_event_summary"
    assert memory.memory_metadata["event_summary_proposal_item_id"] == event_items[1].id
```

- [x] **Step 2: Run RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_analyze_chapter_world_model_creates_new_event_summary_after_terminal_summary_goes_stale -q
```

Expected: fail because only one terminal `event_summary` item exists and the revised summary is skipped as duplicate.

- [x] **Step 3: Implement minimal refresh behavior**

In `backend/app/core/athena_longform.py`:

- import `TERMINAL_ITEM_STATUSES`;
- when `_find_existing_candidate()` returns an existing item:
  - keep current behavior for actionable items;
  - for `event_summary` terminal items, compare `object_ref_or_value`, `notes`, and `evidence_refs`;
  - if changed, append the candidate to `new_candidates` instead of treating it as a duplicate;
  - if unchanged, count it as duplicate.

Suggested helper:

```python
def _should_create_refreshed_event_summary(existing: WorldProposalItem, candidate: Any) -> bool:
    if existing.predicate != "event_summary":
        return False
    if existing.item_status not in TERMINAL_ITEM_STATUSES:
        return False
    return (
        existing.object_ref_or_value != candidate.object_ref_or_value
        or existing.notes != candidate.notes
        or (existing.evidence_refs or []) != (candidate.evidence_refs or [])
    )
```

- [x] **Step 4: Run GREEN and focused regression**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_analyze_chapter_world_model_creates_new_event_summary_after_terminal_summary_goes_stale tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal -q
```

Expected: both pass.

## Task 2: Dogfood Chapter 18 Summary Refresh and Chapter 19

- [x] **Step 0: Align Chapter Length Semantics With Elastic `2000+`**

Updated the existing length tests and behavior so:

- 600-chapter / 1.2M-word projects render `2000-3000` as the default range.
- Agent repeated-length feedback uses advisory wording instead of hard `必须` wording.
- A 3846-word chapter against a 3000-word soft upper target is a warning, not a blocker.

Targeted verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py::test_chapter_payload_uses_2000_floor_for_600_chapter_longform tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_soft_over_target_without_blocking -q
```

Result: `4 passed in 0.43s`.

- [x] **Step 1: Refresh Chapter 18 event summary**

Run `analyze_chapter_world_model` for Chapter 18 after the code fix.

Expected:

- a new pending `event_summary` proposal can be created for the revised Chapter 18;
- no other stale duplicate behavior regresses.

- [x] **Step 2: Review the refreshed summary**

Use the existing proposal draft/apply workflow. For the refreshed Chapter 18 `event_summary`, use `mark_uncertain` if it is a useful writing-memory summary and not a world-truth merge.

Expected:

- pending queue returns to `0`;
- Chapter 18 longform memory source becomes `reviewed_event_summary`.

- [x] **Step 3: Expand, preflight, generate, and review Chapter 19**

Use Chapter 18 ending as guidance:

```text
第19章承接第18章《黑市暗流》结尾：林深、顾衍背着苏晚晴，赵猛带路，四人在暗网通道中逃离追捕。第18章获得的不是完整配方，而是“完整配方在第三研究所核心数据库，需要最高权限访问”的线索。继续保留N-07与苏晚晴的未确认关系；不要把N-07写成顾衍军牌，也不要把N-017混入本章。顾衍欠赵猛雾晶债，这个债务应带来后续风险。第19章目标为2000-3000字，推进逃亡、赵猛债务、核心数据库入口线索和新的阻碍，不要直接拿到完整配方。
```

Run:

```json
[
  {"tool_name": "expand_outline_window", "params": {"start_chapter": 19, "end_chapter": 19, "command_args": "<guidance>"}},
  {"tool_name": "preflight_writing", "params": {"chapter_index": 19}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 19}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 19}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 19, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 19}}
]
```

Stop and resolve proposals or revision issues if the Agent blocks or reviews return actionable findings.

Result:

- Initial Agent run `dd6dd4d0-73d2-4248-a650-85eecad5e3eb` generated Chapter 19 `暗网迷途`.
- Initial word count was `3846`; after the elastic-length clarification this is a warning-class length drift, not a hard failure.
- Dogfood review found a more important narrative problem: the chapter hard-confirmed `N-07` / 苏晚晴 and revealed third-research-institute backstory too early.
- Cleared 7 pre-revision world model proposals with event summary rejected as stale.
- Ran compression/revision twice, then applied a deterministic versioned correction for the remaining premature reveal.
- Final Chapter 19 word count is `2322`, quality review is `ready`, continuity review is `ready`, pending proposals are `0`.
- Longform maintenance is `current` through Chapter 19 after retrieval repair.

## Task 3: Review, Verification, and Report

- [x] **Step 1: Dispatch read-only subagent**

Ask the subagent to check:

- post-revision Chapter 18 memory source is `reviewed_event_summary`;
- Chapter 19 continues the Chapter 18 ending;
- N-07 / N-017 remain distinct;
- Chapter 19 is in `2000-3000` range;
- pending proposals are clear;
- longform maintenance is current through Chapter 19.

Dispatched read-only explorer `019e3ff6-2c06-7e70-a550-194f7c8a811a`; it did not return within the working window and was closed without findings. Main-thread verification evidence is recorded below.

- [x] **Step 2: Run targeted verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_analyze_chapter_world_model_creates_new_event_summary_after_terminal_summary_goes_stale tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal -q
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_chapter_quality or review_chapter_continuity or length_decision"
cd ..
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Results:

- Phase33 focused suite: `7 passed in 0.68s`.
- Review/length/event-summary focused suite: `15 passed, 94 deselected in 1.21s`.
- `git diff --check`: passed with only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- Secret scan: no matches.

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase33-post-revision-summary-and-chapter19.md`.

- [x] **Step 4: Commit and push**

Commit code/docs and push `main`.

Result:

- Commit `c5ebe32` pushed to `origin/main`.
