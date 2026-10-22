"""Support manual sales and reversals in the existing stock-event journal.

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_event", sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stock_event", sa.Column("idempotency_key", sa.Text(), nullable=True))
    op.add_column(
        "stock_event",
        sa.Column("reversal_of_event_id", sa.BigInteger(), sa.ForeignKey("stock_event.id"), nullable=True),
    )
    op.drop_constraint("event_type_valid", "stock_event", type_="check")
    op.create_check_constraint(
        "event_type_valid",
        "stock_event",
        "event_type IN ('receipt', 'shipment', 'sale', 'sale_reversal')",
    )
    op.create_check_constraint(
        "event_sale_fields_consistent",
        "stock_event",
        "(event_type IN ('receipt', 'shipment') AND sold_at IS NULL) OR "
        "(event_type = 'sale' AND sold_at IS NOT NULL AND store_id IS NOT NULL) OR "
        "(event_type = 'sale_reversal' AND sold_at IS NULL AND store_id IS NOT NULL "
        "AND reversal_of_event_id IS NOT NULL)",
    )
    op.create_index(
        "stock_event_idempotency_key_uq",
        "stock_event",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "stock_event_sale_reversal_uq",
        "stock_event",
        ["reversal_of_event_id"],
        unique=True,
        postgresql_where=sa.text("event_type = 'sale_reversal'"),
    )
    op.create_index(
        "stock_event_sale_history_idx",
        "stock_event",
        ["sold_at", "store_id", "product_id"],
        postgresql_where=sa.text("event_type = 'sale'"),
    )


def downgrade() -> None:
    op.drop_index("stock_event_sale_history_idx", table_name="stock_event")
    op.drop_index("stock_event_sale_reversal_uq", table_name="stock_event")
    op.drop_index("stock_event_idempotency_key_uq", table_name="stock_event")
    op.drop_constraint("event_sale_fields_consistent", "stock_event", type_="check")
    op.drop_constraint("event_type_valid", "stock_event", type_="check")
    op.create_check_constraint(
        "event_type_valid", "stock_event", "event_type IN ('receipt', 'shipment')"
    )
    op.drop_column("stock_event", "reversal_of_event_id")
    op.drop_column("stock_event", "idempotency_key")
    op.drop_column("stock_event", "sold_at")
