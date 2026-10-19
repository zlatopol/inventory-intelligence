"""API-схемы прогноза (Phase 3: model as a service)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ForecastDayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: datetime
    demand: float


class ForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: int
    product_id: int
    generated_at: datetime
    model: str
    warning: str | None = None
    forecast: list[ForecastDayRead]


class RetrainRead(BaseModel):
    status: str
    trained_at: datetime


class HistoryDayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: datetime
    demand: int


class HistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: int
    product_id: int
    days: int
    history: list[HistoryDayRead]
