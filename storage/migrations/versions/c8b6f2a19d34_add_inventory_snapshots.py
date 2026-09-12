"""add inventory snapshots

Revision ID: c8b6f2a19d34
Revises: 7ad585bfaa5d
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8b6f2a19d34"
down_revision: Union[str, Sequence[str], None] = "7ad585bfaa5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("camera_id", sa.String(length=60), nullable=False),
        sa.Column("products_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_snapshots_camera_id"),
        "inventory_snapshots",
        ["camera_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_snapshots_timestamp"),
        "inventory_snapshots",
        ["timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_snapshots_timestamp"), table_name="inventory_snapshots")
    op.drop_index(op.f("ix_inventory_snapshots_camera_id"), table_name="inventory_snapshots")
    op.drop_table("inventory_snapshots")
