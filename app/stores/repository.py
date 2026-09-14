from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.stores.models import Store


class StoreRepository:
    """Data access for the store aggregate.

    No business decisions, no transaction management (ADR-0003): the owning
    service flushes/commits the shared session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_live_by_name(self, name: str) -> Store | None:
        """Case-insensitive lookup among live (non-deleted) stores (BR-4 semantics)."""
        stmt = select(Store).where(
            Store.deleted_at.is_(None),
            func.lower(Store.name) == name.lower(),
        )
        return self._session.scalars(stmt).first()

    def find_live_by_id(self, id: int) -> Store | None:
        stmt = select(Store).where(
            Store.deleted_at.is_(None),
            Store.id == id,
        )
        return self._session.scalars(stmt).first()

    def find_id_by_name(self, name: str) -> int:
        stmt = select(Store).where(
            Store.name == name
        )
        return self._session.scalars(stmt).first()

    def add(self, store: Store) -> Store:
        self._session.add(store)
        return store

    def list_live_ordered_by_name(self) -> Sequence[Store]:
        stmt = (
            select(Store)
            .where(Store.deleted_at.is_(None))
            .order_by(func.lower(Store.name))
        )
        return self._session.scalars(stmt).all()
