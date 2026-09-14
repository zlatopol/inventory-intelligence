from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_STATUS_RU = {"submitted": "подана", "processed": "обработана"}


class RequestCreate(BaseModel):
    """FR-8 input: названия магазина/товара + количество (BR-6 range in service)."""

    store_name: str
    product_name: str
    quantity: int


class RequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    status: str
    store_name: str
    product_name: str
    requested_quantity: int
    submitted_at: datetime
    processed_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def _status_to_ru(cls, value: str) -> str:
        return _STATUS_RU[value]  # развилка A: перевод на краю API
