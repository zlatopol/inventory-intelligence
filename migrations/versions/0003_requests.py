from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE store_request_number_seq")
    op.create_table(
        "store_product",
        sa.Column("store_id", sa.BigInteger(), sa.ForeignKey("store.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("store_id", "product_id"),
        sa.CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        )
    )

    op.create_table(
        "store_request",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "number",
            sa.BigInteger(),
            server_default=sa.text("nextval('store_request_number_seq')"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("store_id", sa.BigInteger(), sa.ForeignKey("store.id"), nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="store_request_pkey"),
        sa.CheckConstraint(
            "requested_quantity > 0", name="requested_quantity_positive"
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'processed')", name="store_request_status_valid"
        ),
        sa.CheckConstraint(
            "(status = 'submitted' AND processed_at IS NULL) "
            "OR (status = 'processed' AND processed_at IS NOT NULL)",
            name="store_request_status_date_consistent",
        ),
    )

    op.create_index(
        "store_request_pending_store",
        "store_request",
        ["store_id"],
        postgresql_where=sa.text("status = 'submitted'"),
    )

def downgrade() -> None:
    op.drop_index(
        "store_request_pending_store",
        table_name="store_request",
    )
    op.drop_table("store_request")
    op.drop_table("store_product")
    op.execute("DROP SEQUENCE store_request_number_seq")