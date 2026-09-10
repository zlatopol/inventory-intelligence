from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.stores.repository import StoreRepository
from app.stores.schemas import StoreCreate, StoreRead
from app.stores.service import StoreService
from app.shared.db import get_session

router = APIRouter(prefix="/stores", tags=["stores"])


def get_store_service(session: Session = Depends(get_session)) -> StoreService:
    return StoreService(StoreRepository(session), session)


@router.post("", response_model=StoreRead, status_code=201)
def create_store(
    payload: StoreCreate,
    service: StoreService = Depends(get_store_service),
) -> StoreRead:
    """FR-3: включить новый магазин в список магазинов."""
    return StoreRead.model_validate(service.create_store(payload.name))


@router.delete("/{name}", status_code=204)
def delete_store(
    name: str,
    service: StoreService = Depends(get_store_service),
) -> None:
    """FR-4: удалить ненужный магазин из списка."""
    service.delete_store(name)


@router.get("", response_model=list[StoreRead])
def list_stores(
    service: StoreService = Depends(get_store_service),
) -> list[StoreRead]:
    """FR-11: просмотреть список магазинов (derived, see requirements.md)."""
    return [StoreRead.model_validate(s) for s in service.list_stores()]
