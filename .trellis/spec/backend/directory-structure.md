# Directory Structure

> How backend code is organized in this project.

---

## Overview

The backend is a single FastAPI application living under `backend/app/`. It follows a
layered architecture: API routes → core business logic → service layer → ORM models.
All Python files use `snake_case.py`.

---

## Directory Layout

```
backend/
├── app/                     # Main application package
│   ├── main.py              # FastAPI app, CORS, lifespan, router registration
│   ├── config.py            # API key loading (env → .env → keyring)
│   ├── db.py                # SQLAlchemy engine, sessionmaker, Base
│   ├── agent/               # LLM agent infrastructure (harness, loop, providers)
│   │   ├── providers/       # Provider abstraction (base.py, deepseek.py)
│   │   ├── harness.py       # Stateful agent session harness
│   │   ├── loop.py          # Stateless run loop (async iterator)
│   │   ├── budget.py        # Token/iteration budget tracking
│   │   ├── events.py        # Loop event types (dataclass)
│   │   └── tooling.py       # Tool registry and context
│   ├── api/                 # FastAPI route handlers (one file per resource)
│   │   ├── projects.py / chapters.py / outlines.py / ...
│   │   ├── athena.py / athena_dialog.py / athena_evolution.py / ...
│   │   └── v2_sessions.py   # SSE streaming agent sessions
│   ├── core/                # Business logic (~70+ files)
│   │   ├── ai_service.py / deepseek_adapter.py  # AI / LLM call layer
│   │   ├── error_handler.py / cache.py / event_bus.py
│   │   ├── world_*.py       # World model engine (~20+ files)
│   │   ├── chapter_*.py     # Chapter processing pipeline
│   │   ├── athena_*.py      # Athena (world-building) module core
│   │   └── ...              # prompt_manager, embedding_service, etc.
│   ├── domain/              # Domain layer (currently empty)
│   ├── models/              # SQLAlchemy ORM models (~37 files)
│   ├── prompting/           # Prompt template assembler
│   │   └── providers/       # Domain-specific prompt providers
│   ├── schemas/             # Pydantic request/response models (~23 files)
│   ├── services/            # Business services
│   │   ├── actions/         # Action execution & result viewing
│   │   ├── dialog/          # Message & session services
│   │   ├── tasks/           # Background task framework
│   │   ├── workspace/       # Workspace bootstrap
│   │   ├── writing/         # Writing state management
│   │   └── writing_agent/   # Agent orchestration (~100+ files)
│   └── tools/               # Agent tool definitions
├── alembic/                 # Migration scripts (~25 revisions)
│   └── versions/
├── alembic.ini
├── prompts/                 # Plain-text prompt templates
├── static/                  # Built frontend assets
├── tests/                   # pytest tests (~100+ test files)
├── test_support/            # Test helpers (agent_fakes, run helpers)
├── requirements.txt
├── ruff.toml
└── pytest.ini
```

---

## Module Organization

- **API routes** (`app/api/`): One file per domain resource. Each exports a
  `router = APIRouter(prefix="/api/v1/<resource>")`. Functions are named
  `create_<resource>`, `get_<resource>`, `list_<resources>`, etc.
- **Core logic** (`app/core/`): Stateless or minimal-state functions grouped by
  domain. New feature logic starts here before a service layer is justified.
- **Services** (`app/services/`): Stateful classes with `__init__(self, db: Session)`.
  Used when orchestration crosses multiple core modules or external boundaries.
- **Models** (`app/models/`): One file per SQLAlchemy model. Imported through
  `models/__init__.py` for convenience.
- **Schemas** (`app/schemas/`): One file per domain for Pydantic models.
  Follows the naming `XCreate`, `XUpdate`, `XOut`.

---

## Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Python files | `snake_case.py` | `chapter_content.py`, `error_handler.py` |
| Classes (models) | `PascalCase` | `class WorldFactClaim(Base)` |
| Classes (services) | `PascalCase + Service` | `class WorkspaceBootstrapService` |
| Functions/variables | `snake_case` | `def create_project()` |
| API router prefix | `/api/v1/<resource>` | `/api/v1/projects` |
| Test files | `test_<module>.py` | `test_projects.py` |
| Alembic revision | `<revision>_<description>.py` | `05ffa48c7449_add_versions_table.py` |

---

## Key Patterns

- **Router registration**: All routers registered in `main.py` with explicit
  `app.include_router(projects.router)` calls — no auto-discovery.
- **DB session**: Injected via `Depends(get_db)` in route functions.
- **Service injection**: Constructor-based `def __init__(self, db: Session)`.
- **Model imports**: Central barrel file `models/__init__.py` re-exports all models.
