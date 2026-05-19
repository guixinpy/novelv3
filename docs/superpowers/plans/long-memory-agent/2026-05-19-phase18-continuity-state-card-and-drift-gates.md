# Phase 18 Continuity State Card and Drift Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic continuity context and review gates so the Writing Agent can avoid or catch the Chapter 6 class of longform drift before continuing to Chapter 7.

**Architecture:** Keep the existing Writing Agent orchestration and chapter generator intact. Add small deterministic helpers in preflight/generation and chapter quality review: a previous-chapter state card for generation context, plus review findings for character identity drift, ability-boundary drift, and too-convenient key-item acquisition.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `WritingAgentRunService`, `chapter_quality_review`, pytest.

---

## Phase Metadata

- **Phase:** 18
- **Date:** 2026-05-19
- **Verification Tier:** T1 for deterministic helper behavior and review findings; T2 for dogfood review/preflight on `《雾港回声》`.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Continuity gate evidence for Chapter 6 and a safe decision on whether Chapter 7 can proceed.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Starting State

- Generated chapters: 6
- Latest chapter: Chapter 6 `黑市雾晶`
- Chapter 6 stored word count: 2153
- Pending world-model proposals: 0
- World fact claims: 0
- Known Chapter 6 quality risks:
  - `叶知秋` identity/gender drift.
  - `苏晚晴` ability boundary drift.
  - Existing fog crystal versus purchased memory fog crystal is unclear.
  - Key fog crystal acquisition is too convenient.
  - Outline may contain ability drift before generation.

## Problem

Phase17 proved the Agent can self-correct chapter length, but Chapter 6 exposed higher-value longform risks:

- The generator does not receive a compact "上一章末状态卡".
- Review does not flag explicit character profile drift.
- Review does not flag ability-boundary drift against setup/world rules.
- Review does not flag rare key items being obtained with no cost, condition, debt, or risk.

These are core blockers for million-word continuity. They should be deterministic gates before more autonomous longform generation.

## Success Criteria

- `preflight_writing` returns a `previous_chapter_state_card` check for chapter indexes greater than 1.
- Writing Agent `generate_chapter` appends a compact continuity state card to `command_args` when a previous chapter exists.
- Existing user `command_args` and Phase17 length feedback are preserved.
- `review_chapter_quality` flags explicit profile drift where a setup character is introduced with an identity marker that contradicts their setup background.
- `review_chapter_quality` flags ability-boundary drift when chapter content uses forbidden capability phrases contradicted by setup rules.
- `review_chapter_quality` flags too-convenient acquisition of rare/key story items when no cost/risk terms appear nearby.
- Dogfood review of Chapter 6 records whether these new gates catch the known risks.
- Chapter 7 is generated only if preflight and quality gates do not show unresolved blockers. If blocked, record the blocker and do not force generation.

## Explicit Non-Goals

- Do not change database schema.
- Do not add frontend UI.
- Do not introduce LLM-based semantic review in this phase.
- Do not rewrite Chapter 6 in this phase unless an existing tool already makes it safe and cheap.
- Do not perform full frontend/browser verification.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/core/chapter_quality_review.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md`

## Task 1: Add Previous Chapter State Card to Agent Context

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing preflight state-card test**

Add this test near existing preflight tests in `backend/tests/test_writing_agent_runs.py`:

```python
def test_agent_preflight_reports_previous_chapter_state_card(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "空白信的秘密"
    chapter.content = "林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。"
    chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    card = output["checks"]["previous_chapter_state_card"]
    assert response.status_code == 200
    assert card["status"] == "ready"
    assert card["chapter_index"] == 1
    assert card["title"] == "空白信的秘密"
    assert "雾晶是钥匙" in card["last_excerpt"]
    assert "空白信" in card["key_terms"]
    assert "下城" in card["key_terms"]
```

- [x] **Step 2: Run RED preflight test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_reports_previous_chapter_state_card -q
```

Expected: fail because `previous_chapter_state_card` is not present.

- [x] **Step 3: Implement minimal state-card helper**

In `backend/app/services/writing_agent/run_service.py`, add a helper:

```python
CONTINUITY_KEY_TERMS = ("空白信", "雾晶", "记忆雾晶", "钥匙", "下城", "黑市", "灯塔", "实验体", "叶知秋", "苏晚晴", "林深")


def _previous_chapter_state_card(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    if chapter_index <= 1:
        return {"status": "not_required"}
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index - 1)
        .first()
    )
    if chapter is None:
        return {"status": "missing", "chapter_index": chapter_index - 1}
    content = str(chapter.content or "").strip()
    excerpt = content[-220:] if len(content) > 220 else content
    key_terms = [term for term in CONTINUITY_KEY_TERMS if term in content]
    return {
        "status": "ready",
        "chapter_index": chapter.chapter_index,
        "title": chapter.title,
        "last_excerpt": excerpt,
        "key_terms": key_terms,
    }
```

In `_preflight_writing`, set:

```python
checks["previous_chapter_state_card"] = _previous_chapter_state_card(self.db, project_id, chapter_index)
```

- [x] **Step 4: Run GREEN preflight test**

Run the same test and confirm it passes.

- [x] **Step 5: Write failing generation context test**

Add this test near the Phase17 length feedback tests:

```python
def test_agent_generate_chapter_appends_previous_state_card(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "空白信的秘密"
    chapter.content = "林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。"
    chapter.word_count = 2000
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第2章",
            "tools": [
                {
                    "tool_name": "generate_chapter",
                    "command_args": "保持紧张感",
                    "params": {"chapter_index": 2},
                }
            ],
        },
    )

    command_args = str(captured["command_args"])
    assert response.status_code == 200
    assert "保持紧张感" in command_args
    assert "上一章状态卡" in command_args
    assert "空白信的秘密" in command_args
    assert "雾晶是钥匙" in command_args
    assert "下城" in command_args
```

- [x] **Step 6: Run RED generation context test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_previous_state_card -q
```

Expected: fail because generation command args do not include the state card.

- [x] **Step 7: Append state card to effective chapter command args**

In `run_service.py`, change the chapter tool path to combine user args, continuity feedback, and length feedback. Add:

```python
def _chapter_continuity_feedback(db: Session, project_id: str, chapter_index: int) -> dict[str, Any] | None:
    card = _previous_chapter_state_card(db, project_id, chapter_index)
    if card.get("status") != "ready":
        return None
    message = (
        "【上一章状态卡】"
        f"第{card['chapter_index']}章《{card.get('title') or ''}》结尾：{card.get('last_excerpt') or ''}"
    )
    key_terms = card.get("key_terms") or []
    if key_terms:
        message += f"；延续关键词：{', '.join(str(term) for term in key_terms[:8])}"
    return {"status": "active", "card": card, "message": message}
```

Update `_effective_chapter_command_args` to accept multiple feedback messages in order:

1. original user `command_args`;
2. continuity feedback;
3. length feedback.

Attach `agent_continuity_feedback` to the result when feedback exists.

- [x] **Step 8: Run GREEN state-card tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_reports_previous_chapter_state_card tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_previous_state_card -q
```

Expected: both pass.

## Task 2: Add Deterministic Drift and Convenience Review Gates

**Files:**

- Modify: `backend/app/core/chapter_quality_review.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing profile-drift review test**

Add:

```python
def test_agent_review_chapter_quality_flags_character_profile_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员，只是一直隐瞒身份。"
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
    finding = next(item for item in output["findings"] if item["code"] == "character_profile_drift")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["character"] == "苏晚晴"
    assert "失踪者家属" in finding["evidence"]["known_profile"]
```

- [x] **Step 2: Write failing ability-boundary test**

Add:

```python
def test_agent_review_chapter_quality_flags_ability_boundary_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴抬手制造幻觉，凭空创造出一段真实记忆骗过守卫。"
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
    finding = next(item for item in output["findings"] if item["code"] == "ability_boundary_drift")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert "制造幻觉" in finding["evidence"]["matched_terms"]
```

- [x] **Step 3: Write failing convenience review test**

Add:

```python
def test_agent_review_chapter_quality_warns_on_convenient_key_item_acquisition(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "老赵看了林深一眼，立刻把稀有记忆雾晶给了他，让他们马上离开。"
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
    finding = next(item for item in output["findings"] if item["code"] == "convenient_key_item_acquisition")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert "记忆雾晶" in finding["evidence"]["matched_terms"]
```

- [x] **Step 4: Run RED review tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_character_profile_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_ability_boundary_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_convenient_key_item_acquisition -q
```

Expected: fail because the new findings do not exist.

- [x] **Step 5: Implement minimal review helpers**

In `backend/app/core/chapter_quality_review.py`, add helpers:

```python
IDENTITY_MARKERS = ("以前是", "其实是", "原来是", "曾是", "真实身份")
CONFLICTING_ROLE_TERMS = ("雾安局研究员", "雾安局特工", "研究员", "特工")
ABILITY_FORBIDDEN_TERMS = ("制造幻觉", "凭空创造", "创造真实记忆", "篡改记忆")
KEY_ITEM_TERMS = ("记忆雾晶", "雾晶", "钥匙", "核心", "信物")
ACQUISITION_TERMS = ("给了", "交给", "递给", "拿到", "获得", "买到")
COST_OR_RISK_TERMS = ("代价", "交换", "条件", "欠", "债", "受伤", "暴露", "损失", "背叛", "追杀", "风险")
```

Implement:

- `_setup_payload(db, project_id)` to load latest `Setup`.
- `_character_profile_drift_findings(setup, content)`.
- `_ability_boundary_findings(setup, content)`.
- `_convenient_key_item_findings(content)`.

Keep the first version deterministic and conservative:

- Only inspect explicit setup characters.
- Only flag identity drift when a character name, an identity marker, and a conflicting role term appear in the same short window.
- Only flag ability drift when setup rules contain a negative marker such as `不能` and content contains forbidden ability terms.
- Only flag convenience when key-item acquisition terms appear and no cost/risk terms appear in the same sentence.

Add findings to `review_chapter_quality` after word-target checks.

- [x] **Step 6: Run GREEN review tests**

Run the same three tests and confirm they pass.

- [x] **Step 7: Run focused quality review regression**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_generic_title_and_length tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_modest_over_target_length tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_future_outline_overlap tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_ignores_single_future_character_name_match -q
```

Expected: pass.

## Task 3: Dogfood Chapter 6/7 Decision Loop

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md`

- [x] **Step 1: Run dogfood review for Chapter 6**

Run a Writing Agent run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 6}}
]
```

Expected:

- If new gates catch known drift, status may become `blocked`.
- Record exact finding codes, severity, and messages.

- [x] **Step 2: Run Chapter 7 preflight**

Run:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 7}}
]
```

Expected:

- `previous_chapter_state_card` is present and references Chapter 6.
- If preflight is blocked for missing outline or unresolved quality gates, record it.

- [x] **Step 3: Generate Chapter 7 only when safe**

If Chapter 6 review has blocker findings, do not force Chapter 7 generation. Record that Phase18 intentionally stopped at the gate.

If Chapter 6 has no blockers and Chapter 7 preflight is ready, run:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 7}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 7}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 7}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 7}}
]
```

Expected:

- Generated Chapter 7 has `word_count >= 2000`.
- Step output includes `agent_continuity_feedback`.
- Review blockers are 0 before moving to proposal resolution.

- [x] **Step 4: Resolve proposal queue if Chapter 7 generated**

If Chapter 7 generated proposals:

- Run `draft_world_model_proposal_resolution_decisions`.
- Run `apply_world_model_proposal_resolution` with confirm only for the drafted safe decisions.
- Run final `review_chapter_quality` for Chapter 7.

## Task 4: Verification, Report, Commit, Push

**Files:**

- Modify: all changed Phase18 files.

- [x] **Step 1: Run T2 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [x] **Step 2: Write Phase18 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md` with:

- code changes;
- RED/GREEN evidence;
- dogfood Chapter 6 review result;
- Chapter 7 preflight/generation decision;
- unresolved issues;
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
- only intended Phase18 files are changed.

- [x] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md
git commit -m "docs: plan long memory agent phase 18"
```

Commit implementation/report after verification:

```powershell
git add backend/app/services/writing_agent/run_service.py backend/app/core/chapter_quality_review.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase18-continuity-state-card-and-drift-gates.md
git commit -m "feat: add continuity and drift gates"
git push origin main
```
