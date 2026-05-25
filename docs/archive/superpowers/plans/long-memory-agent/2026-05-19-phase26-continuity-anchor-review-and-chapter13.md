# Continuity Anchor Review and Chapter 13 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic continuity-anchor review tool for high-salience dates and identifiers, then use it before continuing the dogfood novel to Chapter 13.

**Architecture:** The new review should live beside existing chapter quality review code, but remain a separate Writing Agent tool so continuity evidence is explicit and can later become its own Agent capability. It should compare the target chapter against previous generated chapters and emit structured findings for hard conflicts such as different dates for the same named event or treating the same identifier as two different kinds of facts.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent run service, pytest.

---

## Context

Phase25 generated and repaired Chapter 12. A subagent quality review caught hard continuity issues that the current automated review missed:

- `2045年7月12日`, `2045年8月12日`, and `2045年11月7日` were all tied to "雾灾发生前三天".
- `N-017` was already established as Gu Yan's military tag number, while Chapter 12 temporarily treated `N-07` as the same kind of identifier.

This phase turns that failure into a small but durable Agent capability.

## Scope

In scope:

- Add a backend continuity anchor review function.
- Add a Writing Agent tool named `review_chapter_continuity`.
- Detect conflicting dates for the same explicit event phrase.
- Detect conflicting military-tag identifier claims when another code is later presented as the same tag number.
- Allow a chapter to distinguish a military tag number from an experiment code.
- Run the tool on the current dogfood project before Chapter 13.
- Generate Chapter 13 only after continuity review, preflight, quality review, and world-model queue are clean.

Out of scope:

- Full timeline graph rebuilding.
- General natural-language contradiction detection.
- UI changes for displaying anchor graphs.
- Compressing old over-target Chapters 1-3 and 5.

## Files

- Create: `backend/app/core/chapter_continuity_review.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Add report: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase26-continuity-anchor-review-and-chapter13.md`

## Task 1: Date Anchor Review

- [ ] **Step 1: Write failing date-conflict test**

Add a test in `backend/tests/test_writing_agent_runs.py`:

```python
def test_agent_review_chapter_continuity_flags_event_date_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "信封上的邮戳日期是2045年8月9日——雾灾发生前三天。"
    first.word_count = 2000
    second.content = "林深看了看信封上的邮戳——2045年7月12日。那是雾灾发生的前三天。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章连续性锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["code"] == "timeline_anchor_conflict"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["event_key"] == "fog_disaster_minus_3_days"
    assert finding["evidence"]["values"] == ["2045年8月9日", "2045年7月12日"]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_event_date_conflict -q
```

Expected: FAIL because `review_chapter_continuity` is not yet an allowed Writing Agent tool.

- [ ] **Step 3: Implement minimal date anchor extraction**

Create `backend/app/core/chapter_continuity_review.py` with:

- `review_chapter_continuity(db, project_id, chapter_index, lookback=20)`.
- Regex extraction for `YYYY年M月D日`.
- Sentence splitting on Chinese and ASCII sentence punctuation.
- Event-key inference for sentences containing `雾灾发生前三天` or `雾灾前三天`.
- Structured findings when one event key maps to multiple date values.

- [ ] **Step 4: Register Writing Agent tool**

Modify `backend/app/services/writing_agent/run_service.py`:

- Add `review_chapter_continuity` to `ALLOWED_TOOLS`.
- Add it to `INTERNAL_TOOLS`.
- Add `review_chapter_continuity: "review"` in `_target_type_for_tool`.
- Dispatch to `app.core.chapter_continuity_review.review_chapter_continuity`.

- [ ] **Step 5: Run GREEN**

Run the same pytest command from Step 2.

Expected: PASS.

## Task 2: Identifier Anchor Review

- [ ] **Step 1: Write failing identifier-conflict test**

Add:

```python
def test_agent_review_chapter_continuity_flags_identifier_kind_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "顾衍把军牌扔在桌上，上面刻着编号：N-017。"
    first.word_count = 2000
    second.content = "顾衍掏出军牌，翻到背面。上面刻着一串编号——N-07。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert output["status"] == "blocked"
    assert finding["code"] == "identifier_anchor_conflict"
    assert finding["evidence"]["anchor_key"] == "顾衍:military_tag_number"
    assert finding["evidence"]["values"] == ["N-017", "N-07"]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_identifier_kind_conflict -q
```

Expected: FAIL until identifier anchors are implemented.

- [ ] **Step 3: Implement identifier anchors**

Extend `chapter_continuity_review.py`:

- Extract identifiers matching `[A-Z]-\d+`.
- Classify `military_tag_number` when the same sentence contains `军牌` and `编号` or `刻着`.
- Use `顾衍:military_tag_number` when the sentence contains `顾衍`.
- Treat sentences containing `不是军牌编号` or `实验代号` as non-conflicting experiment-code context.

- [ ] **Step 4: Run GREEN**

Run the pytest command from Step 2.

Expected: PASS.

## Task 3: False Positive Guard

- [ ] **Step 1: Add a passing distinction test**

Add:

```python
def test_agent_review_chapter_continuity_allows_experiment_code_distinction(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "顾衍把军牌扔在桌上，上面刻着编号：N-017。"
    first.word_count = 2000
    second.content = "顾衍掏出军牌，正面的编号仍是N-017；背面浮出暗纹——N-07。那不是军牌编号，更像实验代号。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["status"] == "ready"
    assert output["finding_count"] == 0
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_event_date_conflict tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_identifier_kind_conflict tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_allows_experiment_code_distinction -q
```

Expected: PASS.

## Task 4: Dogfood Chapter 13 Loop

- [ ] **Step 1: Run continuity review on current Chapter 12**

Use `/agent-runs` with:

```json
{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 12}}
```

Expected: ready, 0 blocker findings.

- [ ] **Step 2: Preflight Chapter 13**

Use `/agent-runs` with:

```json
{"tool_name": "preflight_writing", "params": {"chapter_index": 13}}
```

If the outline is missing, run `expand_outline_window` for Chapter 13 only.

- [ ] **Step 3: Generate and review Chapter 13**

Use `/agent-runs` with:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 13}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 13}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 13}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 13}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 13}}
]
```

- [ ] **Step 4: Resolve or document follow-up**

If Chapter 13 is outside 2000-2300 words, use existing expansion/compression tools.
If world-model proposals remain, draft and apply guarded decisions when they are classification-safe.
If continuity findings remain, repair before proceeding.

## Task 5: Verification and Report

- [ ] **Step 1: Run T2 backend tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: PASS.

- [ ] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
git status --short --branch
```

Expected: no whitespace errors, no secret matches, only intended files changed before commit.

- [ ] **Step 3: Write Phase26 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase26-continuity-anchor-review-and-chapter13.md` with:

- implementation summary;
- RED/GREEN evidence;
- dogfood Chapter 13 evidence;
- continuity review findings;
- world-model queue status;
- next phase recommendation.

- [ ] **Step 4: Commit and push**

Commit plan separately first, then implementation/report after verification.
