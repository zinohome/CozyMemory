"""api_usage — per-App API 用量表 (Step 8.16)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("route", sa.String(100), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_api_usage_app_time", "api_usage", ["app_id", "created_at"]
    )
    op.create_index("ix_api_usage_route", "api_usage", ["route"])
    # 若 migration 由 superuser 执行（如 1panel / docker-entry），runtime 用户
    # 默认没 DML 权限；显式 GRANT 幂等，runtime-self 情况下是 no-op。
    op.execute("GRANT ALL ON api_usage TO cozymemory_user")


def downgrade() -> None:
    op.drop_index("ix_api_usage_route", table_name="api_usage")
    op.drop_index("ix_api_usage_app_time", table_name="api_usage")
    op.drop_table("api_usage")
