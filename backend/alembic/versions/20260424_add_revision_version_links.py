"""add revision version links

Revision ID: 20260424_add_revision_version_links
Revises: 20260424_add_chapter_revisions
Create Date: 2026-04-24 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260424_add_revision_version_links"
down_revision: str | None = "20260424_add_chapter_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chapter_revisions") as batch_op:
        batch_op.add_column(sa.Column("base_version_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("result_version_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_chapter_revisions_base_version_id_versions",
            "versions",
            ["base_version_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_chapter_revisions_result_version_id_versions",
            "versions",
            ["result_version_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("chapter_revisions") as batch_op:
        batch_op.drop_constraint("fk_chapter_revisions_result_version_id_versions", type_="foreignkey")
        batch_op.drop_constraint("fk_chapter_revisions_base_version_id_versions", type_="foreignkey")
        batch_op.drop_column("result_version_id")
        batch_op.drop_column("base_version_id")
