"""app_datasets — Knowledge per-App 归属表 (Step 8.15)

Revision ID: a1b2c3d4e5f6
Revises: e8718d7f606c
Create Date: 2026-04-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e8718d7f606c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_datasets",
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["app_id"], ["apps.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_index("ix_app_datasets_app", "app_datasets", ["app_id"])


def downgrade() -> None:
    op.drop_index("ix_app_datasets_app", table_name="app_datasets")
    op.drop_table("app_datasets")
