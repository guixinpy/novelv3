# Phase30 Event Summary Memory and Chapter 16 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn reviewed chapter `event_summary` proposals into a usable longform-memory summary lane, then generate and validate Dogfood Chapter 16.

**Architecture:** Keep world truth and writing memory separate. `event_summary` proposals reviewed as `uncertain` stay out of `WorldFactClaim`, but `refresh_longform_memory_for_chapter()` may use their summary text as the chapter memory summary because this is a writing-memory aid, not a world-truth merge. Then continue the real chapter-generation loop from Chapter 16.

**Post-phase user supplement:** Future phases should revise chapter length policy so `2000+` is treated as an elastic target, roughly `2000-3000`, with 2000 as the hard lower bound and the upper bound as a soft quality/pace guard. Avoid hard-compressing chapters solely because they exceed a narrow 2300-word cap.

**Tech Stack:** FastAPI backend, SQLAlchemy SQLite dogfood data, Writing Agent run service, Athena world proposals, longform memory/retrieval, pytest.

---

## Context

Phase29 ended with:

```text
chapter_15_title: 向下螺旋
chapter_15_word_count: 2293
longform_maintenance: current
latest_synced_chapter_index: 15
pending_actionable_proposals: 0
outline16_exists: false
```

Recurring workflow friction:

```text
event_summary -> draft decision mark_uncertain
```

This is correct for world truth, but inefficient for longform memory. The summary should not become a confirmed world fact automatically, yet it can still improve chapter memory and retrieval after the proposal has been reviewed into a non-actionable state.

## Scope

In scope:

- Make `refresh_longform_memory_for_chapter()` prefer reviewed `event_summary` proposal summaries for that chapter.
- Only use non-actionable reviewed statuses (`uncertain`, `approved`, `approved_with_edits`) and ignore pending/rejected items.
- Preserve current fallback to content preview when no reviewed event summary exists.
- Sync retrieval through existing longform-memory sync paths.
- Expand Chapter 16 outline from the actual Chapter 15 state.
- Generate Chapter 16, review quality/continuity, resolve proposal maintenance, and run subagent review.

Out of scope:

- Changing Writing Agent guarded apply to approve `event_summary`.
- Creating new database tables or migrations.
- General knowledge-base module implementation.
- Frontend work.
- Full semantic outline-drift detection.

## Files

- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase30-event-summary-memory-and-chapter16.md`
- Update: this plan file as steps complete.

## Task 1: Event Summary Memory Lane

- [x] **Step 1: Write failing test**

Add this test near the compression/longform-memory tests in `backend/tests/test_writing_agent_runs.py`:

```python
def test_refresh_longform_memory_prefers_reviewed_event_summary_proposal(db_session):
    from app.core.athena_longform import analyze_chapter_to_world_proposals
    from app.core.longform_memory import refresh_longform_memory_for_chapter
    from app.core.world_proposal_service import review_proposal_item

    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "蓝雾电梯"
    chapter.content = (
        "林深沿着潮湿管道走了很久，墙上的灰蓝色雾晶回声像旧唱片一样反复刮擦。"
        "他在第二道门后发现蓝雾电梯启动，苏晚晴确认这不是普通出口。"
        "随后他们又穿过一段漫长的空走廊，脚步声被黑暗吞没，墙面只剩无意义的噪点。"
        * 8
    )
    chapter.word_count = 2600
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)
    analyze_chapter_to_world_proposals(db=db_session, project_id=project.id, chapter_index=1)
    event_item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .one()
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=event_item.id,
        reviewer_ref="test",
        action="mark_uncertain",
        reason="章节摘要只进入写作记忆，不进入真相层",
        evidence_refs=["chapter:1"],
        commit=True,
    )

    refresh_longform_memory_for_chapter(db_session, project.id, 1)

    memory = (
        db_session.query(LongformMemory)
        .filter_by(project_id=project.id, memory_type="chapter", scope_key="chapter:1")
        .one()
    )
    assert "蓝雾电梯启动" in memory.summary
    assert memory.memory_metadata["source"] == "reviewed_event_summary"
    assert memory.memory_metadata["event_summary_proposal_item_id"] == event_item.id
```

- [x] **Step 2: Run RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal -q
```

Expected: FAIL because `LongformMemory.summary` still uses the chapter content preview and lacks `reviewed_event_summary` metadata.

- [x] **Step 3: Implement minimal longform-memory lookup**

In `backend/app/core/longform_memory.py`:

- import `WorldProposalItem`;
- add `REVIEWED_EVENT_SUMMARY_STATUSES = {"uncertain", "approved", "approved_with_edits"}`;
- build an event-summary lookup in `rebuild_longform_memory()` and `refresh_longform_memory_for_chapter()`;
- update `_chapter_memory()` to accept an optional reviewed summary record;
- when present, use `object_ref_or_value["summary"]` as `LongformMemory.summary`;
- set metadata `source`, `event_summary_proposal_item_id`, and `event_summary_item_status`.

- [x] **Step 4: Run GREEN and focused regression**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_refreshes_longform_memory_and_retrieval -q
```

Expected: both tests pass.

## Task 2: Apply Memory Lane to Dogfood and Generate Chapter 16

- [x] **Step 1: Refresh dogfood memory for Chapters 14-15**

Run `refresh_longform_memory_for_chapter()` for Chapters 14 and 15, then `sync_longform_memory_retrieval_documents()` for updated memory IDs.

Expected:

- `longform_maintenance.status == current`;
- Chapter 14 and 15 memory metadata can use reviewed event summaries if present.

- [x] **Step 2: Expand Chapter 16 outline**

Use `expand_outline_window` for Chapter 16 with guidance:

```text
第16章必须承接第15章《向下螺旋》的结尾：三人逃出第三研究所后，手电里传出“N-07同步完成”。继续处理N-07同步后果，保持N-07为实验代号/实验体编号，不得写成顾衍军牌；顾衍军牌事实仍为N-017。不要跳过逃出后的即时余波与角色反应。
```

- [x] **Step 3: Preflight Chapter 16**

Run `preflight_writing` for Chapter 16.

Expected: ready.

- [x] **Step 4: Generate and review Chapter 16**

Run:

```json
[
  {"tool_name": "generate_chapter", "params": {"chapter_index": 16}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 16}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 16, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 16}}
]
```

Resolve pending proposals and length drift with the existing workflow.

## Task 3: Independent Review and Report

- [x] **Step 1: Dispatch read-only subagent**

Ask a subagent to inspect Chapter 16 and report:

- whether it continues the `N-07同步完成` hook;
- whether N-07 and N-017 remain distinct;
- whether chapter memory/retrieval reflects reviewed event-summary summaries;
- whether quality/continuity issues remain.

- [x] **Step 2: Fix or document findings**

Fix clear blockers and record non-blocking items.

- [x] **Step 3: Verification**

Because this touches longform memory and chapter generation, run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_memory or compress_chapter_to_target or review_chapter_quality"
```

Also run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 4: Report, commit, push**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase30-event-summary-memory-and-chapter16.md`, update this plan, commit, and push `main`.
