from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    """FR-1 input: the raw name; trimming happens in the service (D-1)."""

    name: str


class ReceiptCreate(BaseModel):
    """FR-5 input: количество поступления (type-checked here, BR-5 range in service)."""

    quantity: int


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    warehouse_quantity: int
