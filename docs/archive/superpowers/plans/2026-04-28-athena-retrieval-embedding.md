# Athena Retrieval Embedding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent hybrid retrieval layer for Athena so long-form chapter generation can retrieve relevant prior chapters and world facts before prompt assembly.

**Architecture:** Store retrieval documents, chunks, and embedding vectors in SQLite. Use a deterministic local embedding provider as the default test/dev path, with an OpenAI-compatible remote provider behind configuration. Athena context assembly ranks chunks with hybrid lexical/vector scoring and injects the top evidence into chapter prompts.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, SQLite JSON, Vue 3, Pinia, Vitest, pytest.

---

### File Structure

- Create `backend/app/models/retrieval.py`: ORM tables for documents, chunks, and embeddings.
- Create `backend/app/core/embedding_service.py`: embedding provider abstraction, local deterministic vectors, optional remote embedding client, cosine helpers.
- Create `backend/app/core/athena_retrieval.py`: indexing, search, diagnostics, and context-section builders.
- Create `backend/app/schemas/athena_retrieval.py`: API request/response schemas.
- Create `backend/alembic/versions/20260428_add_athena_retrieval_tables.py`: persistent retrieval schema.
- Modify `backend/app/models/__init__.py`: register retrieval models.
- Modify `backend/app/core/athena_longform.py`: add retrieval section to `build_chapter_context_package`.
- Modify `backend/app/api/athena.py`: expose reindex, chapter index, search, diagnostics endpoints.
- Modify `backend/app/api/chapters.py`: refresh retrieval index after chapter generation.
- Create `backend/tests/test_athena_retrieval.py`: red/green coverage for indexing, search, API, and context injection.
- Modify `frontend/src/api/types.ts`: retrieval response types.
- Modify `frontend/src/api/client.ts`: retrieval API methods.
- Modify `frontend/src/stores/athena.ts`: retrieval state/actions.
- Modify `frontend/src/stores/ui.ts`: add `retrieval` Athena section.
- Modify `frontend/src/views/AthenaView.vue`: add retrieval navigation and panel.
- Create `frontend/src/components/athena/RetrievalPanel.vue`: diagnostics, search box, results.
- Create `frontend/src/stores/athena.retrieval.test.ts`: store API behavior.

### Task 1: Backend Retrieval Contract

- [ ] Write failing pytest coverage in `backend/tests/test_athena_retrieval.py` for chapter indexing and search:

```python
def test_index_project_retrieval_chunks_chapters_and_facts(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    response = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/search?q=旧灯塔&limit=5")
    assert response.status_code == 200
    assert response.json()["total"] >= 2
```

- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_retrieval.py -q`; expected failure: module/endpoints do not exist.
- [ ] Implement retrieval ORM, schemas, and core service with deterministic local embeddings.
- [ ] Add Alembic migration for `retrieval_documents`, `retrieval_chunks`, and `retrieval_embeddings`.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_retrieval.py -q`; expected pass.

### Task 2: Athena API and Context Injection

- [ ] Add failing tests for:
  - `POST /athena/retrieval/reindex`
  - `POST /athena/retrieval/chapters/{chapter_index}/index`
  - `GET /athena/retrieval/search`
  - `GET /athena/retrieval/diagnostics`
  - retrieval section appearing in `/athena/context/chapter/{chapter_index}`
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_retrieval.py -q`; expected failure on missing endpoints/context.
- [ ] Wire endpoints in `backend/app/api/athena.py`.
- [ ] Inject `build_retrieval_context_section()` output into `build_chapter_context_package()`.
- [ ] Refresh chapter retrieval index after generated chapter commit.
- [ ] Run targeted backend tests; expected pass.

### Task 3: Frontend Retrieval Panel

- [ ] Write failing Vitest coverage in `frontend/src/stores/athena.retrieval.test.ts` for `loadRetrievalDiagnostics`, `searchRetrieval`, and `reindexRetrieval`.
- [ ] Run `cd frontend && npm run test:unit -- src/stores/athena.retrieval.test.ts`; expected failure on missing actions/types.
- [ ] Add API types/client methods and Pinia state/actions.
- [ ] Add `retrieval` to Athena navigation and render `RetrievalPanel.vue`.
- [ ] Run targeted frontend test; expected pass.

### Task 4: Verification and Integration

- [ ] Run `cd backend && source .venv/bin/activate && pytest -q`.
- [ ] Run `cd frontend && npm run test:unit`.
- [ ] Run `cd frontend && npm run build`.
- [ ] Review `git diff --stat` and ensure no secrets, generated DBs, or local docs are staged in root.
- [ ] Commit with `feat: add Athena retrieval embeddings`.
