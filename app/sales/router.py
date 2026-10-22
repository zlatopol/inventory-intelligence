from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.sales.repository import SaleRepository
from app.sales.schemas import SaleCreate, SaleRead, SaleReversalRead
from app.sales.service import SaleService
from app.shared.db import get_session

router = APIRouter(prefix="/sales", tags=["sales"])


def get_sale_service(session: Session = Depends(get_session)) -> SaleService:
    return SaleService(SaleRepository(session), session)


def _read_sale(event, store_name: str, product_name: str, reversal_id: int | None) -> SaleRead:
    return SaleRead(
        id=event.id,
        store_id=event.store_id,
        store_name=store_name,
        product_id=event.product_id,
        product_name=product_name,
        quantity=event.quantity,
        sold_at=event.sold_at,
        created_at=event.created_at,
        status="cancelled" if reversal_id is not None else "active",
        reversal_event_id=reversal_id,
    )


@router.post("", response_model=SaleRead, status_code=201)
def create_sale(
    payload: SaleCreate,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    service: SaleService = Depends(get_sale_service),
) -> SaleRead:
    event = service.register_sale(
        store_id=payload.store_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        sold_at=payload.sold_at,
        idempotency_key=str(idempotency_key),
    )
    store = service._repo.get_live_store(payload.store_id)
    product = service._repo.get_live_product(payload.product_id)
    reversal = service._repo.get_reversal_for(event.id)
    return _read_sale(
        event,
        store.name if store else "",
        product.name if product else "",
        reversal.id if reversal else None,
    )


@router.get("", response_model=list[SaleRead])
def list_sales(
    store_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    sold_from: datetime | None = None,
    sold_to: datetime | None = None,
    status: Literal["all", "active", "cancelled"] = "all",
    service: SaleService = Depends(get_sale_service),
) -> list[SaleRead]:
    rows = service.list_sales(
        store_id=store_id,
        product_id=product_id,
        sold_from=sold_from,
        sold_to=sold_to,
        status=status,
    )
    return [_read_sale(event, store_name, product_name, reversal_id)
            for event, store_name, product_name, reversal_id in rows]


@router.post("/{sale_id}/reverse", response_model=SaleReversalRead)
def reverse_sale(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
) -> SaleReversalRead:
    reversal, stock_quantity = service.reverse_sale(sale_id)
    return SaleReversalRead(
        sale_id=sale_id,
        reversal_event_id=reversal.id,
        store_stock=stock_quantity,
    )
