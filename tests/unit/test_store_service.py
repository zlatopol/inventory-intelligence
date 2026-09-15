"""Unit tests for StoreService (FR-3, FR-4, FR-11) — no database."""
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from fakes import FakeSession

from app.shared.errors import (
    DuplicateStoreNameError,
    EmptyNameError,
    StoreDeletionBlockedError,
    StoreNotFoundError,
)
from app.stores.models import Store
from app.stores.service import StoreService


class FakeRepository:
    def __init__(self, stores: list[Store] | None = None) -> None:
        self.stores: list[Store] = list(stores or [])

    def find_live_by_name(self, name: str) -> Store | None:
        return next(
            (
                s
                for s in self.stores
                if s.deleted_at is None and s.name.lower() == name.lower()
            ),
            None,
        )

    def add(self, store: Store) -> Store:
        self.stores.append(store)
        return store

    def list_live_ordered_by_name(self) -> list[Store]:
        return sorted(
            (s for s in self.stores if s.deleted_at is None),
            key=lambda s: s.name.lower(),
        )

class FakeRequestsRepository:
    """Stand-in for StoreRequestRepository — only the BR-8 guard query."""

    def __init__(self, pending_store_ids: set[int] | None = None) -> None:
        self.pending_store_ids = pending_store_ids or set()

    def has_pending_for_store(self, store_id: int) -> bool:
        return store_id in self.pending_store_ids


def make_service(
    repo: FakeRepository | None = None,
    session: FakeSession | None = None,
    requests_repo: FakeRequestsRepository | None = None,
):
    repo = repo or FakeRepository()
    session = session or FakeSession()
    requests_repo = requests_repo or FakeRequestsRepository()
    return (
        StoreService(repo, requests_repo, session),  # type: ignore[arg-type]
        repo,
        session,
    )


# --- FR-3: create -----------------------------------------------------------


def test_create_stores_trimmed_name():
    service, repo, session = make_service()

    store = service.create_store("  Пятёрочка  ")

    assert store.name == "Пятёрочка"  # D-1 + EL-4
    assert repo.stores == [store]
    assert session.commits == 1


def test_create_rejects_whitespace_only_name():
    service, *_ = make_service()
    with pytest.raises(EmptyNameError):  # BR-1
        service.create_store("   ")


def test_create_rejects_duplicate_case_insensitive():
    service, *_ = make_service(FakeRepository([Store(name="Пятёрочка")]))
    with pytest.raises(DuplicateStoreNameError):  # BR-4
        service.create_store("пятёрочка")


def test_create_translates_unique_violation():
    race = IntegrityError("INSERT ...", None, Exception("duplicate key"))
    service, _, session = make_service(session=FakeSession(flush_error=race))

    with pytest.raises(DuplicateStoreNameError):  # ADR-0004
        service.create_store("Пятёрочка")

    assert session.rollbacks == 1
    assert session.commits == 0


# --- FR-4: delete -----------------------------------------------------------


def test_delete_marks_deleted_at():
    store = Store(name="Пятёрочка")
    service, *_ = make_service(FakeRepository([store]))

    service.delete_store("пятёрочка")  # case-insensitive lookup

    assert store.deleted_at is not None  # soft delete (ADR-0005)
    # BR-8 (pending requests guard) is vacuously true until slice 3.


def test_delete_unknown_store_rejected():
    service, *_ = make_service()
    with pytest.raises(StoreNotFoundError):  # EL-8
        service.delete_store("Пятёрочка")


def test_delete_blocked_by_pending_request():
    """BR-8: заявки со статусом «подана» блокируют удаление магазина."""
    store = Store(id=7, name="Пятёрочка")
    service, *_ = make_service(
        repo=FakeRepository([store]),
        requests_repo=FakeRequestsRepository(pending_store_ids={7}),
    )

    with pytest.raises(StoreDeletionBlockedError):
        service.delete_store("Пятёрочка")

    assert store.deleted_at is None  # rejection changes nothing


def test_delete_allowed_when_only_processed_requests():
    """BR-8 scope: обработанные заявки не блокируют удаление (EL-19)."""
    store = Store(id=7, name="Пятёрочка")
    service, *_ = make_service(
        repo=FakeRepository([store]),
        requests_repo=FakeRequestsRepository(pending_store_ids=set()),
    )

    service.delete_store("Пятёрочка")

    assert store.deleted_at is not None


def test_delete_rejects_empty_name():
    service, *_ = make_service()
    with pytest.raises(EmptyNameError):
        service.delete_store("  ")


# --- FR-11: list ------------------------------------------------------------


def test_list_returns_live_stores_ordered_case_insensitively():
    live = [Store(name="Ярче"), Store(name="ашан"), Store(name="Магнит")]
    deleted = Store(name="Абсолют")
    deleted.deleted_at = datetime.now(UTC)
    service, *_ = make_service(FakeRepository(live + [deleted]))

    result = service.list_stores()

    assert [s.name for s in result] == ["ашан", "Магнит", "Ярче"]  # EL-10 pattern
