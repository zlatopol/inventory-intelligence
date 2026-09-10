from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.stores.models import Store
from app.stores.repository import StoreRepository
from app.shared.errors import (
    DuplicateStoreNameError,
    EmptyNameError,
    StoreNotFoundError,
)



class StoreService:
    """Store use cases: FR-3, FR-4, FR-11.

    Transaction owner per ADR-0003: mutating use cases commit here.
    """

    def __init__(self, repository: StoreRepository, session: Session) -> None:
        self._repo = repository
        self._session = session

    def create_store(self, raw_name: str) -> Store:
        """FR-3: включить новый магазин в список магазинов."""
        name = raw_name.strip()  # D-1
        if not name:
            raise EmptyNameError  # BR-1 (ed.2: applies to all names)
        if self._repo.find_live_by_name(name) is not None:
            raise DuplicateStoreNameError  # BR-4 (deterministic friendly check)

        store = Store(name=name)
        self._repo.add(store)
        try:
            self._session.flush()
        except IntegrityError:
            # ADR-0004: the partial unique index won a race with us —
            # same user-facing outcome as the BR-4 check above.
            self._session.rollback()
            raise DuplicateStoreNameError from None
        self._session.commit()
        return store

    def delete_store(self, raw_name: str) -> None:
        """FR-4: удалить ненужный магазин из списка (soft delete, ADR-0005)."""
        name = raw_name.strip()
        if not name:
            raise EmptyNameError  # BR-1
        store = self._get_live_or_raise(name)
        # BR-8 (FR-4): guard pending («подана») requests here — slice 3
        # (vacuously true while store_request does not exist).
        store.deleted_at = datetime.now(UTC)
        self._session.commit()

    def list_stores(self) -> Sequence[Store]:
        """FR-11: просмотреть список магазинов."""
        return self._repo.list_live_ordered_by_name()

    def _get_live_or_raise(self, name: str) -> Store:
        store = self._repo.find_live_by_name(name)
        if store is None:
            raise StoreNotFoundError
        return store