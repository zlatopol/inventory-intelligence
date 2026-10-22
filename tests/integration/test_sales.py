from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.events.models import StockEvent
from app.products.models import Product
from app.requests.models import StoreProduct
from app.sales.repository import SaleRepository
from app.sales.service import SaleService
from app.shared.errors import (
    InsufficientStoreStockError,
    SaleAlreadyReversedError,
)


def setup_stock(session, quantity: int = 5):
    product = Product(name="Кофе", warehouse_quantity=0)
    store = Store(name="Магазин 1")
    session.add_all([product, store])
    session.flush()
    stock = StoreProduct(store_id=store.id, product_id=product.id, quantity=quantity)
    session.add(stock)
    session.commit()
    return product, store, stock


def service(session):
    return SaleService(SaleRepository(session), session)


def test_sale_decreases_stock_and_is_written_to_event_history(db_session):
    product, store, stock = setup_stock(db_session)
    sold_at = datetime.now(UTC) - timedelta(days=1)

    event = service(db_session).register_sale(
        store.id, product.id, 2, sold_at, "test-sale-key-1"
    )

    assert db_session.get(StoreProduct, (store.id, product.id)) is None
    assert event.event_type == "sale"
    assert event.sold_at == sold_at
    assert event.created_at is not None


def test_repeating_same_idempotency_key_does_not_deduct_twice(db_session):
    product, store, stock = setup_stock(db_session)
    sold_at = datetime.now(UTC)

    first = service(db_session).register_sale(
        store.id, product.id, 2, sold_at, "test-sale-key-2"
    )
    second = service(db_session).register_sale(
        store.id, product.id, 2, sold_at, "test-sale-key-2"
    )

    assert first.id == second.id
    assert stock.quantity == 3


def test_sale_rejects_quantity_above_current_stock(db_session):
    product, store, stock = setup_stock(db_session, quantity=1)

    with pytest.raises(InsufficientStoreStockError):
        service(db_session).register_sale(
            store.id, product.id, 2, datetime.now(UTC), "test-sale-key-3"
        )

    assert stock.quantity == 1
    assert db_session.scalars(select(StockEvent).where(StockEvent.event_type == "sale")).all() == []


def test_reversal_returns_quantity_and_can_only_happen_once(db_session):
    product, store, stock = setup_stock(db_session, quantity=5)
    sale = service(db_session).register_sale(
        store.id, product.id, 3, datetime.now(UTC), "test-sale-key-4"
    )

    reversal, resulting_stock = service(db_session).reverse_sale(sale.id)

    assert db_session.get(StoreProduct, (store.id, product.id)).quantity == 5
    assert resulting_stock == 5
    assert reversal.event_type == "sale_reversal"
    assert reversal.reversal_of_event_id == sale.id

    with pytest.raises(SaleAlreadyReversedError):
        service(db_session).reverse_sale(sale.id)

    assert stock.quantity == 5
