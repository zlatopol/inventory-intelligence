"""Прогноз спроса как API-сервис (Phase 3).

GET  /forecast?store_id&product_id&days  — прогноз на 1–14 дней (по умолчанию 3);
POST /forecast/retrain                   — ручное переобучение (форс-мажор, Q1).
Модель живёт в синглтоне сервиса (кэш + TTL), а не в запросе.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.forecast.schemas import ForecastRead, RetrainRead
from app.forecast.service import (
    MAX_FORECAST_DAYS,
    MIN_FORECAST_DAYS,
    ForecastService,
)
from app.ml.sources import load_from_stock_event
from app.shared.db import get_session

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _history_loader(session: Session):
    def load():
        return load_from_stock_event(session)

    return load


def get_forecast_service(
    session: Session = Depends(get_session),
) -> ForecastService:
    # Синглтон: модель и кэш переживают запросы; сессия — нет, поэтому
    # загрузчик открывает свою сессию (не держим долгоживущую).
    from app.shared.db import get_engine
    from sqlalchemy.orm import sessionmaker

    if not hasattr(get_forecast_service, "_instance"):
        factory = sessionmaker(bind=get_engine(), expire_on_commit=False)

        def load():
            with factory() as s:
                return load_from_stock_event(s)

        get_forecast_service._instance = ForecastService(history_loader=load)
    return get_forecast_service._instance


@router.get("", response_model=ForecastRead)
def get_forecast(
    store_id: int = Query(gt=0),
    product_id: int = Query(gt=0),
    days: int = Query(
        default=3, ge=MIN_FORECAST_DAYS, le=MAX_FORECAST_DAYS
    ),
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastRead:
    try:
        result = service.forecast(store_id, product_id, days)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ForecastRead.model_validate(result)


@router.post("/retrain", response_model=RetrainRead)
def retrain_model(
    service: ForecastService = Depends(get_forecast_service),
) -> RetrainRead:
    """Q1: форс-мажор — переобучить немедленно, не дожидаясь TTL."""
    return RetrainRead.model_validate(service.retrain(force=True))
