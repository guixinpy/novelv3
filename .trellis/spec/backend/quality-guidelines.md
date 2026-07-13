# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

- **Linter/Formatter**: Ruff (target Python 3.11, line length 120)
- **Test framework**: pytest 8.3.3 + pytest-asyncio 0.24.0
- **Type hints**: Required for all function signatures (Python 3.14 runtime)
- **No type checker in CI**: Type hints are documentation aids, not enforced by mypy/pyright

Configuration files: `backend/ruff.toml`, `backend/pytest.ini`.

---

## Ruff Configuration

```toml
# backend/ruff.toml
target-version = "py311"
line-length = 120
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "ARG"]
ignore = ["E501"]  # line-length handled by formatter
```

---

## Testing Requirements

### Test layout

```
backend/tests/
├── conftest.py           # Shared fixtures (client, db_session)
├── agent/                # Agent infrastructure tests
│   ├── test_harness.py
│   ├── test_loop.py
│   ├── test_tooling.py
│   └── ...
├── test_<module>.py      # Domain tests (flat structure)
└── ...

backend/test_support/     # Test helpers
├── agent_fakes.py
└── writing_agent_run_helpers.py
```

### Fixture pattern

```python
# backend/tests/conftest.py
@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database, rebuilt per test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = SessionLocal(bind=engine)
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
```

### Test conventions

| Aspect | Convention |
|--------|-----------|
| File naming | `test_<module>.py` |
| Function naming | `def test_<description>()` |
| Async tests | `async def test_<description>()` with `pytest-asyncio` |
| DB isolation | Each test gets a fresh in-memory SQLite DB |
| Fixture scope | `function` by default (per-test isolation) |
| Assertion style | Plain `assert` (no self.assert*) |
| Test data | Inline or via helper factories in `test_support/` |

### Fixture loop scope

```ini
# backend/pytest.ini
[pytest]
asyncio_default_fixture_loop_scope = function
```

---

## Required Patterns

- **Type annotations on all function signatures** — parameters and return types.
- **Docstrings on public functions** — brief description of what the function does.
- **Context managers for external resources** — use `with` or `async with`.
- **`model_dump()` for Pydantic serialization** — Pydantic v2 convention.

---

## Forbidden Patterns

1. **`print()` for debugging** — Use `log_event()` instead.
2. **Bare `except:`** — Always catch specific exception types.
3. **Mutable default arguments** — `def func(x=[])` is not allowed.
4. **`from module import *`** — Explicit imports only.
5. **Global mutable state** — Use dependency injection or service classes.
6. **`# type: ignore` without comment** — If needed, explain why.
7. **Circular imports between `core/` and `services/`** — Services depend on core, not vice versa.

---

## Code Review Checklist

- [ ] Type annotations on all function signatures
- [ ] No `print()` statements
- [ ] No bare `except:` blocks
- [ ] Error handling includes `AppError` or `HTTPException` with meaningful messages
- [ ] Database queries are scoped (filtered by project_id or similar)
- [ ] Migrations are reversible (have both `upgrade()` and `downgrade()`)
- [ ] New models are added to `models/__init__.py` barrel
- [ ] Test covers the happy path and at least one error case
