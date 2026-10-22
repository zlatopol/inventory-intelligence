from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import StockEvent
from app.products.models import Product
from app.requests.models import StoreProduct
from app.stores.models import Store


class SaleRepository:
    """Queries for sale events and store stock; transaction owned by service."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_live_store(self, store_id: int) -> Store | None:
        return self._session.scalars(
            select(Store).where(Store.id == store_id, Store.deleted_at.is_(None))
        ).first()

    def get_live_product(self, product_id: int) -> Product | None:
        return self._session.scalars(
            select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
        ).first()

    def get_stock_for_update(self, store_id: int, product_id: int) -> StoreProduct | None:
        stmt = (
            select(StoreProduct)
            .where(StoreProduct.store_id == store_id, StoreProduct.product_id == product_id)
            .with_for_update()
        )
        return self._session.scalars(stmt).first()

    def get_event(self, event_id: int) -> StockEvent | None:
        return self._session.get(StockEvent, event_id)

    def get_by_idempotency_key(self, key: str) -> StockEvent | None:
        return self._session.scalars(
            select(StockEvent).where(StockEvent.idempotency_key == key)
        ).first()

    def get_reversal_for(self, sale_id: int) -> StockEvent | None:
        return self._session.scalars(
            select(StockEvent).where(
                StockEvent.event_type == "sale_reversal",
                StockEvent.reversal_of_event_id == sale_id,
            )
        ).first()

    def add_event(self, event: StockEvent) -> StockEvent:
        self._session.add(event)
        return event

    def list_sales(
        self,
        store_id: int | None = None,
        product_id: int | None = None,
        sold_from: datetime | None = None,
        sold_to: datetime | None = None,
        status: str = "all",
    ) -> Sequence[tuple[StockEvent, str, str, int | None]]:
        sale = StockEvent
        reversal = StockEvent.__table__.alias("reversal")
        stmt = (
            select(sale, Store.name, Product.name, reversal.c.id)
            .join(Store, Store.id == sale.store_id)
            .join(Product, Product.id == sale.product_id)
            .outerjoin(
                reversal,
                (reversal.c.event_type == "sale_reversal")
                & (reversal.c.reversal_of_event_id == sale.id),
            )
            .where(sale.event_type == "sale")
        )
        if store_id is not None:
            stmt = stmt.where(sale.store_id == store_id)
        if product_id is not None:
            stmt = stmt.where(sale.product_id == product_id)
        if sold_from is not None:
            stmt = stmt.where(sale.sold_at >= sold_from)
        if sold_to is not None:
            stmt = stmt.where(sale.sold_at <= sold_to)
        if status == "active":
            stmt = stmt.where(reversal.c.id.is_(None))
        elif status == "cancelled":
            stmt = stmt.where(reversal.c.id.is_not(None))
        return self._session.execute(stmt.order_by(sale.sold_at.desc(), sale.id.desc())).all()
