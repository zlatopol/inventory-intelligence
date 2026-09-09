"""product table (slice 1)

FR-1/FR-2/FR-5/FR-6; BR-2 uniqueness among live rows (ADR-0004 + ADR-0005);
warehouse_quantity >= 0 CHECK (database.md §2).

Revision ID: 0001
Revises:
Create Date: 2026-09-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("warehouse_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="product_pkey"),
        sa.CheckConstraint(
            "warehouse_quantity >= 0", name="product_warehouse_quantity_nonnegative"
        ),
    )
    # BR-2 among live rows only: a soft-deleted name may be re-created (ADR-0005).
    op.create_index(
        "product_live_name_key",
        "product",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("product_live_name_key", table_name="product")
    op.drop_table("product")
