from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.products.repository import ProductRepository
from app.products.schemas import ProductCreate, ProductRead, ReceiptCreate
from app.products.service import ProductService
from app.shared.db import get_session

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(session: Session = Depends(get_session)) -> ProductService:
    return ProductService(ProductRepository(session), session)


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """FR-1: включить новый товар в список товаров на складе."""
    return ProductRead.model_validate(service.create_product(payload.name))


@router.delete("/{name}", status_code=204)
def delete_product(
    name: str,
    service: ProductService = Depends(get_product_service),
) -> None:
    """FR-2: удалить ненужный товар из складского списка."""
    service.delete_product(name)


@router.post("/{name}/receipts", response_model=ProductRead)
def receive_product(
    name: str,
    payload: ReceiptCreate,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """FR-5: учесть поступление некоторого товара на склад."""
    return ProductRead.model_validate(service.receive_product(name, payload.quantity))


@router.get("", response_model=list[ProductRead])
def list_products(
    service: ProductService = Depends(get_product_service),
) -> list[ProductRead]:
    """FR-6: просмотреть информацию о товарах на складе."""
    return [ProductRead.model_validate(p) for p in service.list_warehouse()]
