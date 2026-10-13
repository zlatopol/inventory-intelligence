"""RecommendationService — рекомендация по закупке как сервис (EX-2).

Прогноз ≠ решение: между ними инвентаризационная политика (policy.py).
Спрос склада по товару = Σ прогнозов по всем парам (магазин, товар) с
историей — продаж в магазинах у нас нет, единственный реальный остаток,
который может истощаться, — склад (Product.warehouse_quantity).

Зависимости — инъекции (как history_loader у ForecastService):
- forecast: ForecastService — переиспользуем, НЕ дублируем;
- history_loader: контракт [date, store_id, product_id, demand] — для σ;
- products_loader: живые товары с остатками (list_live_ordered_by_name).

Производительность (честная оговорка): forecast() вызывается НА пару и
каждый раз сам подгружает историю целиком — на сид-данных (десятки пар)
незаметно, для сотен пар нужен массовый прогноз — см. §8 «Future ideas»
в docs/requirements.md.

Валидация параметров — ЗДЕСЬ (единственный источник правил: API дублирует
простые границы в Query для раннего 422, CLI полагается только на сервис).
"""
import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

import pandas as pd

from app.forecast.service import ForecastService
from app.recommendations.policy import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_LEAD_TIME_DAYS,
    DEFAULT_SERVICE_LEVEL,
    SIGMA_WINDOW_DAYS,
    order_quantity,
    safety_stock,
    validate_params,
)


class ProductLike(Protocol):
    """Минимальный контракт товара для сервиса (ORM Product ему удовлетворяет)."""

    id: int
    name: str
    warehouse_quantity: int


class RecommendationService:
    def __init__(
        self,
        forecast: ForecastService,
        history_loader: Callable[[], pd.DataFrame],
        products_loader: Callable[[], list[ProductLike]],
    ) -> None:
        self._forecast = forecast
        self._history_loader = history_loader
        self._products_loader = products_loader

    def recommendations(
        self,
        service_level: float = DEFAULT_SERVICE_LEVEL,
        lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
        horizon_days: int = DEFAULT_HORIZON_DAYS,
        product_id: int | None = None,
    ) -> dict:
        validate_params(service_level, lead_time_days, horizon_days)
        window = lead_time_days + horizon_days

        history = self._history_loader()
        products = self._products_loader()
        if product_id is not None:  # фильтр, не поиск: пустой список честен
            products = [p for p in products if p.id == product_id]

        rows = []
        warning = None
        for product in products:
            stores = sorted(
                history.loc[
                    history["product_id"] == product.id, "store_id"
                ].unique()
            )
            if len(stores) == 0:
                rows.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "status": "cold_start",
                        "warehouse_quantity": product.warehouse_quantity,
                        "forecast_demand": None,
                        "safety_stock": None,
                        "order_quantity": None,
                        "model": None,
                    }
                )
                continue

            forecast_total = 0.0
            model = None
            for store_id in stores:
                result = self._forecast.forecast(
                    int(store_id), product.id, window
                )
                forecast_total += sum(day["demand"] for day in result["forecast"])
                model = result["model"]
                if warning is None:
                    warning = result["warning"]

            sigma = self._sigma(history, product.id)
            ss = safety_stock(sigma, window, service_level)
            quantity = order_quantity(
                forecast_total, product.warehouse_quantity, sigma, window,
                service_level,
            )
            rows.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "status": "order" if quantity > 0 else "sufficient",
                    "warehouse_quantity": product.warehouse_quantity,
                    "forecast_demand": round(forecast_total, 1),
                    "safety_stock": round(ss, 1),
                    "order_quantity": quantity,
                    "model": model,
                }
            )

        return {
            "generated_at": datetime.now(UTC),
            "service_level": service_level,
            "lead_time_days": lead_time_days,
            "horizon_days": horizon_days,
            "warning": warning,  # глобален (span-based): одинаков у всех пар
            "recommendations": rows,
        }

    @staticmethod
    def _sigma(history: pd.DataFrame, product_id: int) -> float:
        """σ дневного АГРЕГИРОВАННОГО по магазинам спроса за 28 дней (Q4).

        Меньше двух дней истории → σ неопределима → 0.0: страхового запаса
        нет, заказ опирается только на прогноз (честно, без выдуманной σ).
        """
        daily = (
            history[history["product_id"] == product_id]
            .groupby("date")["demand"]
            .sum()
            .tail(SIGMA_WINDOW_DAYS)
        )
        sigma = float(daily.std())  # ddof=1 — выборочное std
        return 0.0 if math.isnan(sigma) else sigma
