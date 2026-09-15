from pydantic import BaseModel, ConfigDict


class StoreCreate(BaseModel):

    name: str


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductStockRead(BaseModel):
    """FR-7: товар внутри магазина."""

    name: str
    quantity: int


class StoreStockRead(BaseModel):
    """FR-7: магазин с его товарами (пустой список — валидный случай, EL-21)."""

    name: str
    products: list[ProductStockRead]
