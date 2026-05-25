# Phase 19 Revision Bridge for Drift Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Phase18 drift-gate findings into actionable revision plans and non-destructive revision drafts for Chapter 6 before continuing generation.

**Architecture:** Keep the existing chapter revision pipeline non-destructive. Extend the revision planner and draft annotation anchoring so `character_profile_drift` and `ability_boundary_drift` findings produce precise revision actions, comments, and selected evidence.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `chapter_quality_review`, `chapter_revision_planner`, `chapter_revision_drafts`, pytest.

---

## Phase Metadata

- **Phase:** 19
- **Date:** 2026-05-19
- **Verification Tier:** T1 for planner/draft behavior; T2 for dogfood plan/draft on Chapter 6 and focused backend regressions.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 6 revision plan and planner-owned draft annotations for the blocker findings.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Starting State

- Generated chapters: 6
- Latest chapter: Chapter 6 `黑市雾晶`
- Chapter 6 review status from Phase18: `blocked`
- Blocker findings:
  - `character_profile_drift` for `叶知秋`
  - `ability_boundary_drift` for `制造幻觉`
- Chapter 7 preflight is structurally ready, but generation is intentionally blocked until Chapter 6 quality is repaired.

## Problem

Phase18 can detect important drift, but the repair bridge is incomplete:

- `plan_chapter_revision` currently maps only older findings such as generic title, length, future overlap, and missing outline.
- New blocker findings are not converted into revision actions.
- `create_revision_draft` can create planner annotations, but the action comments and selected evidence are not tailored to identity or ability drift.

Without this bridge, the Agent can stop unsafe generation but cannot guide the user/system toward a concrete repair.

## Success Criteria

- `plan_chapter_revision` maps `character_profile_drift` to `fix_character_profile_drift`.
- `plan_chapter_revision` maps `ability_boundary_drift` to `respect_ability_boundary`.
- `plan_chapter_revision` maps `convenient_key_item_acquisition` to `add_key_item_cost`.
- Each mapped action carries evidence from the source finding.
- `create_revision_draft` anchors annotations to evidence excerpts when available.
- Revision comments are specific enough to tell the writer what to fix.
- Dogfood Chapter 6 produces a blocked revision plan with two actions and a planner-owned draft with two annotations.
- Chapter 6正文 is not overwritten in this phase.
- Chapter 7 remains ungenerated until Chapter 6 blockers are resolved.

## Explicit Non-Goals

- Do not directly rewrite or replace Chapter 6 content.
- Do not submit or apply revisions.
- Do not add frontend UI.
- Do not change database schema.
- Do not call LLMs in this phase unless existing tools already do so.
- Do not generate Chapter 7.

## Files

- Modify: `backend/app/core/chapter_revision_planner.py`
- Modify: `backend/app/core/chapter_revision_drafts.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md`

## Task 1: Map Drift Findings to Revision Actions

**Files:**

- Modify: `backend/app/core/chapter_revision_planner.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing planner test for drift findings**

Add this test near existing revision planner tests in `backend/tests/test_writing_agent_runs.py`:

```python
def test_agent_plan_chapter_revision_maps_drift_findings_to_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章漂移修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    actions = {action["action"]: action for action in output["revision_actions"]}
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert "fix_character_profile_drift" in actions
    assert "respect_ability_boundary" in actions
    assert actions["fix_character_profile_drift"]["source_finding"] == "character_profile_drift"
    assert actions["respect_ability_boundary"]["source_finding"] == "ability_boundary_drift"
    assert actions["fix_character_profile_drift"]["evidence"]["character"] == "苏晚晴"
    assert "制造幻觉" in actions["respect_ability_boundary"]["evidence"]["matched_terms"]
```

- [x] **Step 2: Run RED planner test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_drift_findings_to_actions -q
```

Expected: fail because revision actions are missing.

- [x] **Step 3: Implement minimal planner mappings**

In `backend/app/core/chapter_revision_planner.py`, update `_action_for_finding`:

```python
    if code == "character_profile_drift":
        return {
            "action": "fix_character_profile_drift",
            "severity": severity,
            "source_finding": code,
            "reason": message,
            "target": "修正角色身份、职业、性别或履历表述，使其回到既有设定；不要把漂移设定继续写成事实。",
            "evidence": finding.get("evidence") or {},
        }
    if code == "ability_boundary_drift":
        return {
            "action": "respect_ability_boundary",
            "severity": severity,
            "source_finding": code,
            "reason": message,
            "target": "删除或改写超出既有世界规则的能力表现；如需保留新能力，必须先有明确解锁原因和世界模型提案。",
            "evidence": finding.get("evidence") or {},
        }
    if code == "convenient_key_item_acquisition":
        return {
            "action": "add_key_item_cost",
            "severity": severity,
            "source_finding": code,
            "reason": message,
            "target": "为关键道具或线索补足代价、条件、债务、暴露风险或后续反噬。",
            "evidence": finding.get("evidence") or {},
        }
```

- [x] **Step 4: Run GREEN planner test**

Run the same test and confirm it passes.

## Task 2: Anchor Revision Drafts to Drift Evidence

**Files:**

- Modify: `backend/app/core/chapter_revision_drafts.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing draft annotation test**

Add:

```python
def test_agent_create_revision_draft_anchors_drift_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第1章漂移修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=output["revision_id"]).all()
    comments = [annotation.comment or "" for annotation in annotations]
    selected = [annotation.selected_text or "" for annotation in annotations]
    assert response.status_code == 200
    assert output["status"] == "drafted"
    assert output["annotation_count"] == 2
    assert any("[PLAN_ACTION:fix_character_profile_drift]" in comment for comment in comments)
    assert any("[PLAN_ACTION:respect_ability_boundary]" in comment for comment in comments)
    assert any("雾安局研究员" in text for text in selected)
    assert any("制造幻觉" in text for text in selected)
    assert db_session.query(ChapterContent).filter_by(id=chapter.id).one().content == chapter.content
```

- [x] **Step 2: Run RED draft test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_anchors_drift_actions -q
```

Expected: fail because actions/comments/anchors are not specific.

- [x] **Step 3: Improve selected evidence extraction**

In `backend/app/core/chapter_revision_drafts.py`, update `_selected_evidence_text` so it can use:

- `evidence["excerpt"]`
- `evidence["matched_role"]`
- `evidence["matched_terms"]`

Minimal behavior:

```python
    excerpt = str(evidence.get("excerpt") or "").strip()
    if excerpt and excerpt in content:
        return excerpt[: min(len(excerpt), 80)]
    matched_role = str(evidence.get("matched_role") or "").strip()
    if matched_role and matched_role in content:
        return matched_role
    matched_terms = evidence.get("matched_terms") if isinstance(evidence.get("matched_terms"), list) else []
    for term in matched_terms:
        value = str(term or "").strip()
        if value and value in content:
            return value
```

- [x] **Step 4: Add drift action comments**

In `_comment_for_action`, add:

```python
    elif action_name == "fix_character_profile_drift":
        message = str(action.get("target") or "修正角色身份表述，使其回到既有设定。")
    elif action_name == "respect_ability_boundary":
        message = str(action.get("target") or "改写超出既有世界规则的能力表现。")
    elif action_name == "add_key_item_cost":
        message = str(action.get("target") or "补足关键道具获得的代价或风险。")
```

- [x] **Step 5: Run GREEN draft test**

Run the same test and confirm it passes.

## Task 3: Dogfood Chapter 6 Revision Plan and Draft

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md`

- [x] **Step 1: Run dogfood revision plan**

Run a Writing Agent run:

```json
[
  {"tool_name": "plan_chapter_revision", "params": {"chapter_index": 6}}
]
```

Expected:

- status `blocked`
- revision actions include `fix_character_profile_drift` and `respect_ability_boundary`
- `should_generate_next_chapter` is false.

- [x] **Step 2: Run dogfood revision draft**

Run:

```json
[
  {"tool_name": "create_revision_draft", "params": {"chapter_index": 6}}
]
```

Expected:

- status `drafted` or reused planner-owned draft;
- annotations include both drift action comments;
- Chapter 6 content remains unchanged.

- [x] **Step 3: Confirm Chapter 7 remains blocked by policy**

Do not generate Chapter 7. Record that the next required action is applying or submitting the Chapter 6 revision, not continuing generation.

## Task 4: Verification, Report, Commit, Push

**Files:**

- Modify all Phase19 files.

- [x] **Step 1: Run targeted verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [x] **Step 2: Write Phase19 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md` with:

- code changes;
- RED/GREEN evidence;
- dogfood run IDs;
- revision action and annotation evidence;
- Chapter 6 no-overwrite confirmation;
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
- only intended Phase19 files are changed.

- [x] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md
git commit -m "docs: plan long memory agent phase 19"
```

Commit implementation/report after verification:

```powershell
git add backend/app/core/chapter_revision_planner.py backend/app/core/chapter_revision_drafts.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase19-revision-bridge-for-drift-gates.md
git commit -m "feat: bridge drift findings to revision drafts"
git push origin main
```
