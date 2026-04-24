import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db import Base


class WorldTimelineAnchor(Base):
    __tablename__ = "world_timeline_anchors"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "anchor_id",
            name="uq_world_timeline_anchors_project_profile_anchor_id",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_timeline_anchors_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_timeline_anchors_anchor_id", "anchor_id"),
        Index("ix_world_timeline_anchors_chapter_seq", "chapter_index", "intra_chapter_seq"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    anchor_id = Column(String, nullable=False)
    chapter_index = Column(Integer, nullable=True)
    intra_chapter_seq = Column(Integer, nullable=False)
    world_time_label = Column(String, default="")
    normalized_tick_or_range = Column(String, default="")
    precision = Column(String, default="")
    relative_to_anchor_ref = Column(String, nullable=True)
    ordering_key = Column(String, nullable=False)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
