"""stock_event table (Phase 2: event history — ML ground truth).

Append-only journal fed by FR-5 (receipt) and FR-9 (shipment) in the same
transaction (ADR-0006 decisions Q1–Q3: one table; store_id NULL for receipts;
request_number snapshot; no deleted_at — events are eternal).
Index (occurred_at, product_id) serves the future forecasting dataset query.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "stock_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("store_id", sa.BigInteger(), sa.ForeignKey("store.id"), nullable=True),
        sa.Column("request_number", sa.BigInteger(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="stock_event_pkey"),
        sa.CheckConstraint("quantity > 0", name="event_quantity_positive"),
        sa.CheckConstraint(
            "event_type IN ('receipt', 'shipment')", name="event_type_valid"
        ),
    )
    # Serves the future ML dataset read: a product's event timeline.
    op.create_index(
        "stock_event_product_time_idx",
        "stock_event",
        ["occurred_at", "product_id"],
    )


def downgrade() -> None:
    op.drop_index("stock_event_product_time_idx", table_name="stock_event")
    op.drop_table("stock_event")