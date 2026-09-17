"""StockEvent — append-only event journal (Phase 2, ADR-0006 Q1–Q3).

One table for both flows: store_id is NULL for receipts («неприменимо»);
request_number is a snapshot, not an FK (an event is a witness of the past);
no deleted_at — events are never deleted or updated.
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class StockEvent(Base):
    __tablename__ = "stock_event"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="event_quantity_positive"),
        CheckConstraint(
            "event_type IN ('receipt', 'shipment')", name="event_type_valid"
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
