from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.events.models import StockEvent
from app.sales.repository import SaleRepository
from app.shared.errors import (
    IdempotencyConflictError,
    InvalidSaleQuantityError,
    ProductNotFoundError,
    SaleAlreadyReversedError,
    SaleNotFoundError,
    StoreNotFoundError,
    InsufficientStoreStockError,
)


def _positive_integer(value: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


class SaleService:
    def __init__(self, repository: SaleRepository, session: Session) -> None:
        self._repo = repository
        self._session = session

    def register_sale(
        self, store_id: int, product_id: int, quantity: int,
        sold_at: datetime, idempotency_key: str,
    ) -> StockEvent:
        if not _positive_integer(quantity):
            raise InvalidSaleQuantityError()
        if not idempotency_key.strip():
            raise IdempotencyConflictError()

        previous = self._repo.get_by_idempotency_key(idempotency_key)
        if previous is not None:
            if (
                previous.event_type == "sale"
                and previous.store_id == store_id
                and previous.product_id == product_id
                and previous.quantity == quantity
                and previous.sold_at == sold_at
            ):
                return previous
            raise IdempotencyConflictError()

        store = self._repo.get_live_store(store_id)
        if store is None:
            raise StoreNotFoundError()
        product = self._repo.get_live_product(product_id)
        if product is None:
            raise ProductNotFoundError()

        stock = self._repo.get_stock_for_update(store_id, product_id)
        if stock is None or stock.quantity < quantity:
            raise InsufficientStoreStockError()

        event = StockEvent(
            event_type="sale",
            product_id=product_id,
            store_id=store_id,
            request_number=None,
            quantity=quantity,
            sold_at=sold_at,
            idempotency_key=idempotency_key,
        )
        stock.quantity -= quantity
        if stock.quantity == 0:
            self._repo.delete_stock(stock)
        self._repo.add_event(event)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            previous = self._repo.get_by_idempotency_key(idempotency_key)
            if previous is not None:
                return previous
            raise
        return event

    def reverse_sale(self, sale_id: int) -> tuple[StockEvent, int]:
        sale = self._repo.get_event(sale_id)
        if sale is None or sale.event_type != "sale":
            raise SaleNotFoundError()
        if self._repo.get_reversal_for(sale_id) is not None:
            raise SaleAlreadyReversedError()

        stock = self._repo.get_stock_for_update(sale.store_id, sale.product_id)

        reversal = StockEvent(
            event_type="sale_reversal",
            product_id=sale.product_id,
            store_id=sale.store_id,
            request_number=None,
            quantity=sale.quantity,
            reversal_of_event_id=sale.id,
            sold_at=None,
        )
        if stock is None:
            stock = self._repo.add_stock(sale.store_id, sale.product_id, sale.quantity)
        else:
            stock.quantity += sale.quantity
        self._repo.add_event(reversal)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            if self._repo.get_reversal_for(sale_id) is not None:
                raise SaleAlreadyReversedError()
            raise
        return reversal, stock.quantity

    def list_sales(self, **filters):
        return self._repo.list_sales(**filters)
