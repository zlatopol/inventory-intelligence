"""Модель спроса: LightGBM поверх фичей из features.py (Phase 2, ML track).

Две реализации одного и того же набора фич:
- build_features(history, day)  — поштучно, для ПРОГНОЗА одного дня
  (защита от утечки «по построению»: история кончается накануне);
- build_training_table(dataset) — векторизованно, для ОБУЧЕНИЯ на всей
  истории (цикл по дням непрактичен: тысячи проходов).

Их согласованность охраняет тест: строка векторизованной таблицы для дня D
обязана совпасть с поштучным build_features для D — иначе одна из двух
реализаций врёт (и где-то утечка или потеря данных).

Правило против утечки в векторизованной версии: shift(1) СНАЧАЛА,
rolling/expanding ПОТОМ — иначе текущий день попадает в собственное окно.
Первые дни пары (лаги NaN) отбрасываются (warmup), а не заполняются
константой: фейковые значения создают модели ложные паттерны на старте.
"""
import pandas as pd
from lightgbm import LGBMRegressor

from app.ml.features import (
    FEATURE_COLUMNS,
    PAIR,
    _holiday_distances,
    build_features,
)

DEFAULT_PARAMS = {
    "objective": "regression",
    "n_estimators": 300,
    "learning_rate": 0.05,
    "verbose": -1,
}


def build_training_table(
    dataset: pd.DataFrame, holiday_days: frozenset = frozenset()
) -> pd.DataFrame:
    """Обучающая таблица: фичи каждого дня — только из его прошлого.

    Выход: [PAIR, date, FEATURE_COLUMNS..., demand]; первые 7 дней каждой
    пары (NaN лагов) отброшены. holiday_days — тот же календарь, что
    в поштучном build_features (и тот же расчёт — оракул сверяет построчно).
    """
    df = dataset.sort_values(PAIR + ["date"]).copy()
    df["dayofweek"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["days_from_start"] = (df["date"] - df["date"].min()).dt.days

    demand = df.groupby(PAIR, sort=False)["demand"]
    # shift(1) ДО rolling/expanding — текущий спрос не попадает в свои окна
    df["lag_1"] = demand.shift(1)
    df["lag_7"] = demand.shift(7)
    df["rolling_mean_7"] = df.groupby(PAIR, sort=False)["demand"].transform(
        lambda s: s.shift(1).rolling(7).mean()
    )
    df["expanding_mean_pair"] = df.groupby(PAIR, sort=False)["demand"].transform(
        lambda s: s.shift(1).expanding().mean()
    )

    # Праздничные дистанции: свойство даты → расчёт тот же, что поштучно
    # (_holiday_distances), по уникальным дням + map (дней ~тысячи, не пары
    # × дни) — согласованность путей по построению, а не по аккуратности.
    to_map: dict = {}
    from_map: dict = {}
    for d in df["date"].unique():
        ts = pd.Timestamp(d)
        to_map[ts], from_map[ts] = _holiday_distances(ts, holiday_days)
    df["days_to_holiday"] = df["date"].map(to_map)
    df["days_from_holiday"] = df["date"].map(from_map)

    table = df.dropna(subset=["lag_7", "rolling_mean_7", "expanding_mean_pair"])
    return table[PAIR + ["date"] + FEATURE_COLUMNS + ["demand"]].reset_index(drop=True)


class LightGBMModel:
    """forecast(train) в контракте walk_forward_evaluate.

    Переобучение — дорого (таблица на всей истории); прогноз — дёшево.
    Поэтому модель кэшируется и переобучается не чаще, чем раз в
    `retrain_every` дней (компромисс из брифа: ежедневно — минуты,
    ежемесячно — секунды; влияние на качество проверяется прогоном).
    """

    def __init__(self, retrain_every: int = 28, params: dict | None = None) -> None:
        self.retrain_every = retrain_every
        self.params = {**DEFAULT_PARAMS, **(params or {})}
        self._regressor: LGBMRegressor | None = None
        self._trained_through: pd.Timestamp | None = None

    def forecast(self, train: pd.DataFrame) -> pd.DataFrame:
        target_day = train["date"].max() + pd.Timedelta(days=1)

        if (
            self._regressor is None
            or (target_day - self._trained_through).days >= self.retrain_every
        ):
            table = build_training_table(train)
            self._regressor = LGBMRegressor(**self.params)
            self._regressor.fit(table[FEATURE_COLUMNS], table["demand"])
            self._trained_through = target_day

        # Прогнозные фичи — поштучным путём (защита от утечки по построению);
        # NaN-ы отдельных лагов LightGBM обрабатывает нативно.
        features = build_features(train, target_day)
        features["prediction"] = self._regressor.predict(features[FEATURE_COLUMNS])
        return features[PAIR + ["prediction"]]
