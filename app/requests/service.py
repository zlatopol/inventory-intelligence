"""Request use cases: FR-8 (submit), FR-9 (process), FR-10 (list).

Transaction owner per ADR-0003: FR-9 changes three things in ONE commit —
warehouse quantity, per-store stock, request status/date (EL-17 atomicity).
"""
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.events.models import StockEvent
from app.events.repository import StockEventRepository
from app.products.repository import ProductRepository
from app.requests.models import RequestStatus, StoreRequest
from app.requests.repository import StoreRequestRepository
from app.shared.errors import (
    EmptyNameError,
    InsufficientStockError,
    InvalidRequestQuantityError,
    ProductNotFoundError,
    RequestAlreadyProcessedError,
    RequestNotFoundError,
    StoreNotFoundError,
)
from app.stores.repository import StoreRepository


def _is_positive_integer(quantity: int) -> bool:
    # bool is an int subclass in Python — exclude it explicitly (True == 1).
    return isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0


class RequestService:

    def __init__(
        self,
        requests_repo: StoreRequestRepository,
        product_repo: ProductRepository,
        store_repo: StoreRepository,
        events_repo: StockEventRepository,
        session: Session,
    ) -> None:
        self._requests_repo = requests_repo
        self._product_repo = product_repo
        self._store_repo = store_repo
        self._events_repo = events_repo
        self._session = session

    def submit_request(
        self, raw_store_name: str, raw_product_name: str, quantity: int
    ) -> StoreRequest:
        """FR-8: подать заявку магазина."""
        store_name = raw_store_name.strip()  # D-1
        product_name = raw_product_name.strip()  # D-1
        if not store_name or not product_name:
            raise EmptyNameError  # BR-1 (ed.2: applies to all names)
        if not _is_positive_integer(quantity):
            raise InvalidRequestQuantityError  # BR-6

        store = self._store_repo.find_live_by_name(store_name)
        if store is None:
            raise StoreNotFoundError  # EL-8
        product = self._product_repo.find_live_by_name(product_name)
        if product is None:
            raise ProductNotFoundError  # EL-7

        request = StoreRequest(
            store_id=store.id,
            product_id=product.id,
            requested_quantity=quantity,
            status=RequestStatus.SUBMITTED,  # EL-14: заявка рождается «подана»
        )
        self._requests_repo.add(request)
        self._session.flush()  # here the sequence assigns `number` (EL-14)
        self._session.commit()
        return request

    def process_request(self, number: int) -> StoreRequest:
        """FR-9: обработать заявку — отпуск со склада в магазин.

        Rejection order mirrors FR-9: not found → already processed →
        store/product of the request gone → BR-7. Three changes, one commit.
        """
        request = self._requests_repo.get_by_number(number)
        if request is None:
            raise RequestNotFoundError  # EL-18
        if request.status != RequestStatus.SUBMITTED:
            raise RequestAlreadyProcessedError  # EL-15

        store = self._store_repo.find_live_by_id(request.store_id)
        if store is None:
            raise StoreNotFoundError  # EL-18: магазин заявки не найден
        product = self._product_repo.find_live_by_id(request.product_id)
        if product is None:
            raise ProductNotFoundError  # EL-18: товар заявки не найден
        if product.warehouse_quantity < request.requested_quantity:
            raise InsufficientStockError  # BR-7

        # Three changes — all or nothing (EL-17): one commit below.
        product.warehouse_quantity -= request.requested_quantity
        self._requests_repo.increase_store_stock(
            store.id, product.id, request.requested_quantity
        )
        request.status = RequestStatus.PROCESSED
        request.processed_at = datetime.now(UTC)  # A-3
        # Event history (Phase 2): the shipment event rides the SAME transaction;
        # request_number is a snapshot (Q2) — witness of the past, not an FK.
        self._events_repo.add(
            StockEvent(
                event_type="shipment",
                product_id=product.id,
                store_id=store.id,
                request_number=request.number,
                quantity=request.requested_quantity,
            )
        )
        self._session.commit()
        return request

    def list_requests(self) -> Sequence[tuple[StoreRequest, str, str]]:
        """FR-10: просмотреть заявки (names come pre-joined, no N+1)."""
        return self._requests_repo.list_all_with_names()

    def get_request_with_names(self, number: int) -> tuple[StoreRequest, str, str]:
        """FR-9 response: the processed request with store/product names."""
        row = self._requests_repo.get_with_names(number)
        if row is None:
            raise RequestNotFoundError  # unreachable right after a successful process; safety net
        return row
