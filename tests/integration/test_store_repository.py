"""Integration tests: StoreRepository against real PostgreSQL (slice 2)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.stores.models import Store
from app.stores.repository import StoreRepository


def add_directly(session, name: str) -> Store:
    store = Store(name=name)
    session.add(store)
    session.flush()
    return store


def test_live_name_uniqueness_enforced_by_index(db_session):
    add_directly(db_session, "Магнит")

    db_session.add(Store(name="магнит"))  # different case — same live name
    with pytest.raises(IntegrityError):  # BR-4 via store_live_name_key
        db_session.flush()


def test_soft_deleted_name_can_be_recreated(db_session):
    store = add_directly(db_session, "Магнит")
    store.deleted_at = store.created_at
    db_session.flush()

    recreated = add_directly(db_session, "МАГНИТ")  # partial index frees the name
    assert recreated.id != store.id


def test_find_live_by_name_ignores_deleted(db_session):
    store = add_directly(db_session, "Магнит")
    store.deleted_at = store.created_at
    db_session.flush()
    db_session.expire_all()

    repo = StoreRepository(db_session)
    assert repo.find_live_by_name("магнит") is None


def test_list_live_ordered_by_name_case_insensitive(db_session):
    for name in ["Ярче", "ашан", "Магнит"]:
        add_directly(db_session, name)
    db_session.expire_all()

    repo = StoreRepository(db_session)
    names = [s.name for s in repo.list_live_ordered_by_name()]

    assert names == ["ашан", "Магнит", "Ярче"]  # FR-11 / EL-10 pattern
