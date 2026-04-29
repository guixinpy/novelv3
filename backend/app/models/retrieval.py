import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.db import Base


class RetrievalDocument(Base):
    __tablename__ = "retrieval_documents"
    __table_args__ = (
        UniqueConstraint("project_id", "source_type", "source_id", name="uq_retrieval_documents_source"),
        Index("ix_retrieval_documents_project_source_type", "project_id", "source_type"),
        Index("ix_retrieval_documents_project_chapter", "project_id", "chapter_index"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    source_ref = Column(String, nullable=False)
    title = Column(String, default="")
    chapter_index = Column(Integer, nullable=True)
    profile_version = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=False)
    document_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class RetrievalChunk(Base):
    __tablename__ = "retrieval_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_retrieval_chunks_document_chunk"),
        Index("ix_retrieval_chunks_project", "project_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    document_id = Column(String, ForeignKey("retrieval_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    start_offset = Column(Integer, default=0)
    end_offset = Column(Integer, default=0)
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class RetrievalTerm(Base):
    __tablename__ = "retrieval_terms"
    __table_args__ = (
        UniqueConstraint("project_id", "chunk_id", "token", name="uq_retrieval_terms_project_chunk_token"),
        Index("ix_retrieval_terms_project_token", "project_id", "token"),
        Index("ix_retrieval_terms_chunk", "chunk_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chunk_id = Column(String, ForeignKey("retrieval_chunks.id"), nullable=False)
    token = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class RetrievalEmbedding(Base):
    __tablename__ = "retrieval_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "provider", "model", name="uq_retrieval_embeddings_chunk_provider"),
        Index("ix_retrieval_embeddings_project_provider", "project_id", "provider", "model"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chunk_id = Column(String, ForeignKey("retrieval_chunks.id"), nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    dimensions = Column(Integer, nullable=False)
    vector = Column(JSON, nullable=False)
    vector_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
