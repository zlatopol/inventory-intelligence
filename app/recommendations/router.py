"""Рекомендации по закупке как API-сервис (EX-2).

GET /recommendations?product_id&service_level&lead_time_days&horizon_days —
список по всем товарам складского списка (Q1), опциональный фильтр по товару.

Валидация: простые границы продублированы в Query (ранний 422, как days у
прогноза), но канонический источник правил — СЕРВИС (CLI полагается только
на него); перекрёстное правило L+H ≤ 14 в Query невыразимо — живёт в сервисе.
product_id — фильтр, не поиск: неизвестный id даёт пустой список, не 404.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import sessionmaker

from app.forecast.router import get_forecast_service
from app.forecast.service import ForecastService
from app.recommendations.policy import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_LEAD_TIME_DAYS,
    DEFAULT_SERVICE_LEVEL,
    MIN_PARAM_DAYS,
)
from app.recommendations.schemas import RecommendationListRead
from app.recommendations.service import RecommendationService
from app.shared.db import get_engine

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service(
    forecast: ForecastService = Depends(get_forecast_service),
) -> RecommendationService:
    # Синглтон + переиспользование синглтона прогноза: модель и её кэш — общие.
    # Сессии запросов недолговечны, поэтому загрузчики открывают свои.
    if not hasattr(get_recommendation_service, "_instance"):
        from app.ml.sources import load_from_stock_event
        from app.products.repository import ProductRepository

        factory = sessionmaker(bind=get_engine(), expire_on_commit=False)

        def load_history():
            with factory() as s:
                return load_from_stock_event(s)

        def load_products():
            with factory() as s:
                return ProductRepository(s).list_live_ordered_by_name()

        get_recommendation_service._instance = RecommendationService(
            forecast=forecast,
            history_loader=load_history,
            products_loader=load_products,
        )
    return get_recommendation_service._instance


@router.get("", response_model=RecommendationListRead)
def get_recommendations(
    product_id: int | None = Query(default=None, gt=0),
    service_level: float = Query(
        default=DEFAULT_SERVICE_LEVEL, gt=0, lt=1
    ),
    lead_time_days: int = Query(
        default=DEFAULT_LEAD_TIME_DAYS, ge=MIN_PARAM_DAYS
    ),
    horizon_days: int = Query(
        default=DEFAULT_HORIZON_DAYS, ge=MIN_PARAM_DAYS
    ),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationListRead:
    result = service.recommendations(
        service_level=service_level,
        lead_time_days=lead_time_days,
        horizon_days=horizon_days,
        product_id=product_id,
    )
    return RecommendationListRead.model_validate(result)
