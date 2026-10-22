"""Append-only stock movement journal shared by receipts, shipments and sales."""
from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, Text, func, text
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class StockEvent(Base):
    __tablename__ = "stock_event"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="event_quantity_positive"),
        CheckConstraint(
            "event_type IN ('receipt', 'shipment', 'sale', 'sale_reversal')",
            name="event_type_valid",
        ),
        CheckConstraint(
            "(event_type IN ('receipt', 'shipment') AND sold_at IS NULL) OR "
            "(event_type = 'sale' AND sold_at IS NOT NULL AND store_id IS NOT NULL) OR "
            "(event_type = 'sale_reversal' AND sold_at IS NULL AND store_id IS NOT NULL "
            "AND reversal_of_event_id IS NOT NULL)",
            name="event_sale_fields_consistent",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=False
    )
    store_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("store.id"), nullable=True
    )
    request_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversal_of_event_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stock_event.id"), nullable=True
    )

    @property
    def created_at(self) -> datetime:
        """Backward-compatible API name for the immutable event registration time."""
        return self.occurred_at
