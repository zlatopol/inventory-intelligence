"""ForecastService — прогноз спроса как сервис (Phase 3: model as a service).

Дизайн-решения (Q&A 2026-10-08):
- Q1: модель кэшируется, переобучается по TTL (данные меняются не лавинообразно)
  + ручной форс-мажор вариант — retrain(force=True) (эндпоинт /forecast/retrain);
- Q2: при истории < MIN_HISTORY_DAYS отдаём BASELINE (moving-average) с честной
  пометкой model/warning — baseline это легитимная модель для малых данных,
  а не «слабый lightgbm»; данные копятся, сервис сам переходит на модель;
- Q3: горизонт по умолчанию 2–4 дня (параметр days, 1–14).

Горизонт — рекурсивно: фичи дня D+2 строятся по истории, дополненной
прогнозом D+1 (prediction-лаги). Источник истории — ЗАГРУЗЧИК (внедрённая
зависимость): в проде — события нашей системы, в тестах — синтетика.

Праздничный календарь (days_to/from_holiday): СОЗНАТЕЛЬНО не инжектируется —
пустой календарь даёт HOLIDAY_FAR (фича вырождена, вреда нет). RU-сид
праздничного сигнала не содержит. КОГДА накопится реальная RU-история —
передавать frozenset дат (holidays.country_holidays("RU"), годы с запасом +2)
в build_training_table/build_features ниже; без запаса лет фича молча
выродится в 999 (см. комментарий у HOLIDAY_FAR в app/ml/features.py).
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pandas as pd
from lightgbm import LGBMRegressor

from app.ml.features import FEATURE_COLUMNS, build_features
from app.ml.model import DEFAULT_PARAMS, build_training_table
from app.shared.errors import InvalidForecastHorizonError

MIN_HISTORY_DAYS = 30
MIN_FORECAST_DAYS = 1
MAX_FORECAST_DAYS = 14
BASELINE_TAG = "baseline_moving_average_7"
MODEL_TAG = "lightgbm"


class ForecastService:
    def __init__(
        self,
        history_loader: Callable[[], pd.DataFrame],
        min_history_days: int = MIN_HISTORY_DAYS,
        retrain_ttl_hours: int = 72,
    ) -> None:
        self._loader = history_loader
        self._min_history_days = min_history_days
        self._retrain_ttl = timedelta(hours=retrain_ttl_hours)
        self._model: LGBMRegressor | None = None
        self._trained_at: datetime | None = None
        self._lock = threading.Lock()  # sync-эндпоинты идут из threadpool'а

    # --- публичное ------------------------------------------------------------

    def forecast(self, store_id: int, product_id: int, days: int) -> dict:
        if not (MIN_FORECAST_DAYS <= days <= MAX_FORECAST_DAYS):
            raise InvalidForecastHorizonError(days, MIN_FORECAST_DAYS, MAX_FORECAST_DAYS)

        history = self._loader()
        pair_history = history[
            (history["store_id"] == store_id)
            & (history["product_id"] == product_id)
        ]
        if pair_history.empty:
            raise LookupError(  # роутер переведёт в 404
                f"В истории событий нет пары store={store_id}, product={product_id}"
            )

        span_days = (history["date"].max() - history["date"].min()).days
        use_model = span_days >= self._min_history_days

        warning = None
        predictor = self._baseline_prediction
        if use_model:
            self._ensure_model(history)
            predictor = self._model_prediction
        else:
            warning = (
                f"история {span_days} дн. < {self._min_history_days}: прогноз "
                f"даёт baseline, модель включится при накоплении данных"
            )

        # Рекурсивный горизонт: каждый следующий день прогнозируется по истории,
        # дополненной предыдущими прогнозами.
        extended = history.copy()
        rows = []
        last_date = history["date"].max()
        for offset in range(1, days + 1):
            target = last_date + pd.Timedelta(days=offset)
            prediction = predictor(extended, store_id, product_id, target)
            rows.append({"date": target, "demand": round(float(prediction), 1)})
            extended = pd.concat(
                [
                    extended,
                    pd.DataFrame(
                        {
                            "date": [target],
                            "store_id": [store_id],
                            "product_id": [product_id],
                            "demand": [prediction],
                        }
                    ),
                ],
                ignore_index=True,
            )

        return {
            "store_id": store_id,
            "product_id": product_id,
            "generated_at": datetime.now(UTC),
            "model": MODEL_TAG if use_model else BASELINE_TAG,
            "warning": warning,
            "forecast": rows,
        }

    def retrain(self, force: bool = False) -> dict:
        """Ручное переобучение (форс-мажор по решению Q1)."""
        with self._lock:
            history = self._loader()
            table = build_training_table(history)
            self._model = LGBMRegressor(**DEFAULT_PARAMS)
            self._model.fit(table[FEATURE_COLUMNS], table["demand"])
            self._trained_at = datetime.now(UTC)
        return {"status": "retrained", "trained_at": self._trained_at}

    # --- внутреннее -----------------------------------------------------------

    def _ensure_model(self, history: pd.DataFrame) -> None:
        with self._lock:
            stale = (
                self._trained_at is None
                or (datetime.now(UTC) - self._trained_at) > self._retrain_ttl
            )
            if stale or self._model is None:
                table = build_training_table(history)
                self._model = LGBMRegressor(**DEFAULT_PARAMS)
                self._model.fit(table[FEATURE_COLUMNS], table["demand"])
                self._trained_at = datetime.now(UTC)

    def _model_prediction(
        self, history: pd.DataFrame, store_id: int, product_id: int, target
    ) -> float:
        features = build_features(history, target)
        row = features[
            (features["store_id"] == store_id) & (features["product_id"] == product_id)
        ]
        return float(self._model.predict(row[FEATURE_COLUMNS])[0])

    @staticmethod
    def _baseline_prediction(
        history: pd.DataFrame, store_id: int, product_id: int, target
    ) -> float:
        """Moving-average: среднее последних 7 дней пары (окно до target)."""
        pair = history[
            (history["store_id"] == store_id)
            & (history["product_id"] == product_id)
        ]
        window = pair[pair["date"] < pd.Timestamp(target)].tail(7)
        return float(window["demand"].mean())
