
"""Stock-event tests (Phase 2, test-first) — RED until slice implements events.

Design decisions fixed by these tests (to become ADR-0006):
- Q1: ONE append-only table; store_id is NULL for receipts («неприменимо»);
- Q2: shipment carries a request_number SNAPSHOT (event = witness of the past,
  EL-19 tradition), not an FK;
- Q3: append-only — no update/delete paths exist by design; occurred_at per A-3.
"""
import pytest
from sqlalchemy import select

from app.events.models import StockEvent
from app.products.models import Product
from app.products.repository import ProductRepository
from app.products.service import ProductService
from app.requests.models import RequestStatus, StoreProduct, StoreRequest
from app.requests.repository import StoreRequestRepository
from app.requests.service import RequestService
from app.shared.errors import InsufficientStockError
from app.stores.models import Store
from app.stores.repository import StoreRepository


def add_product(session, name: str, warehouse_quantity: int = 0) -> Product:
    product = Product(name=name, warehouse_quantity=warehouse_quantity)
    session.add(product)
    return product


def add_store(session, name: str) -> Store:
    store = Store(name=name)
    session.add(store)
    return store


def add_request(session, product: Product, store: Store, quantity: int) -> StoreRequest:
    request = StoreRequest(
        product_id=product.id,
        store_id=store.id,
        requested_quantity=quantity,
        status=RequestStatus.SUBMITTED,
    )
    session.add(request)
    return request


def make_product_service(session) -> ProductService:
    return ProductService(ProductRepository(session), session)


def make_request_service(session) -> RequestService:
    return RequestService(
        StoreRequestRepository(session),
        ProductRepository(session),
        StoreRepository(session),
        session,
    )


def test_receive_product_creates_receipt_event(db_session):
    # ARRANGE
    product = add_product(db_session, name="Сахар", warehouse_quantity=0)
    db_session.flush()

    # ACT
    make_product_service(db_session).receive_product(product.name, 10)

    # ASSERT
    event = db_session.execute(
        select(StockEvent).where(StockEvent.product_id == product.id)
    ).scalar_one()

    assert event.event_type == "receipt"
    assert event.quantity == 10
    assert event.product_id == product.id
    assert event.store_id is None  # Q1: «неприменимо» для поступления
    assert event.request_number is None  # Q2: только у отгрузки
    assert event.occurred_at is not None  # A-3
    assert product.warehouse_quantity == 10  # состояние обновлено вместе с событием


def test_process_request_creates_shipment_event_with_store_and_number(db_session):
    # ARRANGE
    product = add_product(db_session, name="Сахар", warehouse_quantity=20)
    store = add_store(db_session, name="Магнит")
    request = add_request(db_session, product, store, quantity=7)
    db_session.flush()  # sequence assigns request.number here

    # ACT
    make_request_service(db_session).process_request(request.number)

    # ASSERT
    event = db_session.execute(
        select(StockEvent).where(
            StockEvent.product_id == product.id,
            StockEvent.store_id == store.id,
            StockEvent.request_number == request.number,
        )
    ).scalar_one()

    assert event.event_type == "shipment"
    assert event.quantity == 7
    assert event.product_id == product.id
    assert event.store_id == store.id
    assert event.request_number == request.number  # Q2: снимок номера
    assert event.occurred_at is not None
    assert request.status == RequestStatus.PROCESSED
    assert request.processed_at is not None
    assert product.warehouse_quantity == 13

    store_product = db_session.execute(
        select(StoreProduct).where(
            StoreProduct.product_id == product.id,
            StoreProduct.store_id == store.id,
        )
    ).scalar_one()
    assert store_product.quantity == 7


def test_process_request_insufficient_stock_creates_no_event_and_changes_no_state(
    db_session,
):
    # ARRANGE
    product = add_product(db_session, name="Сахар", warehouse_quantity=5)
    store = add_store(db_session, name="Магнит")
    request = add_request(db_session, product, store, quantity=10)  # 10 > 5
    db_session.flush()

    # ACT
    with pytest.raises(InsufficientStockError):
        make_request_service(db_session).process_request(request.number)

    # ASSERT — атомарность: события нет и ничего не изменилось (EL-17)
    event = db_session.execute(
        select(StockEvent).where(
            StockEvent.product_id == product.id,
            StockEvent.store_id == store.id,
            StockEvent.request_number == request.number,
        )
    ).scalar_one_or_none()

    assert event is None  # отказ не пишет событий
    assert request.status == RequestStatus.SUBMITTED
    assert product.warehouse_quantity == 5
    assert request.processed_at is None
    assert (
        db_session.execute(
            select(StoreProduct).where(
                StoreProduct.product_id == product.id,
                StoreProduct.store_id == store.id,
            )
        ).scalar_one_or_none()
        is None
    )

