"""Integration tests: RequestService FR-9 against real PostgreSQL — atomicity.

Atomicity is asserted by OBSERVABLE STATE after rejections, read fresh
(expire_all) so the identity map cannot mask what is actually stored.
"""
from datetime import UTC

import pytest

from app.products.models import Product
from app.products.repository import ProductRepository
from app.requests.models import RequestStatus, StoreRequest
from app.requests.repository import StoreRequestRepository
from app.requests.service import RequestService
from app.shared.errors import InsufficientStockError
from app.stores.models import Store
from app.stores.repository import StoreRepository


def make_service(db_session) -> RequestService:
    return RequestService(
        StoreRequestRepository(db_session),
        ProductRepository(db_session),
        StoreRepository(db_session),
        db_session,
    )


def seed(db_session, warehouse_quantity: int = 10):
    product = Product(name="Сахар", warehouse_quantity=warehouse_quantity)
    store = Store(name="Магнит")
    db_session.add_all([product, store])
    db_session.commit()
    return product, store


def submit(db_session, product, store, quantity: int) -> StoreRequest:
    return make_service(db_session).submit_request("Магнит", "Сахар", quantity)


def snapshot(db_session, product, store, request):
    """Fresh read of the three FR-9 observables (D2: identity map bypassed)."""
    db_session.expire_all()
    stock = db_session.get(Product, product.id).warehouse_quantity
    row = StoreRequestRepository(db_session).get_store_product(store.id, product.id)
    fresh_request = db_session.get(StoreRequest, request.id)
    return stock, (row.quantity if row else 0), fresh_request.status


def test_br7_rejection_leaves_no_trace(db_session):
    """BR-7 отказ: склад, остаток магазина и статус — всё нетронуто."""
    product, store = seed(db_session, warehouse_quantity=3)
    request = submit(db_session, product, store, quantity=5)  # 5 > 3

    with pytest.raises(InsufficientStockError):
        make_service(db_session).process_request(request.number)

    stock, store_qty, status = snapshot(db_session, product, store, request)
    assert (stock, store_qty, status) == (3, 0, RequestStatus.SUBMITTED)


def test_first_processed_second_failed_is_isolated(db_session):
    """Успех №1 не мешает отказу №2 — и следы успеха остаются точными."""
    product, store = seed(db_session, warehouse_quantity=5)
    first = submit(db_session, product, store, quantity=3)  # влезает
    second = submit(db_session, product, store, quantity=4)  # остатка 2 не хватит

    make_service(db_session).process_request(first.number)
    with pytest.raises(InsufficientStockError):
        make_service(db_session).process_request(second.number)

    stock, store_qty, status1 = snapshot(db_session, product, store, first)
    _, _, status2 = snapshot(db_session, product, store, second)
    assert (stock, store_qty, status1) == (2, 3, RequestStatus.PROCESSED)
    assert status2 == RequestStatus.SUBMITTED


def test_full_flow_updates_all_three_observables(db_session):
    product, store = seed(db_session, warehouse_quantity=10)
    request = submit(db_session, product, store, quantity=5)

    processed = make_service(db_session).process_request(request.number)

    stock, store_qty, status = snapshot(db_session, product, store, request)
    assert (stock, store_qty, status) == (5, 5, RequestStatus.PROCESSED)
    assert processed.processed_at is not None  # A-3
    # psycopg returns timestamptz as ZoneInfo("Etc/UTC") — same zone as
    # timezone.utc but a different object; assert the SEMANTICS (zero offset).
    assert processed.processed_at.utcoffset().total_seconds() == 0
