"""Инвентаризационная политика order-up-to — чистая математика (EX-2).

Формула: потребность = F + SS − stock, где
  F  — прогнозный спрос на окно L+H (сумма по парам и дням);
  SS = z·σ·√(L+H) — страховой запас: дисперсии независимых дневных ошибок
      складываются (T·σ²), σ извлекается корнем → σ·√T; z — квантиль нормального
      распределения для уровня сервиса (ЦПТ: сумма многих слагаемых ≈ норма);
  Q  = ceil(потребность), если она > 0, иначе 0 («товара достаточно»).

Тот же модуль используют сервис и backtest-скрипт — ОДНА реализация формулы
(культура репозитория: как с _holiday_distances в ml/features.py).

Дефолты и их обоснование — в docs/requirements.md §8.1 (EX-2).
"""
import math
from statistics import NormalDist

from app.shared.errors import (
    InvalidLeadTimeError,
    InvalidPolicyHorizonError,
    InvalidReplenishmentWindowError,
    InvalidServiceLevelError,
)

DEFAULT_SERVICE_LEVEL = 0.95
DEFAULT_LEAD_TIME_DAYS = 3
DEFAULT_HORIZON_DAYS = 7
MIN_PARAM_DAYS = 1
MAX_WINDOW_DAYS = 14  # = MAX_FORECAST_DAYS — доказанный горизонт модели
SIGMA_WINDOW_DAYS = 28  # окно оценки σ (4 недели)


def validate_params(
    service_level: float, lead_time_days: int, horizon_days: int
) -> None:
    """Правила параметров EX-2; каждому нарушению — своё сообщение (EL-3)."""
    if not 0 < service_level < 1:
        raise InvalidServiceLevelError(service_level)
    if lead_time_days < MIN_PARAM_DAYS:
        raise InvalidLeadTimeError(lead_time_days)
    if horizon_days < MIN_PARAM_DAYS:
        raise InvalidPolicyHorizonError(horizon_days)
    window = lead_time_days + horizon_days
    if window > MAX_WINDOW_DAYS:
        raise InvalidReplenishmentWindowError(
            lead_time_days, horizon_days, MAX_WINDOW_DAYS
        )


def z_score(service_level: float) -> float:
    """Квантиль нормального распределения: SL 0.95 → z ≈ 1.645, 0.99 → 2.326."""
    return NormalDist().inv_cdf(service_level)


def safety_stock(sigma: float, window_days: int, service_level: float) -> float:
    """SS = z·σ·√T. σ — дневная изменчивость; √T — сумма дисперсий независимых дней."""
    return z_score(service_level) * sigma * math.sqrt(window_days)


def order_quantity(
    forecast_demand: float,
    stock: int,
    sigma: float,
    window_days: int,
    service_level: float,
) -> int:
    """Q = ceil(потребность), потребность ≤ 0 → 0 (G5: «достаточно»).

    round(…, 6) — гвардия плавающего шума: без неё 0.1 + 0.2 − 0.3
    (= 5.5e-17) «положительна» и даёт Q = 1 вместо 0.
    """
    need = round(
        forecast_demand
        + safety_stock(sigma, window_days, service_level)
        - stock,
        6,
    )
    return math.ceil(need) if need > 0 else 0
