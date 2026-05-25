# Phase29 Review Baseline and Chapter 15 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unblock and generate Dogfood Chapter 15 while adding a small, test-backed quality-review baseline for obvious issues exposed by Chapter 14.

**Architecture:** Keep Phase29 narrow: the Writing Agent remains the orchestrator, `review_chapter_quality` gains deterministic checks for duplicate titles and known typo patterns, and the real dogfood loop expands Chapter 15 outline before generation. Code changes must be TDD-backed; content generation and maintenance fixes are recorded in the phase report.

**Tech Stack:** FastAPI backend, SQLAlchemy SQLite dogfood data, Writing Agent run service, Athena world model, longform memory/retrieval, pytest.

---

## Context

Phase28 ended with Chapter 14 complete:

```text
project_id: 25fa2b20-5b9f-473b-918b-f4ea491cbb60
chapter_14_title: 门后回声
chapter_14_word_count: 2298
longform_maintenance: current
pending_actionable_proposals: 0
```

Chapter 15 preflight is blocked only because Chapter 15 has no outline:

```text
preflight_chapter_15: blocked
issue: missing_outline_chapter
previous_chapter_state_card: ready, title 门后回声
```

Phase28 subagent also exposed two review gaps that are cheap to make deterministic now:

- obvious typo pattern: `戴着眼睛` should be caught before manual review;
- duplicate non-generic chapter titles should be surfaced before they confuse chapter lists.

Outline drift remains important, but broad semantic outline-vs-content evaluation is not in this phase unless Chapter 15 dogfood exposes another concrete repeatable failure. Avoid adding a brittle heuristic that blocks good hook-following chapters.

## Scope

In scope:

- Add deterministic quality-review warnings for duplicate chapter titles.
- Add deterministic quality-review blocker/warning for known typo patterns, starting with `戴着眼睛`.
- Expand or repair Chapter 15 outline from actual Chapter 14 state.
- Generate Chapter 15 and run quality, continuity, world-model analysis.
- Resolve classification-safe world-model proposal maintenance.
- Dispatch a read-only subagent for Chapter 15 reader/continuity review.
- Record findings and verification in a Phase29 report.

Out of scope:

- Full semantic outline-drift checker.
- Knowledge-base module implementation.
- Task queue redesign.
- Frontend work.
- Full T3 verification unless a high-risk code path changes.

## Files

- Modify: `backend/app/core/chapter_quality_review.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase29-review-baseline-and-chapter15.md`
- Update: this plan file as steps complete.

## Task 1: Quality Review Baseline

- [x] **Step 1: Write failing tests**

Add two tests near the existing `review_chapter_quality` tests in `backend/tests/test_writing_agent_runs.py`:

```python
def test_agent_review_chapter_quality_warns_on_duplicate_specific_title(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.title = "废弃实验室"
    second.title = "废弃实验室"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第2章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "duplicate_chapter_title")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert finding["evidence"]["matched_chapter_indexes"] == [1]
```

```python
def test_agent_review_chapter_quality_flags_known_typo_pattern(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "门后回声"
    chapter.content = "林深看见一个四十多岁的女人，戴着眼睛，头发扎成发髻。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "known_typo_pattern")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert finding["evidence"]["matched_text"] == "戴着眼睛"
    assert finding["evidence"]["suggestion"] == "戴着眼镜"
```

- [x] **Step 2: Run tests to verify RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_duplicate_specific_title tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_known_typo_pattern -q
```

Expected: both tests fail because the finding codes do not exist yet.

- [x] **Step 3: Implement minimal checks**

In `backend/app/core/chapter_quality_review.py`:

- add `KNOWN_TYPO_PATTERNS = {"戴着眼睛": "戴着眼镜"}`;
- add `_duplicate_title_findings(db, project_id, chapter)` that ignores empty/generic titles and returns a warning with previous matching chapter indexes;
- add `_known_typo_findings(content)` that returns warnings for configured typo patterns;
- call both from `review_chapter_quality()` after title/content are available.

- [x] **Step 4: Run GREEN checks**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_duplicate_specific_title tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_known_typo_pattern -q
```

Expected: both tests pass.

## Task 2: Chapter 15 Outline and Generation

- [x] **Step 1: Expand Chapter 15 outline**

Use the Writing Agent `expand_outline_window` tool for Chapter 15 in project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

Required guidance:

```text
第15章必须承接第14章《门后回声》的结尾：林深、苏晚晴、顾衍进入门后的向下楼梯。不要回到旧版巡逻队潜入线。继续处理N-07作为实验代号/实验体编号的悬念，不得把N-07写成顾衍军牌；顾衍军牌事实为N-017。章节目标仍为2000-2300字正文。
```

- [x] **Step 2: Preflight Chapter 15**

Run `preflight_writing` for Chapter 15.

Expected:

- outline chapter ready;
- previous chapter state card ready;
- longform maintenance ready;
- world model ready;
- retrieval ready;
- no pending world-model proposal blocker.

- [x] **Step 3: Generate and review Chapter 15**

Run this Writing Agent chain:

```json
[
  {"tool_name": "generate_chapter", "params": {"chapter_index": 15}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 15}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 15, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 15}}
]
```

Expected:

- Chapter 15 is正文, not outline;
- word count is at least 2000;
- quality review has no blockers;
- continuity review has no stable truth conflicts;
- world-model proposal queue is handled before next chapter.

- [x] **Step 4: Resolve immediate blockers**

If the chapter is under target, use `expand_chapter_to_target`.

If over target, resolve pending proposals first, then use `compress_chapter_to_target`.

If world-model proposals remain, use `draft_world_model_proposal_resolution_decisions` and `apply_world_model_proposal_resolution` only for classification-safe decisions.

## Task 3: Independent Chapter 15 Review

- [x] **Step 1: Dispatch read-only subagent**

Ask a subagent to inspect Chapter 15 in `data/mozhou.db` and report:

- whether the chapter continues the Chapter 14 door/stair hook;
- whether `N-07` / `N-017` remain distinct;
- whether `林建国` remains the father anchor;
- whether the chapter is readable web-novel正文 over 2000 words;
- whether any system-level issue should be fixed or recorded.

- [x] **Step 2: Fix or document findings**

Fix clear blockers in content or code. Record non-blocking quality issues in the report.

## Task 4: Verification, Report, Commit

- [x] **Step 1: Verification**

Because Task 1 changes one backend review module and Task 2 runs dogfood generation, use T1/T2:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_chapter_quality or compress_chapter_to_target"
```

If generation touches compression/expansion maintenance again, also run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py -q
```

Always run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 2: Write Phase29 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase29-review-baseline-and-chapter15.md` with:

- code changes and TDD evidence;
- Chapter 15 outline/preflight/generation run IDs;
- final Chapter 15 title and word count;
- quality/continuity/world-model review results;
- subagent review findings;
- pending issues and Phase30 recommendation.

- [ ] **Step 3: Commit and push**

Commit implementation and report, then push `main`.
