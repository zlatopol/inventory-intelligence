from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.products.models import Product
from app.requests.models import RequestStatus, StoreProduct, StoreRequest
from app.stores.models import Store


class StoreRequestRepository:
    """Data access for the store_request aggregate (+ store_product stock rows).

    No business decisions, no transaction management (ADR-0003): the owning
    service flushes/commits the shared session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, store_request: StoreRequest) -> StoreRequest:
        self._session.add(store_request)
        return store_request

    def get_by_number(self, number: int) -> StoreRequest | None:
        """FR-9 lookup by the business number (unique, EL-14)."""
        stmt = select(StoreRequest).where(StoreRequest.number == number)
        return self._session.scalars(stmt).first()

    def list_all_with_names(self) -> Sequence[tuple[StoreRequest, str, str]]:
        """FR-10: all requests (incl. past years, EL-20) with store/product names,
        ordered by number. One query — joins instead of per-row lookups (no N+1).
        Soft-deleted stores/products still resolve: their rows are alive (EL-19/EL-22)."""
        stmt = (
            select(StoreRequest, Store.name, Product.name)
            .join(Store, StoreRequest.store_id == Store.id)
            .join(Product, StoreRequest.product_id == Product.id)
            .order_by(StoreRequest.number)
        )
        return self._session.execute(stmt).all()

    def get_with_names(self, number: int) -> tuple[StoreRequest, str, str] | None:
        """FR-9 response: one request + resolved store/product names (single query,
        same joins as list_all_with_names)."""
        stmt = (
            select(StoreRequest, Store.name, Product.name)
            .join(Store, StoreRequest.store_id == Store.id)
            .join(Product, StoreRequest.product_id == Product.id)
            .where(StoreRequest.number == number)
        )
        return self._session.execute(stmt).first()

    def has_pending_for_store(self, store_id: int) -> bool:
        """BR-8 guard query; served by the partial index store_request_pending_store."""
        stmt = select(StoreRequest).where(
            StoreRequest.store_id == store_id,
            StoreRequest.status == RequestStatus.SUBMITTED.value,
        )
        return self._session.scalars(stmt).first() is not None

    def get_store_product(self, store_id: int, product_id: int) -> StoreProduct | None:
        stmt = select(StoreProduct).where(
            StoreProduct.store_id == store_id,
            StoreProduct.product_id == product_id,
        )
        return self._session.scalars(stmt).first()

    def increase_store_stock(
        self, store_id: int, product_id: int, quantity: int
    ) -> StoreProduct:
        """FR-9 store-side effect: increase per-store stock, creating the row on
        first shipment («если товара не было — количество равно количеству заявки»)."""
        existing = self.get_store_product(store_id, product_id)
        if existing is not None:
            existing.quantity += quantity
            return existing
        new_row = StoreProduct(store_id=store_id, product_id=product_id, quantity=quantity)
        self._session.add(new_row)
        return new_row