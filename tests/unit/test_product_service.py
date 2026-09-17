"""Unit tests for ProductService (FR-1, FR-2, FR-5, FR-6) — no database.

Repositories and the session are faked; only business rules are under test.
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from fakes import FakeSession

from app.products.models import Product
from app.products.repository import ProductRepository
from app.products.service import ProductService
from app.shared.errors import (
    DuplicateProductNameError,
    EmptyNameError,
    InvalidReceiptQuantityError,
    ProductDeletionBlockedError,
    ProductNotFoundError,
)


class FakeRepository:
    """In-memory stand-in matching ProductRepository's contract."""

    def __init__(self, products: list[Product] | None = None) -> None:
        self.products: list[Product] = list(products or [])

    def find_live_by_name(self, name: str) -> Product | None:
        return next(
            (
                p
                for p in self.products
                if p.deleted_at is None and p.name.lower() == name.lower()
            ),
            None,
        )

    def add(self, product: Product) -> Product:
        self.products.append(product)
        return product

    def list_live_ordered_by_name(self) -> list[Product]:
        return sorted(
            (p for p in self.products if p.deleted_at is None),
            key=lambda p: p.name.lower(),
        )


class FakeEventsRepo:
    """Stand-in for StockEventRepository — collects added events (append-only)."""

    def __init__(self) -> None:
        self.events: list = []

    def add(self, event) -> None:
        self.events.append(event)


def make_service(repo: FakeRepository | None = None, session: FakeSession | None = None):
    repo = repo or FakeRepository()
    session = session or FakeSession()
    return (
        ProductService(repo, FakeEventsRepo(), session),  # type: ignore[arg-type]
        repo,
        session,
    )


# --- FR-1: create -----------------------------------------------------------


def test_create_stores_trimmed_name_and_zero_quantity():
    service, repo, session = make_service()

    product = service.create_product("  Молоко  ")

    assert product.name == "Молоко"  # D-1 + EL-4: stored spelling is the first entered
    assert product.warehouse_quantity == 0  # EL-2
    assert repo.products == [product]
    assert session.commits == 1


def test_create_rejects_whitespace_only_name():
    service, *_ = make_service()
    with pytest.raises(EmptyNameError):  # BR-1
        service.create_product("   ")


def test_create_rejects_duplicate_case_insensitive():
    service, *_ = make_service(FakeRepository([Product(name="Молоко", warehouse_quantity=0)]))
    with pytest.raises(DuplicateProductNameError):  # BR-2
        service.create_product("молоко")


def test_create_translates_unique_violation():
    # ADR-0004: the DB index won the race — same outcome as the BR-2 check.
    race = IntegrityError("INSERT ...", None, Exception("duplicate key"))
    service, _, session = make_service(session=FakeSession(flush_error=race))

    with pytest.raises(DuplicateProductNameError):
        service.create_product("Молоко")

    assert session.rollbacks == 1
    assert session.commits == 0


# --- FR-5: receive ----------------------------------------------------------


def test_receive_rejects_non_positive_or_fractional_quantity():
    service, *_ = make_service(FakeRepository([Product(name="Сахар", warehouse_quantity=0)]))
    with pytest.raises(InvalidReceiptQuantityError):  # BR-5
        service.receive_product("Сахар", 0)
    with pytest.raises(InvalidReceiptQuantityError):
        service.receive_product("Сахар", -3)
    with pytest.raises(InvalidReceiptQuantityError):
        service.receive_product("Сахар", 2.5)


def test_receive_rejects_empty_name_before_lookup():
    service, *_ = make_service()
    with pytest.raises(EmptyNameError):  # BR-1 applies to every name input
        service.receive_product("  ", 5)


def test_receive_unknown_product_rejected():
    service, *_ = make_service()
    with pytest.raises(ProductNotFoundError):  # EL-7
        service.receive_product("Сахар", 5)


def test_receive_increases_warehouse_quantity():
    repo = FakeRepository([Product(name="Сахар", warehouse_quantity=0)])
    service, *_ = make_service(repo)

    service.receive_product("Сахар", 5)
    service.receive_product("  САХАР  ", 3)  # lookup is case-insensitive, trimmed

    assert repo.products[0].warehouse_quantity == 8


# --- FR-2: delete -----------------------------------------------------------


def test_delete_blocked_when_quantity_nonzero():
    product = Product(name="Сахар", warehouse_quantity=250)
    service, *_ = make_service(FakeRepository([product]))

    with pytest.raises(ProductDeletionBlockedError):  # BR-3
        service.delete_product("Сахар")

    assert product.deleted_at is None  # rejection changes nothing


def test_delete_marks_deleted_at_when_quantity_zero():
    product = Product(name="Сахар", warehouse_quantity=0)
    service, *_ = make_service(FakeRepository([product]))

    service.delete_product("сахар")  # lookup is case-insensitive

    assert product.deleted_at is not None  # soft delete (ADR-0005)


def test_delete_unknown_product_rejected():
    service, *_ = make_service()
    with pytest.raises(ProductNotFoundError):
        service.delete_product("Сахар")


# --- FR-6: list -------------------------------------------------------------


def test_list_returns_live_products_ordered_case_insensitively():
    live = [
        Product(name="Яблоки", warehouse_quantity=1),
        Product(name="ананас", warehouse_quantity=2),
        Product(name="Банан", warehouse_quantity=3),
    ]
    deleted = Product(name="Арбуз", warehouse_quantity=0)
    deleted.deleted_at = datetime.now(UTC)
    service, *_ = make_service(FakeRepository(live + [deleted]))

    result = service.list_warehouse()

    assert [p.name for p in result] == ["ананас", "Банан", "Яблоки"]  # EL-10
