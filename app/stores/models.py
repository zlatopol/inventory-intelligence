from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class Store(Base):
    """Магазин из списка магазинов (database.md §2; soft delete per ADR-0005)."""

    __tablename__ = "store"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Note: the case-insensitive unique index over live rows (store_live_name_key,
    # BR-4 + ADR-0004/0005) is created by migration 0002 — see migrations/versions/.