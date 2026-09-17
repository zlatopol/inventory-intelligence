"""Unit tests for RequestService (FR-8, FR-9, FR-10) — no database.

Canonical fixture trio: Store(id=1, «Магнит») × Product(id=1, «Сахар»,
warehouse_quantity=10) × request for 5 — one fixture covers both sides of BR-7
(5 fits into 10; with warehouse 3 it does not).
"""
from datetime import UTC, datetime

import pytest

from fakes import FakeSession

from app.products.models import Product
from app.requests.models import RequestStatus, StoreProduct, StoreRequest
from app.requests.service import RequestService
from app.shared.errors import (
    EmptyNameError,
    InsufficientStockError,
    InvalidRequestQuantityError,
    ProductNotFoundError,
    RequestAlreadyProcessedError,
    RequestNotFoundError,
    StoreNotFoundError,
)
from app.stores.models import Store


def make_product(quantity: int = 10, product_id: int = 1) -> Product:
    return Product(id=product_id, name="Сахар", warehouse_quantity=quantity)


def make_store(store_id: int = 1) -> Store:
    return Store(id=store_id, name="Магнит")


def make_request(
    number: int = 1,
    quantity: int = 5,
    store_id: int = 1,
    product_id: int = 1,
    status: RequestStatus = RequestStatus.SUBMITTED,
) -> StoreRequest:
    return StoreRequest(
        number=number,
        status=status,
        store_id=store_id,
        product_id=product_id,
        requested_quantity=quantity,
        submitted_at=datetime.now(UTC),
    )


class FakeProductRepo:
    def __init__(self, products: list[Product] | None = None) -> None:
        self.products = list(products or [])

    def find_live_by_name(self, name: str) -> Product | None:
        return next((p for p in self.products if p.name.lower() == name.lower()), None)

    def find_live_by_id(self, product_id: int) -> Product | None:
        return next((p for p in self.products if p.id == product_id), None)


class FakeStoreRepo:
    def __init__(self, stores: list[Store] | None = None) -> None:
        self.stores = list(stores or [])

    def find_live_by_name(self, name: str) -> Store | None:
        return next((s for s in self.stores if s.name.lower() == name.lower()), None)

    def find_live_by_id(self, store_id: int) -> Store | None:
        return next((s for s in self.stores if s.id == store_id), None)


class FakeRequestsRepo:
    """In-memory StoreRequestRepository double (incl. increase_store_stock upsert)."""

    def __init__(
        self,
        requests: list[StoreRequest] | None = None,
        store_products: list[StoreProduct] | None = None,
    ) -> None:
        self.requests = list(requests or [])
        self.store_products = list(store_products or [])

    def add(self, request: StoreRequest) -> StoreRequest:
        self.requests.append(request)
        return request

    def get_by_number(self, number: int) -> StoreRequest | None:
        return next((r for r in self.requests if r.number == number), None)

    def list_all_with_names(self):
        return [
            (r, "Магнит", "Сахар")
            for r in sorted(self.requests, key=lambda r: r.number)
        ]

    def get_with_names(self, number: int):
        r = self.get_by_number(number)
        return None if r is None else (r, "Магнит", "Сахар")

    def has_pending_for_store(self, store_id: int) -> bool:
        return any(
            r.store_id == store_id and r.status == RequestStatus.SUBMITTED
            for r in self.requests
        )

    def increase_store_stock(self, store_id: int, product_id: int, quantity: int):
        existing = next(
            (
                sp
                for sp in self.store_products
                if sp.store_id == store_id and sp.product_id == product_id
            ),
            None,
        )
        if existing is not None:
            existing.quantity += quantity
            return existing
        row = StoreProduct(store_id=store_id, product_id=product_id, quantity=quantity)
        self.store_products.append(row)
        return row


class FakeEventsRepo:
    """Stand-in for StockEventRepository — collects added events (append-only)."""

    def __init__(self) -> None:
        self.events: list = []

    def add(self, event) -> None:
        self.events.append(event)


def make_service(
    products: list[Product] | None = None,
    stores: list[Store] | None = None,
    requests: list[StoreRequest] | None = None,
    store_products: list[StoreProduct] | None = None,
    session: FakeSession | None = None,
):
    requests_repo = FakeRequestsRepo(requests, store_products)
    session = session or FakeSession()
    service = RequestService(
        requests_repo,
        FakeProductRepo(products),
        FakeStoreRepo(stores),
        FakeEventsRepo(),
        session,
    )
    return service, requests_repo, session  # type: ignore[arg-type]


# --- FR-8: submit -----------------------------------------------------------


def test_submit_creates_request_with_trimmed_names_and_submitted_status():
    service, requests_repo, session = make_service(
        products=[make_product()], stores=[make_store()]
    )

    request = service.submit_request("  магнит  ", "  САХАР  ", 5)

    assert request.store_id == 1 and request.product_id == 1  # case-insensitive lookup
    assert request.status == RequestStatus.SUBMITTED  # EL-14: заявка рождается «подана»
    assert request.requested_quantity == 5
    assert session.commits == 1


def test_submit_rejects_empty_names():
    service, _, session = make_service(products=[make_product()], stores=[make_store()])

    with pytest.raises(EmptyNameError):  # BR-1
        service.submit_request("   ", "Сахар", 5)
    with pytest.raises(EmptyNameError):
        service.submit_request("Магнит", "  ", 5)

    assert session.commits == 0


def test_submit_rejects_non_positive_quantity():
    service, *_ = make_service(products=[make_product()], stores=[make_store()])

    with pytest.raises(InvalidRequestQuantityError):  # BR-6
        service.submit_request("Магнит", "Сахар", 0)
    with pytest.raises(InvalidRequestQuantityError):
        service.submit_request("Магнит", "Сахар", -3)


def test_submit_unknown_store_rejected():
    service, *_ = make_service(products=[make_product()])  # магазина нет

    with pytest.raises(StoreNotFoundError):  # EL-8
        service.submit_request("Магнит", "Сахар", 5)


def test_submit_unknown_product_rejected():
    service, *_ = make_service(stores=[make_store()])  # товара нет

    with pytest.raises(ProductNotFoundError):  # EL-7
        service.submit_request("Магнит", "Сахар", 5)


# --- FR-9: process ----------------------------------------------------------


def test_process_unknown_request_rejected():
    service, *_ = make_service(products=[make_product()], stores=[make_store()])

    with pytest.raises(RequestNotFoundError):  # EL-18
        service.process_request(999)


def test_process_already_processed_rejected():
    request = make_request(status=RequestStatus.PROCESSED)
    service, _, session = make_service(
        products=[make_product()], stores=[make_store()], requests=[request]
    )

    with pytest.raises(RequestAlreadyProcessedError):  # EL-15
        service.process_request(1)

    assert session.commits == 0  # отказ не меняет ничего


def test_process_store_of_request_deleted_rejected():
    request = make_request(store_id=7)  # магазин 7 не существует
    service, *_ = make_service(products=[make_product()], requests=[request])

    with pytest.raises(StoreNotFoundError):  # EL-18: магазин заявки не найден
        service.process_request(1)


def test_process_insufficient_stock_rejected_and_nothing_changes():
    """BR-7: полный отказ — ни одно из трёх изменений не происходит."""
    product = make_product(quantity=3)
    request = make_request(quantity=5)  # 5 > 3
    service, requests_repo, session = make_service(
        products=[product], stores=[make_store()], requests=[request]
    )

    with pytest.raises(InsufficientStockError):  # BR-7
        service.process_request(1)

    assert session.commits == 0
    assert product.warehouse_quantity == 3  # склад не тронут
    assert requests_repo.store_products == []  # магазин не тронут
    assert request.status == RequestStatus.SUBMITTED  # статус не тронут (EL-15)


def test_process_success_three_changes_single_commit():
    product = make_product(quantity=10)
    request = make_request(quantity=5)
    service, requests_repo, session = make_service(
        products=[product], stores=[make_store()], requests=[request]
    )

    processed = service.process_request(1)

    assert session.commits == 1  # EL-17: атомарность = один commit на три изменения
    assert product.warehouse_quantity == 5  # склад −5
    assert requests_repo.store_products[0].quantity == 5  # магазин +5, строка родилась
    assert processed.status == RequestStatus.PROCESSED
    assert processed.processed_at is not None  # A-3


def test_process_success_increases_existing_store_stock():
    product = make_product(quantity=10)
    existing_row = StoreProduct(store_id=1, product_id=1, quantity=2)
    request = make_request(quantity=5)
    service, requests_repo, _ = make_service(
        products=[product],
        stores=[make_store()],
        requests=[request],
        store_products=[existing_row],
    )

    service.process_request(1)

    assert [sp.quantity for sp in requests_repo.store_products] == [7]  # 2 + 5, одна строка


def test_process_rejection_order_already_processed_first():
    """FR-9: «уже обработана» проверяется раньше, чем исчезновение магазина."""
    request = make_request(status=RequestStatus.PROCESSED, store_id=7)
    service, *_ = make_service(products=[make_product()], requests=[request])

    with pytest.raises(RequestAlreadyProcessedError):  # не StoreNotFoundError
        service.process_request(1)


# --- FR-10: list ------------------------------------------------------------


def test_list_returns_rows_ordered_by_number():
    requests = [make_request(number=3), make_request(number=1), make_request(number=2)]
    service, *_ = make_service(requests=requests)

    numbers = [row[0].number for row in service.list_requests()]

    assert numbers == [1, 2, 3]
