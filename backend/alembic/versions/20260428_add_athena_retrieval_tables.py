"""add athena retrieval tables

Revision ID: 20260428_add_athena_retrieval_tables
Revises: 20260424_add_revision_version_links
Create Date: 2026-04-28 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260428_add_athena_retrieval_tables"
down_revision: str | None = "20260424_add_revision_version_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_ref", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("document_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "source_type", "source_id", name="uq_retrieval_documents_source"),
    )
    op.create_index(
        "ix_retrieval_documents_project_source_type",
        "retrieval_documents",
        ["project_id", "source_type"],
    )
    op.create_index(
        "ix_retrieval_documents_project_chapter",
        "retrieval_documents",
        ["project_id", "chapter_index"],
    )

    op.create_table(
        "retrieval_chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("chunk_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["retrieval_documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_retrieval_chunks_document_chunk"),
    )
    op.create_index("ix_retrieval_chunks_project", "retrieval_chunks", ["project_id"])

    op.create_table(
        "retrieval_embeddings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("vector_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["retrieval_chunks.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "provider", "model", name="uq_retrieval_embeddings_chunk_provider"),
    )
    op.create_index(
        "ix_retrieval_embeddings_project_provider",
        "retrieval_embeddings",
        ["project_id", "provider", "model"],
    )


def downgrade() -> None:
    op.drop_index("ix_retrieval_embeddings_project_provider", table_name="retrieval_embeddings")
    op.drop_table("retrieval_embeddings")
    op.drop_index("ix_retrieval_chunks_project", table_name="retrieval_chunks")
    op.drop_table("retrieval_chunks")
    op.drop_index("ix_retrieval_documents_project_chapter", table_name="retrieval_documents")
    op.drop_index("ix_retrieval_documents_project_source_type", table_name="retrieval_documents")
    op.drop_table("retrieval_documents")
