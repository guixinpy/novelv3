# Phase31 Elastic Length Policy and Chapter 17 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change longform chapter length handling from a narrow hard cap to an elastic `2000+` policy, then continue Dogfood through Chapter 17.

**Architecture:** Keep one source of truth in `project_chapter_word_range()`. For longform projects whose per-chapter average is at least 2000, treat the average as a hard lower bound and use a softer upper bound around 1.5x average, so the current Dogfood target becomes `2000-3000` instead of `2000-2300`. Small synthetic projects keep the existing 0.85x / 1.15x behavior so existing short-unit tests remain meaningful.

**Tech Stack:** FastAPI backend, SQLAlchemy, Writing Agent run service, chapter quality review, longform memory diagnostics, pytest.

---

## Context

The user clarified that `2000+` should be a flexible quality target, not a narrow hard range. For online novel writing, forcing every chapter down toward 2000 words can hurt model output quality, scene density, and natural pacing. The current backend computes a 2300 upper bound for the Dogfood project because `project_chapter_word_range()` returns `average * 1.15`.

Phase30 already recorded this requirement in:

- `docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- `docs/superpowers/notes/long-memory-agent/2026-05-19-phase30-event-summary-memory-and-chapter16.md`

## Scope

In scope:

- Make longform `2000+` projects use a softer default upper bound, currently `round(average * 1.5)`.
- Keep the lower bound at the per-chapter average when average is at least 2000.
- Keep small synthetic projects on the old 0.85x / 1.15x behavior.
- Update quality review, preflight length policy, diagnostics, and generation diagnostics through the shared helper.
- Continue Dogfood by expanding and preflighting Chapter 17, then generating/reviewing it if preflight is ready.

Out of scope:

- Frontend controls for configuring the elastic upper multiplier.
- Per-project custom length presets.
- Changing existing compression mechanics except through the shared target range.
- Full frontend build unless backend behavior changes reveal an API contract break.

## Files

- Modify: `backend/app/prompting/providers/chapter.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Modify: `backend/tests/test_longform_scale.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase31-elastic-length-policy-and-chapter17.md`
- Update: this plan file as steps complete.

## Task 1: Elastic Longform Length Range

- [x] **Step 1: Write failing tests**

Update or add tests:

1. In `backend/tests/test_longform_scale.py`, change `test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects` so the 1,200,000 / 600 project expects:

```python
assert payload["word_target"]["target_average_word_count"] == 2000
assert payload["word_target"]["target_min_word_count"] == 2000
assert payload["word_target"]["target_max_word_count"] == 3000
assert payload["word_target"]["under_target_chapter_indexes"] == [1]
assert payload["word_target"]["over_target_chapter_indexes"] == []
```

2. In `backend/tests/test_writing_agent_runs.py`, change the modest over-target review test so a `2482` word chapter under a 2000+ project produces no `chapter_over_target` finding:

```python
def test_agent_review_chapter_quality_accepts_elastic_2000_plus_length(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "雾中回声"
    chapter.word_count = 2482
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    codes = {finding["code"] for finding in output["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_over_target" not in codes
```

3. Update repeated-over-target tests to use `3300` or higher as the repeated over value, since `3000` becomes inside the elastic range.

- [x] **Step 2: Run RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_accepts_elastic_2000_plus_length -q
```

Expected: fail because current target max remains `2300` and `2482` is still flagged as over-target.

- [x] **Step 3: Implement minimal shared policy**

In `backend/app/prompting/providers/chapter.py`, update `project_chapter_word_range()`:

```python
def project_chapter_word_range(project: Project) -> tuple[int, int] | None:
    target_words = int(project.target_word_count or 0)
    target_chapters = int(project.target_chapter_count or 0)
    if target_words <= 0 or target_chapters <= 0:
        return None
    average = max(1, round(target_words / target_chapters))
    if average >= 2000:
        return average, max(average, round(average * 1.5))
    target_min = round(average * 0.85)
    return max(1, target_min), max(1, round(average * 1.15))
```

- [x] **Step 4: Run GREEN and focused regression**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects tests\test_writing_agent_runs.py -q -k "length_decision or length_policy or review_chapter_quality"
```

Expected: all selected tests pass.

## Task 2: Dogfood Chapter 17

- [x] **Step 1: Expand Chapter 17 outline**

Use `expand_outline_window` for Chapter 17 with guidance:

```text
第17章承接第16章《同步后遗症》结尾：林深、顾衍带着昏迷的苏晚晴前往废弃医院。保持N-07与N-017区分：N-07是林深相关同步/实验编号，N-017仍是顾衍军牌和旧定位绑定。写作目标为2000+，允许自然上浮到约3000字，不要为了贴近2000而牺牲场景完整度。
```

- [x] **Step 2: Preflight Chapter 17**

Run `preflight_writing` for Chapter 17.

Expected: ready, unless outline expansion fails or world-model queue is non-empty.

- [x] **Step 3: Generate and review Chapter 17**

Run:

```json
[
  {"tool_name": "generate_chapter", "params": {"chapter_index": 17}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 17}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 17, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 17}}
]
```

Resolve pending proposals with the existing draft/apply workflow. Only compress if the chapter is below 2000 or clearly above the elastic soft upper bound.

## Task 3: Independent Review and Report

- [x] **Step 1: Dispatch read-only subagent**

Ask a subagent to review:

- whether the elastic policy is reflected in diagnostics and reviews;
- whether Chapter 17 continues Chapter 16;
- whether N-07 and N-017 remain distinct;
- whether pending world-model proposals are cleared;
- whether longform memory and retrieval are current.

- [x] **Step 2: Verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects tests\test_writing_agent_runs.py -q -k "length_decision or length_policy or review_chapter_quality"
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 3: Report, commit, push**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase31-elastic-length-policy-and-chapter17.md`, update this plan, commit, and push `main`.
