import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ChapterRevision(Base):
    __tablename__ = "chapter_revisions"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_id = Column(String, ForeignKey("chapter_contents.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    revision_index = Column(Integer, nullable=False)
    status = Column(String, default="draft")
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    base_version_id = Column(String, ForeignKey("versions.id"), nullable=True)
    result_version_id = Column(String, ForeignKey("versions.id"), nullable=True)


class RevisionAnnotation(Base):
    __tablename__ = "revision_annotations"

    id = Column(String, primary_key=True, default=_uuid)
    revision_id = Column(String, ForeignKey("chapter_revisions.id"), nullable=False)
    paragraph_index = Column(Integer, nullable=False)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    selected_text = Column(Text, nullable=False)
    comment = Column(Text, nullable=False)


class RevisionCorrection(Base):
    __tablename__ = "revision_corrections"

    id = Column(String, primary_key=True, default=_uuid)
    revision_id = Column(String, ForeignKey("chapter_revisions.id"), nullable=False)
    paragraph_index = Column(Integer, nullable=False)
    original_text = Column(Text, nullable=False)
    corrected_text = Column(Text, nullable=False)
