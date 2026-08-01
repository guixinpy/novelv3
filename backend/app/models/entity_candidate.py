import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.db import Base


class EntityCandidate(Base):
    """正文规则提取 / L2 深查产生的候选实体（实体登记来源扩展）。

    rule 来源需跨 ≥2 章出现（chapter_count ≥ 2）才转正进入 _capture_entities 白名单；
    l2 来源（LLM 提取）免转正。
    """

    __tablename__ = "entity_candidates"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_entity_candidates_project_name"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    source = Column(String, default="rule")  # rule | l2
    first_chapter = Column(Integer, nullable=True)
    last_chapter = Column(Integer, nullable=True)
    chapter_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
