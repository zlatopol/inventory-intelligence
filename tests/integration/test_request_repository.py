"""Integration tests: StoreRequestRepository against real PostgreSQL (slice 3)."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.products.models import Product
from app.requests.models import RequestStatus, StoreProduct, StoreRequest
from app.requests.repository import StoreRequestRepository
from app.stores.models import Store


@pytest.fixture
def trio(db_session):
    product = Product(name="Сахар", warehouse_quantity=10)
    store = Store(name="Магнит")
    db_session.add_all([product, store])
    db_session.flush()
    return product, store


def make_request_row(
    product: Product,
    store: Store,
    number: int | None = None,
    quantity: int = 5,
    status: RequestStatus = RequestStatus.SUBMITTED,
) -> StoreRequest:
    kwargs: dict = {
        "status": status,
        "product_id": product.id,
        "store_id": store.id,
        "requested_quantity": quantity,
        "submitted_at": datetime.now(UTC),
    }
    if number is not None:
        kwargs["number"] = number
    if status == RequestStatus.PROCESSED:
        kwargs["processed_at"] = datetime.now(UTC)  # статус⇔дата CHECK
    return StoreRequest(**kwargs)


def test_get_with_names_resolves_names(db_session, trio):
    product, store = trio
    repo = StoreRequestRepository(db_session)
    request = repo.add(make_request_row(product, store))
    db_session.flush()  # sequence assigns the number here

    row = repo.get_with_names(request.number)

    assert row is not None
    entity, store_name, product_name = row
    assert store_name == "Магнит"
    assert product_name == "Сахар"
    assert entity.number == request.number


def test_has_pending_for_store_distinguishes_status(db_session, trio):
    product, store = trio
    repo = StoreRequestRepository(db_session)

    repo.add(make_request_row(product, store, status=RequestStatus.PROCESSED))
    db_session.flush()
    assert repo.has_pending_for_store(store.id) is False  # обработанные не считаются

    repo.add(make_request_row(product, store))  # submitted
    db_session.flush()
    assert repo.has_pending_for_store(store.id) is True  # BR-8 guard


def test_list_all_with_names_orders_by_number(db_session, trio):
    product, store = trio
    repo = StoreRequestRepository(db_session)
    for n in (3, 1, 2):
        repo.add(make_request_row(product, store, number=n))
    db_session.flush()
    db_session.expire_all()

    numbers = [row[0].number for row in repo.list_all_with_names()]

    assert numbers == [1, 2, 3]  # FR-10 ordering


def test_increase_store_stock_creates_then_increases(db_session, trio):
    product, store = trio
    repo = StoreRequestRepository(db_session)

    repo.increase_store_stock(store.id, product.id, 3)
    db_session.flush()
    repo.increase_store_stock(store.id, product.id, 4)
    db_session.commit()
    db_session.expire_all()  # fresh read — no identity-map illusions

    rows = db_session.scalars(
        select(StoreProduct).where(
            StoreProduct.store_id == store.id,
            StoreProduct.product_id == product.id,
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].quantity == 7  # 3 + 4 in a single row (FR-9 upsert semantics)
