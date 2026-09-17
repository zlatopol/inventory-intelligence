from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.events.repository import StockEventRepository
from app.products.repository import ProductRepository
from app.requests.models import StoreRequest
from app.requests.repository import StoreRequestRepository
from app.requests.schemas import RequestCreate, RequestRead
from app.requests.service import RequestService
from app.shared.db import get_session
from app.stores.repository import StoreRepository

router = APIRouter(prefix="/requests", tags=["requests"])


def get_request_service(session: Session = Depends(get_session)) -> RequestService:
    # FR-9 spans three aggregates — the service composes all repositories
    # (cross-domain composition per ADR-0002 ред. 2, transaction per ADR-0003).
    return RequestService(
        requests_repo=StoreRequestRepository(session),
        product_repo=ProductRepository(session),
        store_repo=StoreRepository(session),
        events_repo=StockEventRepository(session),
        session=session,
    )


def _to_read(request: StoreRequest, store_name: str, product_name: str) -> RequestRead:
    """Manual assembly: the entity carries ids, the schema needs names."""
    return RequestRead(
        number=request.number,
        status=request.status,
        store_name=store_name,
        product_name=product_name,
        requested_quantity=request.requested_quantity,
        submitted_at=request.submitted_at,
        processed_at=request.processed_at,
    )


@router.post("", response_model=RequestRead, status_code=201)
def create_request(
    payload: RequestCreate,
    service: RequestService = Depends(get_request_service),
) -> RequestRead:
    """FR-8: подать заявку магазина."""
    request = service.submit_request(
        payload.store_name, payload.product_name, payload.quantity
    )
    # Response names are the trimmed spellings (D-1) — what was stored,
    # not the raw input the client sent.
    return _to_read(request, payload.store_name.strip(), payload.product_name.strip())


@router.post("/{number}/process", response_model=RequestRead)
def process_request(
    number: int,
    service: RequestService = Depends(get_request_service),
) -> RequestRead:
    """FR-9: обработать заявку (отпуск со склада в магазин)."""
    service.process_request(number)
    request, store_name, product_name = service.get_request_with_names(number)
    return _to_read(request, store_name, product_name)


@router.get("", response_model=list[RequestRead])
def list_requests(
    service: RequestService = Depends(get_request_service),
) -> list[RequestRead]:
    """FR-10: просмотреть заявки (все годы, EL-20; порядок по номеру)."""
    return [
        _to_read(request, store_name, product_name)
        for request, store_name, product_name in service.list_requests()
    ]