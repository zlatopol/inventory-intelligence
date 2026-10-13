"""API-схемы рекомендаций по закупке (EX-2)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    status: Literal["order", "sufficient", "cold_start"]
    warehouse_quantity: int
    forecast_demand: float | None = None
    safety_stock: float | None = None
    order_quantity: int | None = None
    model: str | None = None


class RecommendationListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    service_level: float
    lead_time_days: int
    horizon_days: int
    warning: str | None = None
    recommendations: list[RecommendationRead]
