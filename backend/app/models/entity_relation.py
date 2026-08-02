import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint

from app.db import Base


class EntityRelation(Base):
    """实体共现关系边（openhuman 共现图，特化：存 (count, last_chapter) 双字段）。

    同章提取到的实体两两成对建边（entity_a < entity_b 字典序，保证无向唯一）；
    count = 共现章数，last_chapter = 最近一次共现的章节（时间衰减的依据）。
    """

    __tablename__ = "entity_relations"
    __table_args__ = (
        UniqueConstraint("project_id", "entity_a", "entity_b", name="uq_entity_relations_pair"),
        # related_entities 的 OR 查询两分支均需索引（code-review #15）
        Index("ix_entity_relations_project_b", "project_id", "entity_b"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    entity_a = Column(String, nullable=False)
    entity_b = Column(String, nullable=False)
    count = Column(Integer, default=1)
    last_chapter = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
