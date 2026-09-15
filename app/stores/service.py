from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.requests.repository import StoreRequestRepository
from app.stores.models import Store
from app.stores.repository import StoreRepository
from app.shared.errors import (
    DuplicateStoreNameError,
    EmptyNameError,
    StoreDeletionBlockedError,
    StoreNotFoundError,
)



class StoreService:
    """Store use cases: FR-3, FR-4, FR-11.

    Transaction owner per ADR-0003: mutating use cases commit here.
    """

    def __init__(
        self,
        repository: StoreRepository,
        requests_repo: StoreRequestRepository,
        session: Session,
    ) -> None:
        self._repo = repository
        self._requests_repo = requests_repo
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
        if self._requests_repo.has_pending_for_store(store.id):
            raise StoreDeletionBlockedError  # BR-8: заявки «подана» блокируют удаление
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

    def stock_by_store(self) -> list[tuple[Store, list[tuple[str, int]]]]:
        """FR-7: просмотреть информацию о товарах по магазинам.

        Flat SQL rows grouped per store; ordering comes from SQL (EL-21);
        a store without products yields an empty list (displayed, not hidden);
        delisted-but-present products included (EL-22)."""
        rows = self._repo.list_live_with_stock()
        grouped = {}
        for store, product_name, quantity in rows:
            items = grouped.setdefault(store, [])
            if product_name is not None:  # строка пустого магазина не попадает в товары
                items.append((product_name, quantity))
        return list(grouped.items())