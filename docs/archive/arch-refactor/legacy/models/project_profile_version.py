import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DDL,
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    event,
    select,
)

from app.db import Base
from app.models.genre_profile import GenreProfile


class ProjectProfileVersion(Base):
    __tablename__ = "project_profile_versions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_project_profile_versions_version_gte_1"),
        UniqueConstraint("project_id", "version", name="uq_project_profile_versions_project_version"),
        UniqueConstraint("project_id", "id", name="uq_project_profile_versions_project_id_id"),
        Index("ix_project_profile_versions_project_version", "project_id", "version"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    genre_profile_id = Column(String, ForeignKey("genre_profiles.id"), nullable=False)
    version = Column(Integer, nullable=False)
    contract_version = Column(String, nullable=False)
    profile_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


@event.listens_for(ProjectProfileVersion, "before_insert")
def validate_project_profile_version_contract(mapper, connection, target):
    expected_contract_version = connection.execute(
        select(GenreProfile.contract_version).where(GenreProfile.id == target.genre_profile_id)
    ).scalar_one_or_none()
    if expected_contract_version is None:
        return
    if target.contract_version != expected_contract_version:
        raise ValueError(
            "ProjectProfileVersion.contract_version must match "
            f"genre_profile.contract_version: expected {expected_contract_version}, got {target.contract_version}"
        )


@event.listens_for(ProjectProfileVersion, "before_update")
def prevent_project_profile_version_updates(mapper, connection, target):
    raise ValueError("ProjectProfileVersion is append-only and cannot be updated")


@event.listens_for(ProjectProfileVersion, "before_delete")
def prevent_project_profile_version_deletes(mapper, connection, target):
    raise ValueError("ProjectProfileVersion is append-only and cannot be deleted")


_project_profile_version_append_only_update_trigger = DDL(
    """
    CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_append_only
    BEFORE UPDATE ON project_profile_versions
    BEGIN
        SELECT RAISE(ABORT, 'project_profile_versions is append-only');
    END;
    """
)

_project_profile_version_contract_version_insert_trigger = DDL(
    """
    CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_contract_version_insert
    BEFORE INSERT ON project_profile_versions
    WHEN EXISTS (
        SELECT 1
        FROM genre_profiles
        WHERE id = NEW.genre_profile_id
          AND contract_version <> NEW.contract_version
    )
    BEGIN
        SELECT RAISE(ABORT, 'project_profile_versions contract_version mismatch');
    END;
    """
)

_project_profile_version_append_only_delete_trigger = DDL(
    """
    CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_append_only_delete
    BEFORE DELETE ON project_profile_versions
    BEGIN
        SELECT RAISE(ABORT, 'project_profile_versions is append-only');
    END;
    """
)

_drop_project_profile_version_append_only_update_trigger = DDL(
    "DROP TRIGGER IF EXISTS trg_project_profile_versions_append_only"
)
_drop_project_profile_version_contract_version_insert_trigger = DDL(
    "DROP TRIGGER IF EXISTS trg_project_profile_versions_contract_version_insert"
)
_drop_project_profile_version_append_only_delete_trigger = DDL(
    "DROP TRIGGER IF EXISTS trg_project_profile_versions_append_only_delete"
)

event.listen(
    ProjectProfileVersion.__table__,
    "after_create",
    _project_profile_version_contract_version_insert_trigger.execute_if(dialect="sqlite"),
)
event.listen(
    ProjectProfileVersion.__table__,
    "after_create",
    _project_profile_version_append_only_update_trigger.execute_if(dialect="sqlite"),
)
event.listen(
    ProjectProfileVersion.__table__,
    "after_create",
    _project_profile_version_append_only_delete_trigger.execute_if(dialect="sqlite"),
)
event.listen(
    ProjectProfileVersion.__table__,
    "before_drop",
    _drop_project_profile_version_contract_version_insert_trigger.execute_if(dialect="sqlite"),
)
event.listen(
    ProjectProfileVersion.__table__,
    "before_drop",
    _drop_project_profile_version_append_only_update_trigger.execute_if(dialect="sqlite"),
)
event.listen(
    ProjectProfileVersion.__table__,
    "before_drop",
    _drop_project_profile_version_append_only_delete_trigger.execute_if(dialect="sqlite"),
)
