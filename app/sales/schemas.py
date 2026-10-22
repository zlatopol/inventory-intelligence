from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SaleCreate(BaseModel):
    store_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, strict=True)
    sold_at: datetime

    @field_validator("sold_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Дата продажи должна содержать часовой пояс")
        return value


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    store_name: str
    product_id: int
    product_name: str
    quantity: int
    sold_at: datetime
    created_at: datetime
    status: str
    reversal_event_id: int | None = None


class SaleReversalRead(BaseModel):
    sale_id: int
    reversal_event_id: int
    store_stock: int
