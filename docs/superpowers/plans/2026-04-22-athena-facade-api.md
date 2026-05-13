# Athena Facade API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Athena Facade API layer that wraps existing modules under a unified `/athena` prefix, add `dialog_type` to the Dialog model for dual-dialog support, and create the Athena Dialog endpoints.

**Architecture:** New `api/athena.py` router with facade endpoints that delegate to existing module functions. Alembic migration adds `dialog_type` column to `dialogs` table. Athena Dialog reuses existing dialog infrastructure with a type filter. All existing APIs remain untouched.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic

---

### Task 1: Add `dialog_type` to Dialog Model + Migration

**Files:**
- Modify: `backend/app/models/dialog.py`
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_dialog_type_to_dialogs.py`

- [ ] **Step 1: Update Dialog model**

Add `dialog_type` column to `backend/app/models/dialog.py`:

```python
dialog_type = Column(String, default="hermes", nullable=False, server_default="hermes")
```

Add it after the `id` and `project_id` columns.

- [ ] **Step 2: Create Alembic migration**

Run: `cd backend && .venv/bin/alembic revision --autogenerate -m "add dialog_type to dialogs"`

Verify the generated migration adds a column `dialog_type` to `dialogs` with server_default `"hermes"`.

- [ ] **Step 3: Run migration**

Run: `cd backend && .venv/bin/alembic upgrade head`
Expected: Migration applies successfully.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/dialog.py backend/alembic/versions/
git commit -m "feat: add dialog_type column to Dialog model"
```

---

### Task 2: Update Dialog Helper to Support dialog_type

**Files:**
- Modify: `backend/app/api/dialogs.py`

- [ ] **Step 1: Update `_get_or_create_dialog` to accept dialog_type**

Change the function signature and filter:

```python
def _get_or_create_dialog(db: Session, project_id: str, dialog_type: str = "hermes") -> Dialog:
    dialog = db.query(Dialog).filter(
        Dialog.project_id == project_id,
        Dialog.dialog_type == dialog_type,
    ).first()
    if not dialog:
        dialog = Dialog(project_id=project_id, dialog_type=dialog_type)
        db.add(dialog)
        db.commit()
        db.refresh(dialog)
    return dialog
```

- [ ] **Step 2: Update `get_messages` to accept dialog_type query param**

```python
@router.get("/api/v1/dialog/projects/{project_id}/messages")
def get_messages(project_id: str, dialog_type: str = "hermes", db: Session = Depends(get_db)):
    dialog = db.query(Dialog).filter(
        Dialog.project_id == project_id,
        Dialog.dialog_type == dialog_type,
    ).first()
```

The rest of the function stays the same.

- [ ] **Step 3: Verify existing tests still pass**

Run: `cd backend && .venv/bin/python -m pytest -v`
Expected: PASS (existing behavior unchanged since default is "hermes")

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/dialogs.py
git commit -m "feat: support dialog_type in dialog helpers"
```

---

### Task 3: Create Athena Facade Router — Ontology Layer

**Files:**
- Create: `backend/app/api/athena.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/api/athena.py` with ontology endpoints**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Project,
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldLocation,
    WorldFaction,
    WorldArtifact,
    WorldResource,
    WorldRelation,
    WorldRule,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/athena",
    tags=["athena"],
)


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


@router.get("/ontology")
def get_ontology(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    profile = _get_current_profile(db, project_id)
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()

    entities = {}
    if profile:
        for model, key in [
            (WorldCharacter, "characters"),
            (WorldLocation, "locations"),
            (WorldFaction, "factions"),
            (WorldArtifact, "artifacts"),
            (WorldResource, "resources"),
        ]:
            items = db.query(model).filter(model.project_id == project_id).all()
            entities[key] = [{"id": item.id, "name": getattr(item, "name", getattr(item, "entity_ref", item.id))} for item in items]

    relations = []
    if profile:
        rels = db.query(WorldRelation).filter(WorldRelation.project_id == project_id).all()
        relations = [{"id": r.id, "source_ref": r.source_ref, "target_ref": r.target_ref, "relation_type": r.relation_type} for r in rels]

    rules = []
    if profile:
        rule_rows = db.query(WorldRule).filter(WorldRule.project_id == project_id).all()
        rules = [{"id": r.id, "rule_id": r.rule_id, "description": r.description} for r in rule_rows]

    return {
        "entities": entities,
        "relations": relations,
        "rules": rules,
        "setup_summary": {
            "characters": setup.characters if setup else None,
            "world_building": setup.world_building if setup else None,
            "core_concept": setup.core_concept if setup else None,
        } if setup else None,
        "profile_version": profile.version if profile else None,
    }


@router.get("/ontology/entities")
def get_ontology_entities(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    result = {}
    for model, key in [
        (WorldCharacter, "characters"),
        (WorldLocation, "locations"),
        (WorldFaction, "factions"),
        (WorldArtifact, "artifacts"),
        (WorldResource, "resources"),
    ]:
        items = db.query(model).filter(model.project_id == project_id).all()
        result[key] = [{"id": item.id, "name": getattr(item, "name", getattr(item, "entity_ref", item.id))} for item in items]
    return result


@router.get("/ontology/relations")
def get_ontology_relations(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    from app.api.topologies import get_topology
    return get_topology(project_id, db)


@router.get("/ontology/rules")
def get_ontology_rules(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    rules = db.query(WorldRule).filter(WorldRule.project_id == project_id).all()
    return [{"id": r.id, "rule_id": r.rule_id, "description": r.description, "scope": r.scope} for r in rules]


@router.post("/ontology/generate")
async def generate_ontology(project_id: str, db: Session = Depends(get_db)):
    from app.api.setups import generate_setup
    return await generate_setup(project_id, db)
```

- [ ] **Step 2: Register router in `backend/app/main.py`**

Add after the existing imports:

```python
from app.api import athena
```

Add after the last `app.include_router`:

```python
app.include_router(athena.router)
```

- [ ] **Step 3: Test the endpoints**

Run: `cd backend && .venv/bin/python -c "from app.main import app; from fastapi.testclient import TestClient; c = TestClient(app); print([r.path for r in app.routes if 'athena' in str(r.path)])"`
Expected: List of athena routes

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/athena.py backend/app/main.py
git commit -m "feat: add Athena facade router with ontology endpoints"
```

---

### Task 4: Athena Facade — State Layer

**Files:**
- Modify: `backend/app/api/athena.py`

- [ ] **Step 1: Add state endpoints**

Append to `backend/app/api/athena.py`:

```python
@router.get("/state")
def get_state(project_id: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_world_model_overview
    return get_world_model_overview(project_id, db)


@router.get("/state/subject-knowledge")
def get_state_subject_knowledge(project_id: str, subject_ref: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_subject_knowledge
    return get_subject_knowledge(project_id, subject_ref, db)


@router.get("/state/snapshot")
def get_state_snapshot(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    from app.api.world_model import get_chapter_snapshot
    return get_chapter_snapshot(project_id, chapter_index, db)


@router.get("/state/timeline")
def get_state_timeline(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    profile = _get_current_profile(db, project_id)
    if profile is None:
        return {"anchors": [], "events": []}

    from app.models import WorldTimelineAnchor, WorldEvent

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(WorldTimelineAnchor.chapter_index.asc(), WorldTimelineAnchor.intra_chapter_seq.asc())
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
        )
        .order_by(WorldEvent.chapter_index.asc(), WorldEvent.intra_chapter_seq.asc())
        .all()
    )
    return {
        "anchors": [
            {
                "id": a.id,
                "anchor_id": a.anchor_id,
                "chapter_index": a.chapter_index,
                "intra_chapter_seq": a.intra_chapter_seq,
                "label": a.label,
            }
            for a in anchors
        ],
        "events": [
            {
                "id": e.id,
                "event_id": e.event_id,
                "chapter_index": e.chapter_index,
                "intra_chapter_seq": e.intra_chapter_seq,
                "event_type": e.event_type,
                "description": e.description,
            }
            for e in events
        ],
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/athena.py
git commit -m "feat: add Athena state layer endpoints"
```

---

### Task 5: Athena Facade — Evolution Layer

**Files:**
- Modify: `backend/app/api/athena.py`

- [ ] **Step 1: Add evolution endpoints**

Append to `backend/app/api/athena.py`:

```python
@router.get("/evolution/plan")
def get_evolution_plan(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    from app.models import Outline, Storyline

    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    return {
        "outline": {
            "id": outline.id,
            "status": outline.status,
            "content": outline.content,
        } if outline else None,
        "storyline": {
            "id": storyline.id,
            "status": storyline.status,
            "content": storyline.content,
        } if storyline else None,
    }


@router.post("/evolution/plan/generate")
async def generate_evolution_plan(
    project_id: str,
    target: str = "outline",
    db: Session = Depends(get_db),
):
    if target == "storyline":
        from app.api.storylines import generate_storyline
        return await generate_storyline(project_id, db)
    from app.api.outlines import generate_outline
    return await generate_outline(project_id, db)


@router.get("/evolution/proposals")
def get_evolution_proposals(
    project_id: str,
    offset: int = 0,
    limit: int = 20,
    bundle_status: str | None = None,
    item_status: str | None = None,
    db: Session = Depends(get_db),
):
    from app.api.world_model import list_world_proposal_bundles
    return list_world_proposal_bundles(
        project_id, offset, limit, bundle_status, item_status, None, db,
    )


@router.get("/evolution/proposals/{bundle_id}")
def get_evolution_proposal_detail(project_id: str, bundle_id: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_world_proposal_bundle
    return get_world_proposal_bundle(project_id, bundle_id, db)


@router.post("/evolution/proposals/{proposal_item_id}/review")
def review_evolution_proposal(
    project_id: str,
    proposal_item_id: str,
    payload: "ProposalReviewCreate",
    db: Session = Depends(get_db),
):
    from app.api.world_model import review_world_proposal_item
    from app.schemas import ProposalReviewCreate
    return review_world_proposal_item(project_id, proposal_item_id, payload, db)


@router.post("/evolution/proposals/{bundle_id}/split")
def split_evolution_proposal(
    project_id: str,
    bundle_id: str,
    payload: "ProposalBundleSplitCreate",
    db: Session = Depends(get_db),
):
    from app.api.world_model import split_world_proposal_bundle
    from app.schemas import ProposalBundleSplitCreate
    return split_world_proposal_bundle(project_id, bundle_id, payload, db)


@router.post("/evolution/reviews/{review_id}/rollback")
def rollback_evolution_review(
    project_id: str,
    review_id: str,
    payload: "ProposalReviewRollbackCreate",
    db: Session = Depends(get_db),
):
    from app.api.world_model import rollback_world_proposal_review
    from app.schemas import ProposalReviewRollbackCreate
    return rollback_world_proposal_review(project_id, review_id, payload, db)


@router.get("/evolution/consistency")
def get_evolution_consistency(project_id: str, db: Session = Depends(get_db)):
    from app.api.consistency import list_issues
    return list_issues(project_id, db)
```

Note: The `payload` type annotations use string literals to avoid circular imports. The actual types are imported inside the function body.

- [ ] **Step 2: Fix the type annotations**

Actually, import the schemas at the top of the file instead:

```python
from app.schemas import ProposalReviewCreate, ProposalBundleSplitCreate, ProposalReviewRollbackCreate
```

And use them directly in the function signatures (remove the string literal quotes).

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/athena.py
git commit -m "feat: add Athena evolution layer endpoints"
```

---

### Task 6: Athena Dialog Endpoints

**Files:**
- Modify: `backend/app/api/athena.py`

- [ ] **Step 1: Add Athena dialog endpoints**

Append to `backend/app/api/athena.py`:

```python
from app.api.dialogs import (
    _get_or_create_dialog,
    _build_diagnosis,
    _save_message,
    _build_chat_idle_hint,
    _free_chat_reply,
    _action_description,
    _latest_unfinished_action_type,
    _build_running_guard_response,
)
from app.models import Dialog, DialogMessage, PendingAction
from app.schemas import ChatIn, ChatOut, PendingActionOut, ProjectDiagnosisOut
from app.core.ui_hints import build_ui_hint, action_to_refresh_targets


@router.get("/dialog/messages")
def get_athena_messages(project_id: str, db: Session = Depends(get_db)):
    from app.api.dialogs import get_messages
    return get_messages(project_id, dialog_type="athena", db=db)


@router.post("/dialog/chat")
async def athena_chat(project_id: str, payload: ChatIn, db: Session = Depends(get_db)):
    project = _require_project(db, project_id)
    payload.project_id = project_id
    dialog = _get_or_create_dialog(db, project_id, dialog_type="athena")
    diagnosis = _build_diagnosis(db, project_id)

    user_text = (payload.text or "").strip()
    if user_text:
        _save_message(db, dialog.id, "user", user_text)

    reply = await _free_chat_reply(db, dialog, project, diagnosis)
    _save_message(db, dialog.id, "assistant", reply)
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("Athena 对话"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


@router.post("/dialog/resolve-action")
async def athena_resolve_action(project_id: str, payload: "ResolveActionIn", db: Session = Depends(get_db)):
    from app.api.dialogs import resolve_action
    from app.schemas import ResolveActionIn
    return await resolve_action(payload, db)
```

- [ ] **Step 2: Import ResolveActionIn at the top**

Add to the top-level imports:

```python
from app.schemas import ChatIn, ChatOut, PendingActionOut, ProjectDiagnosisOut, ResolveActionIn
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/athena.py
git commit -m "feat: add Athena dialog endpoints"
```

---

### Task 7: Verification & Cleanup

- [ ] **Step 1: Run backend tests**

Run: `cd backend && .venv/bin/python -m pytest -v`
Expected: All PASS

- [ ] **Step 2: Test Athena endpoints manually**

```bash
# Test ontology
curl -s http://localhost:8000/api/v1/projects/<PROJECT_ID>/athena/ontology | python -m json.tool | head -20

# Test state
curl -s http://localhost:8000/api/v1/projects/<PROJECT_ID>/athena/state | python -m json.tool | head -20

# Test timeline
curl -s http://localhost:8000/api/v1/projects/<PROJECT_ID>/athena/state/timeline | python -m json.tool | head -20

# Test evolution plan
curl -s http://localhost:8000/api/v1/projects/<PROJECT_ID>/athena/evolution/plan | python -m json.tool | head -20

# Test Athena dialog messages
curl -s http://localhost:8000/api/v1/projects/<PROJECT_ID>/athena/dialog/messages | python -m json.tool

# Test existing API still works
curl -s http://localhost:8000/api/v1/projects/<PROJECT_ID>/world-model | python -m json.tool | head -10
```

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: cleanup after Athena facade API implementation"
```
