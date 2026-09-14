from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class RequestStatus(StrEnum):
    """Заявка: «подана» → «обработана» (EL-15); DB stores lowercase English codes
    (database.md §2), Russian labels live at the API edge."""

    SUBMITTED = "submitted"
    PROCESSED = "processed"

class StoreRequest(Base):
    __tablename__ = "store_request"
    __table_args__ = (
        CheckConstraint("requested_quantity > 0", name="requested_quantity_positive"),
        CheckConstraint("status IN ('submitted', 'processed')", name="store_request_status_valid"),
        CheckConstraint(
            "(status = 'submitted' AND processed_at IS NULL) "
            "OR (status = 'processed' AND processed_at IS NOT NULL)",
            name="store_request_status_date_consistent",
        )
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    number: Mapped[int] = mapped_column(BigInteger, server_default = text("nextval('store_request_number_seq')"), nullable=False, unique = True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"), nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("store.id"), nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class StoreProduct(Base):
    __tablename__ = "store_product"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        PrimaryKeyConstraint("store_id", "product_id"),
    )

    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("store.id"),nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
