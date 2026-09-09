from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class Product(Base):
    """Товар складского списка (database.md §2; soft delete per ADR-0005)."""

    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint("warehouse_quantity >= 0", name="product_warehouse_quantity_nonnegative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    warehouse_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Note: the case-insensitive unique index over live rows (product_live_name_key,
    # BR-2 + ADR-0004/0005) is created by migration 0001 — see migrations/versions/.
