"""Integration tests: ProductRepository against real PostgreSQL (slice 1).

These tests exercise what unit tests cannot: the partial unique index (BR-2 +
ADR-0004/0005), the CHECK constraint, and the FR-6 ordering as performed by the
database.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.products.models import Product
from app.products.repository import ProductRepository


def add_directly(session, name: str, warehouse_quantity: int = 0) -> Product:
    product = Product(name=name, warehouse_quantity=warehouse_quantity)
    session.add(product)
    session.flush()
    return product


def test_live_name_uniqueness_enforced_by_index(db_session):
    add_directly(db_session, "Молоко")

    db_session.add(Product(name="молоко"))  # different case — same live name
    with pytest.raises(IntegrityError):  # BR-2 via product_live_name_key
        db_session.flush()


def test_soft_deleted_name_can_be_recreated(db_session):
    product = add_directly(db_session, "Молоко")
    product.deleted_at = product.created_at
    db_session.flush()

    # The index is partial (WHERE deleted_at IS NULL) — the name is free again.
    recreated = add_directly(db_session, "МОЛОКО")
    assert recreated.id != product.id


def test_warehouse_quantity_check_constraint(db_session):
    db_session.add(Product(name="Сахар", warehouse_quantity=-1))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_find_live_by_name_ignores_deleted(db_session):
    product = add_directly(db_session, "Молоко")
    product.deleted_at = product.created_at
    db_session.flush()
    db_session.expire_all()

    repo = ProductRepository(db_session)
    assert repo.find_live_by_name("молоко") is None


def test_list_live_ordered_by_name_case_insensitive(db_session):
    add_directly(db_session, "Яблоки", 1)
    add_directly(db_session, "ананас", 2)
    add_directly(db_session, "Банан", 3)
    db_session.expire_all()

    repo = ProductRepository(db_session)
    names = [p.name for p in repo.list_live_ordered_by_name()]

    assert names == ["ананас", "Банан", "Яблоки"]  # FR-6 / EL-10
