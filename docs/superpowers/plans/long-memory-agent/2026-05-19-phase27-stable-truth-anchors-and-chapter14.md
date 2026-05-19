# Stable Truth Anchors and Chapter 14 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move high-salience continuity facts into the confirmed world-model truth layer, make continuity review read those stable anchors, and continue the dogfood novel toward Chapter 14 only after the anchor gate is clean.

**Architecture:** Reuse `WorldFactClaim` as the stable truth source. Do not create a parallel anchor table. The Writing Agent should create/approve only whitelisted continuity-anchor facts through the existing proposal/review governance path, then `review_chapter_continuity` should compare extracted chapter anchors against current-profile confirmed truth facts.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing world proposal service, Writing Agent run service, pytest.

---

## Context

Phase26 added `review_chapter_continuity`, but it only compares recent generated text. Phase26 and subagent review found that the dogfood project still has no confirmed `world_fact_claims`, so critical anchors remain vulnerable to drift:

- `林深:father_name = 林建国`
- `顾衍:military_tag_number = N-017`
- `N-07` is an experiment code / experimental subject code, not Gu Yan's military-tag number.
- `雾灾日期 = 2045年8月12日`
- `雾灾发生前三天 = 2045年8月9日`

Current automatic proposals include weak metadata and at least one bad date summary, so this phase must keep approval constrained and explicit.

## Scope

In scope:

- Let `review_chapter_continuity` query current-profile confirmed `WorldFactClaim` rows for whitelisted anchor predicates.
- Return blocker findings when generated chapter text contradicts stable truth anchors.
- Add a deterministic Writing Agent tool to seed missing continuity anchor proposals for the current dogfood truth set.
- Extend guarded proposal apply only enough to approve whitelisted continuity-anchor predicates with `confirm_apply=True`.
- Seed and approve the dogfood critical anchors before Chapter 14.
- Run Chapter 14 preflight after anchor approval.

Out of scope:

- A generic knowledge-base module.
- Full semantic contradiction detection.
- Automatic approval of ordinary world-model proposals.
- Solving all old weak/incorrect proposal items.
- Frontend display changes.

## Anchor Predicate Contract

Stable continuity anchors will use confirmed truth facts:

```text
claim_layer = "truth"
claim_status = "confirmed"
authority_type = "authoritative_structured" or "derived"
```

Initial predicate contract:

- `father_name`: subject is a character ref, value is the canonical parent name.
- `military_tag_number`: subject is a character ref, value is the canonical military-tag number.
- `identifier_meaning`: subject is an identifier ref such as `identifier.N-07`, value describes what the identifier is and is not.
- `event_date`: subject is an event ref such as `event.fog_disaster`, value is the canonical date.
- `relative_event_date`: subject is an event ref such as `event.fog_disaster.minus_3_days`, value is the canonical date.

## Files

- Modify: `backend/app/core/chapter_continuity_review.py`
- Create: `backend/app/core/continuity_anchor_proposals.py`
- Modify: `backend/app/core/world_proposal_resolution_apply.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Add report: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase27-stable-truth-anchors-and-chapter14.md`

## Task 1: Stable Truth Anchor Lookup in Continuity Review

- [ ] **Step 1: Write failing truth-conflict tests**

Add tests in `backend/tests/test_writing_agent_runs.py`:

```python
def test_agent_review_chapter_continuity_blocks_against_confirmed_father_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.father-name",
        subject_ref="林深",
        predicate="father_name",
        object_ref_or_value="林建国",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "空白信背面浮出署名——林远山。林深认出那是父亲留下的字迹。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定父亲姓名锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["code"] == "stable_truth_anchor_conflict"
    assert finding["evidence"]["anchor_key"] == "林深:father_name"
    assert finding["evidence"]["truth_value"] == "林建国"
    assert finding["evidence"]["observed_values"] == ["林远山"]
```

Also add equivalent tests for:

- `顾衍:military_tag_number` truth `N-017` conflicting with text that treats `N-07` as military tag number.
- `fog_disaster_minus_3_days` truth `2045年8月9日` conflicting with text that says `2045年8月12日` is three days before the disaster.

- [ ] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_blocks_against_confirmed_father_truth -q
```

Expected: FAIL because continuity review does not query `WorldFactClaim`.

- [ ] **Step 3: Implement stable truth lookup**

Modify `backend/app/core/chapter_continuity_review.py`:

- import `ProjectProfileVersion` and `WorldFactClaim`;
- add `_current_profile(db, project_id)`;
- add `_stable_truth_anchors(db, project_id, chapter_index)`;
- map facts to the existing anchor keys:
  - `("林深", "father_name") -> "林深:father_name"`
  - `("顾衍", "military_tag_number") -> "顾衍:military_tag_number"`
  - `("event.fog_disaster.minus_3_days", "relative_event_date") -> "fog_disaster_minus_3_days"`
- compare observed extracted values with stable truth values;
- emit `stable_truth_anchor_conflict` blocker with `truth_claim_id`, `truth_value`, `observed_values`, and references.

- [ ] **Step 4: Run GREEN**

Run the three truth-conflict tests.

Expected: PASS.

## Task 2: Seed Continuity Anchor Proposals

- [ ] **Step 1: Write failing seed-tool test**

Add:

```python
def test_agent_seed_continuity_anchor_proposals_creates_missing_anchor_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "补齐稳定连续性锚点提案",
            "tools": [{"tool_name": "seed_continuity_anchor_proposals"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert output["created_item_count"] >= 5
    assert output["should_generate_next_chapter"] is False
    assert {
        (item.subject_ref, item.predicate)
        for item in db_session.query(WorldProposalItem).filter_by(project_id=project.id).all()
    } >= {
        ("林深", "father_name"),
        ("顾衍", "military_tag_number"),
        ("identifier.N-07", "identifier_meaning"),
        ("event.fog_disaster", "event_date"),
        ("event.fog_disaster.minus_3_days", "relative_event_date"),
    }
```

- [ ] **Step 2: Run RED**

Run the seed-tool test.

Expected: FAIL because the Writing Agent tool is not registered.

- [ ] **Step 3: Implement deterministic proposal seeding**

Create `backend/app/core/continuity_anchor_proposals.py`:

- load current profile;
- create one bundle titled `稳定连续性锚点`;
- write missing `WorldProposalItem` rows for the five initial anchors;
- use idempotent `claim_id` values such as `claim.continuity.linshen.father_name`;
- skip an anchor when an actionable proposal or confirmed truth already exists for the same `subject_ref/predicate`;
- return `status="blocked"` when created or pending anchors remain, because approvals are still required.

Modify `backend/app/services/writing_agent/run_service.py`:

- register `seed_continuity_anchor_proposals` as internal tool;
- target type `world_model`;
- generation must stop after this report until proposals are resolved.

- [ ] **Step 4: Run GREEN**

Run the seed-tool test.

Expected: PASS.

## Task 3: Guarded Approval for Continuity Anchors

- [ ] **Step 1: Write failing approval test**

Add a test proving `apply_world_model_proposal_resolution` can approve only whitelisted continuity anchor proposals with `confirm_apply=True`:

```python
def test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={"goal": "seed", "tools": [{"tool_name": "seed_continuity_anchor_proposals"}]},
    )
    item = db_session.query(WorldProposalItem).filter_by(
        project_id=project.id,
        subject_ref="林深",
        predicate="father_name",
    ).one()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审批稳定锚点",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "approve",
                                "reason": "确认父亲姓名锚点",
                                "evidence_refs": ["chapter:10", "chapter:11", "chapter:13"],
                            }
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["applied_count"] == 1
    assert db_session.query(WorldFactClaim).filter_by(project_id=project.id, predicate="father_name").count() == 1
```

Keep the existing approval-rejection test for non-anchor proposals passing.

- [ ] **Step 2: Run RED**

Run the new approval test and the existing non-anchor rejection test.

Expected: new test FAILS; existing test PASSES.

- [ ] **Step 3: Implement whitelisted approval**

Modify `backend/app/core/world_proposal_resolution_apply.py`:

- allow `approve` / `approve_with_edits` only when the target proposal item is a continuity-anchor proposal;
- require `confirm_apply=True`;
- keep ordinary approvals blocked with `approval_not_supported_in_guarded_apply`;
- call existing `review_proposal_item()` so `WorldFactClaim`, review record, retrieval sync, and cache invalidation remain on the existing governance path.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes -q
```

Expected: PASS.

## Task 4: Dogfood Anchor Approval and Chapter 14 Preflight

- [ ] **Step 1: Seed missing dogfood anchors**

Use Writing Agent on project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
{"tool_name": "seed_continuity_anchor_proposals"}
```

Expected: creates or reports the five stable anchor proposals.

- [ ] **Step 2: Approve only the deterministic anchors**

Use `apply_world_model_proposal_resolution` with `confirm_apply=True` for the seeded five anchors.

Expected: confirmed `WorldFactClaim` rows exist, and ordinary weak proposals are not auto-approved.

- [ ] **Step 3: Re-run continuity review for Chapter 13**

Expected: ready, 0 findings.

- [ ] **Step 4: Preflight Chapter 14**

If outline is missing, expand only the Chapter 14 outline first. Do not generate Chapter 14 until stable anchors are confirmed and preflight is ready.

## Task 5: Verification, Report, Commit

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

Expected: no whitespace errors, no secret matches, only intended changes.

- [ ] **Step 3: Write Phase27 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase27-stable-truth-anchors-and-chapter14.md` with:

- implementation summary;
- RED/GREEN evidence;
- seeded anchor facts;
- dogfood world fact count before/after;
- Chapter 13 continuity result;
- Chapter 14 preflight result;
- next phase recommendation.

- [ ] **Step 4: Commit and push**

Commit plan separately, then implementation/report after verification.
