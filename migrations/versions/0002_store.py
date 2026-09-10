"""store table (slice 2)

FR-3/FR-4; BR-4 uniqueness among live rows (ADR-0004 + ADR-0005);
mirrors 0001 (product). See docs/database.md §2.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="store_pkey"),
    )
    # BR-4 among live rows only: a soft-deleted name may be re-created (ADR-0005).
    op.create_index(
        "store_live_name_key",
        "store",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("store_live_name_key", table_name="store")
    op.drop_table("store")
