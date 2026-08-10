# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

- **ORM**: SQLAlchemy 2.0.36 with `declarative_base()`
- **Database**: SQLite (default `data/mozhou.db`), WAL mode
- **Migrations**: Alembic 1.14.0
- **Connection**: Single engine per process, session-per-request via `Depends(get_db)`

Configuration lives in `app/db.py` and `app/core/database_url.py`.
The database URL can be overridden via `MOZHOU_DATABASE_URL` env var.

---

## Engine & Session Setup

```python
# app/db.py
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

**`autoflush=False` means same-transaction read-after-write needs explicit `db.flush()`**:
mutating an ORM instance and then querying for it in the same transaction (before commit)
will NOT see the pending change. Call `db.flush()` before the dependent query — flush is
cheap and idempotent. (Verified: plotline `reopen → status=open` then `postpone` lookup
missed in tests; production sessions share this config.)

SQLite PRAGMAs set on every connection:

```python
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")   # 30s
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
```

---

## ORM Model Patterns

```python
class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    genre = Column(String, nullable=True)
    metadata_dict = Column("metadata", JSON, default=dict)  # SQLite-compatible JSON
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
```

**Rules**:

- All models inherit from `app.db.Base` (one `declarative_base()`)
- Primary keys are `String` UUIDs via `str(uuid.uuid4())`
- Table names are `snake_case` plural (e.g., `chapter_contents`, `world_fact_claims`)
- JSON fields use `Column(JSON, default=dict)` — SQLite stores these as TEXT
- Timestamps use `datetime.now(UTC)` with `onupdate` for `updated_at`
- `nullable=False` for required columns, `nullable=True` (default) for optional

---

## Query Patterns

### Simple queries in API routes

```python
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    result = db.query(Project).filter(Project.id == project_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="not found")
    return result
```

### Pagination pattern

```python
items = db.query(Model).filter(Model.project_id == pid)
    .order_by(Model.created_at.desc())
    .offset(payload.offset)
    .limit(payload.limit + 1)       # fetch one extra for has_more
    .all()
has_more = len(items) > payload.limit
items = items[:payload.limit]
```

### Relationships — cascade delete via centralized registry in `models/`

```python
class ChapterContent(Base):
    __tablename__ = "chapter_contents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="chapters")
```

---

## Migrations (Alembic)

### Creating a migration

```bash
cd backend
alembic revision -m "add_my_new_table"
```

### Migration file pattern

```python
"""add my new table

Revision ID: xxxx
Revises: previous_revision_id
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        "my_table",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )

def downgrade():
    op.drop_table("my_table")
```

**Conventions**:
- Revision ID: either a hash like `05ffa48c7449` or date prefix like `20260424`
- `depends_on` used only when strict ordering is required
- All existing migrations in `backend/alembic/versions/`

---

## Common Mistakes

1. **Forgetting `onupdate` for `updated_at`** — the column won't auto-update on row modification.
2. **Missing `nullable=False` on required columns** — SQLite allows NULL by default.
3. **Using `default=` on JSON columns with mutable values** — use `default=dict` (callable), not `default={}`.
4. **Forgetting `str()` wrapping on UUID** — `Column(String)` expects a string, not a `uuid.UUID` object.
5. **SQLite busy errors under concurrent writes** — WAL mode + 30s busy_timeout mitigates this.
