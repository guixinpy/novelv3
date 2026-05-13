# Module Absorption & Old API Deprecation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all frontend callers from old module APIs (setup, topology, storyline, outline, consistency) to Athena endpoints, then mark old backend routers as deprecated.

**Architecture:** Frontend `api/client.ts` methods are redirected to Athena endpoints. Frontend stores updated to call new methods. Old backend routers get a `Deprecation` response header but remain functional. No data model changes — Athena facade already delegates to the same underlying functions.

**Tech Stack:** FastAPI, Vue 3, TypeScript, Pinia

---

### Task 1: Frontend — Redirect Old API Methods to Athena Endpoints

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Update setup methods**

Change:
```typescript
generateSetup: (id: string) => request(`/projects/${id}/setup/generate`, { method: 'POST' }),
getSetup: (id: string) => request(`/projects/${id}/setup`),
```

To:
```typescript
generateSetup: (id: string) => request(`/projects/${id}/athena/ontology/generate`, { method: 'POST' }),
getSetup: (id: string) => request(`/projects/${id}/setup`),
```

Note: `getSetup` stays on the old endpoint because it returns `SetupOut` which has a different shape than `AthenaOntology`. The generate endpoint is compatible.

- [ ] **Step 2: Update storyline methods**

Change:
```typescript
generateStoryline: (id: string) => request(`/projects/${id}/storyline/generate`, { method: 'POST' }),
getStoryline: (id: string) => request(`/projects/${id}/storyline`),
```

To:
```typescript
generateStoryline: (id: string) => request(`/projects/${id}/athena/evolution/plan/generate?target=storyline`, { method: 'POST' }),
getStoryline: (id: string) => request(`/projects/${id}/storyline`),
```

- [ ] **Step 3: Update outline methods**

Change:
```typescript
generateOutline: (id: string) => request(`/projects/${id}/outline/generate`, { method: 'POST' }),
getOutline: (id: string) => request(`/projects/${id}/outline`),
```

To:
```typescript
generateOutline: (id: string) => request(`/projects/${id}/athena/evolution/plan/generate?target=outline`, { method: 'POST' }),
getOutline: (id: string) => request(`/projects/${id}/outline`),
```

- [ ] **Step 4: Update topology method**

Change:
```typescript
getTopology: (id: string) => request(`/projects/${id}/topology`),
```

To:
```typescript
getTopology: (id: string) => request(`/projects/${id}/athena/ontology/relations`),
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: redirect generate/topology API calls to Athena endpoints"
```

---

### Task 2: Backend — Add Deprecation Headers to Old Routers

**Files:**
- Modify: `backend/app/api/setups.py`
- Modify: `backend/app/api/topologies.py`
- Modify: `backend/app/api/storylines.py`
- Modify: `backend/app/api/outlines.py`
- Modify: `backend/app/api/consistency.py`

- [ ] **Step 1: Add deprecation middleware helper**

Create `backend/app/api/deprecation.py`:

```python
from fastapi import Response


def add_deprecation_header(response: Response, alternative: str) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-07-01"
    response.headers["Link"] = f'<{alternative}>; rel="successor-version"'
```

- [ ] **Step 2: Add deprecation to setups.py**

Add import at top:
```python
from fastapi import Response
from app.api.deprecation import add_deprecation_header
```

Update `generate_setup`:
```python
@router.post("/generate", response_model=SetupOut)
async def generate_setup(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology/generate")
    # ... rest unchanged
```

Update `get_setup`:
```python
@router.get("", response_model=SetupOut)
def get_setup(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology")
    # ... rest unchanged
```

- [ ] **Step 3: Add deprecation to topologies.py**

Same pattern — add `response: Response = None` parameter and call `add_deprecation_header` in each endpoint:

```python
@router.get("", response_model=TopologyOut)
def get_topology(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology/relations")
    # ... rest unchanged
```

Apply to `character_graph` and `timeline` endpoints too.

- [ ] **Step 4: Add deprecation to storylines.py**

```python
@router.post("/generate", response_model=StorylineOut)
async def generate_storyline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=storyline")
    # ... rest unchanged
```

Apply to `get_storyline` too.

- [ ] **Step 5: Add deprecation to outlines.py**

```python
@router.post("/generate", response_model=OutlineOut)
async def generate_outline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=outline")
    # ... rest unchanged
```

Apply to `get_outline` and `update_chapter_outline` too.

- [ ] **Step 6: Add deprecation to consistency.py**

```python
@router.post("/chapters/{chapter_index}/check")
async def run_check(project_id: str, chapter_index: int, depth: str = "l1", db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/consistency")
    # ... rest unchanged
```

Apply to `list_issues` too.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/deprecation.py backend/app/api/setups.py backend/app/api/topologies.py backend/app/api/storylines.py backend/app/api/outlines.py backend/app/api/consistency.py
git commit -m "feat: add deprecation headers to old module APIs"
```

---

### Task 3: Athena Facade — Add Missing Proxied Endpoints

**Files:**
- Modify: `backend/app/api/athena.py`

The Athena facade is missing some endpoints that the old APIs have. Add them for completeness:

- [ ] **Step 1: Add ontology/setup GET (returns SetupOut format)**

```python
@router.get("/ontology/setup")
def get_ontology_setup(project_id: str, db: Session = Depends(get_db)):
    from app.api.setups import get_setup
    return get_setup(project_id, db)
```

- [ ] **Step 2: Add evolution/consistency/check POST**

```python
@router.post("/evolution/consistency/chapters/{chapter_index}/check")
async def check_evolution_consistency(
    project_id: str,
    chapter_index: int,
    depth: str = "l1",
    db: Session = Depends(get_db),
):
    from app.api.consistency import run_check
    return await run_check(project_id, chapter_index, depth, db)
```

- [ ] **Step 3: Add evolution/plan/outline PATCH**

```python
@router.patch("/evolution/plan/outline/chapters/{chapter_index}")
def update_evolution_chapter_outline(
    project_id: str,
    chapter_index: int,
    payload: "ChapterOutlineUpdate",
    db: Session = Depends(get_db),
):
    from app.api.outlines import update_chapter_outline
    from app.schemas import ChapterOutlineUpdate
    return update_chapter_outline(project_id, chapter_index, payload, db)
```

- [ ] **Step 4: Add ontology/topology sub-endpoints**

```python
@router.get("/ontology/character-graph")
def get_ontology_character_graph(project_id: str, db: Session = Depends(get_db)):
    from app.api.topologies import character_graph
    return character_graph(project_id, db)


@router.get("/ontology/timeline")
def get_ontology_topology_timeline(project_id: str, db: Session = Depends(get_db)):
    from app.api.topologies import timeline
    return timeline(project_id, db)
```

- [ ] **Step 5: Import ChapterOutlineUpdate at top**

Add to the existing `from app.schemas import (...)` block:

```python
from app.schemas import (
    ChatIn,
    ChatOut,
    ChapterOutlineUpdate,
    ProposalBundleSplitCreate,
    ProposalReviewCreate,
    ProposalReviewRollbackCreate,
    ResolveActionIn,
)
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/athena.py
git commit -m "feat: add missing proxied endpoints to Athena facade"
```

---

### Task 4: Frontend — Update Athena Store to Use New Endpoints

**Files:**
- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add missing Athena API methods**

Add to `frontend/src/api/client.ts`:

```typescript
getAthenaSetup: (id: string) =>
  request(`/projects/${id}/athena/ontology/setup`),
getAthenaCharacterGraph: (id: string) =>
  request(`/projects/${id}/athena/ontology/character-graph`),
runAthenaConsistencyCheck: (id: string, chapterIndex: number, depth: string = 'l1') =>
  request(`/projects/${id}/athena/evolution/consistency/chapters/${chapterIndex}/check?depth=${depth}`, { method: 'POST' }),
```

- [ ] **Step 2: Add corresponding store methods**

Add to `frontend/src/stores/athena.ts`:

```typescript
const setup = ref<unknown>(null)

async function loadSetup(projectId: string) {
  try {
    setup.value = await api.getAthenaSetup(projectId)
  } catch (err) {
    error.value = toErrorMessage(err)
  }
}

async function runConsistencyCheck(projectId: string, chapterIndex: number, depth: string = 'l1') {
  try {
    await api.runAthenaConsistencyCheck(projectId, chapterIndex, depth)
  } catch (err) {
    error.value = toErrorMessage(err)
  }
}
```

Add `setup`, `loadSetup`, `runConsistencyCheck` to the return block and to `reset()`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/stores/athena.ts
git commit -m "feat: add missing Athena API methods and store actions"
```

---

### Task 5: Verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend && .venv/bin/python -m pytest -v`
Expected: All PASS

- [ ] **Step 2: Run frontend type check and build**

Run: `cd frontend && npx vue-tsc --noEmit && npm run build`
Expected: PASS

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 4: Verify deprecation headers**

```bash
cd backend && .venv/bin/python -c "
from app.main import app
from fastapi.testclient import TestClient
c = TestClient(app)
pid = '5b95b442-724b-4187-9507-283bf709dffa'

# Old setup endpoint should have deprecation header
r = c.get(f'/api/v1/projects/{pid}/setup')
print(f'setup: {r.status_code}, deprecated: {r.headers.get(\"Deprecation\", \"no\")}')

# Old topology endpoint
r = c.get(f'/api/v1/projects/{pid}/topology')
print(f'topology: {r.status_code}, deprecated: {r.headers.get(\"Deprecation\", \"no\")}')

# Athena endpoint should NOT have deprecation header
r = c.get(f'/api/v1/projects/{pid}/athena/ontology')
print(f'athena ontology: {r.status_code}, deprecated: {r.headers.get(\"Deprecation\", \"no\")}')
"
```

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "chore: cleanup after module absorption"
```