"""Feature builder (Phase 2, ML track) — каркас.

Архитектура против утечки — ПО ПОСТРОЕНИЮ, не по аккуратности:
фичи дня D считаются из history, которая ЗАКАНЧИВАЕТСЯ накануне (D-1).
Целевого дня в истории нет → lag/rolling не могут «увидеть» ответ.

Каждая фича обоснована разведкой (docs/img/):
- dayofweek, month    ← H1/H3: стабильный недельный профиль, годичный горб
- days_from_start     ← H3: тренд +35%/5лет
- lag_1, lag_7        ← H2: автокорреляция спроса
- rolling_mean_7      ← H2: окно глушит шум дня (0.27)
- expanding_mean_pair ← H4: уровень пары, посчитанный ТОЛЬКО по прошлому
"""
import pandas as pd

PAIR = ["store_id", "product_id"]

FEATURE_COLUMNS = [
    "dayofweek",
    "month",
    "year",
    "days_from_start",
    "lag_1",
    "lag_7",
    "rolling_mean_7",
    "expanding_mean_pair",
]


def history_until(dataset: pd.DataFrame, day) -> pd.DataFrame:
    """ГРАНИЦА ВРЕМЕНИ: всё СТРОГО раньше `day` — единственное, что можно видеть.

    Это Q3, доведённый до API: любой расчёт фич для дня `day` принимает
    на вход результат этой функции — и физически не может подглядеть.
    """
    return dataset[dataset["date"] < pd.Timestamp(day)].copy()


def build_features(history: pd.DataFrame, target_day) -> pd.DataFrame:
    """Одна строка на пару: фичи для target_day, посчитанные из history.

    Контракт: history = history_until(dataset, target_day) — заканчивается
    накануне; target_day в ней отсутствует.
    """
    target = pd.Timestamp(target_day)
    if not history.empty and history["date"].max() >= target:
        raise ValueError(
            f"history содержит {history['date'].max().date()} — не раньше "
            f"target_day {target.date()}: нарушена граница утечки"
        )

    start = history["date"].min()
    pairs = history[PAIR].drop_duplicates()

    # Календарь целевого дня: берётся из самой даты, не из данных —
    # утечь не может в принципе.
    features = pairs.assign(
        dayofweek=target.dayofweek,
        month=target.month,
        year=target.year,
        days_from_start=(target - start).days,
    )

    # last_day = target − 1 при корректном вызове (страж выше это гарантирует).
    last_day = history["date"].max()

    # Спрос пары в конкретную дату: вчера (lag_1) и «тот же день недели
    # неделю назад» (lag_7) — ровно источники naive/seasonal_naive, но
    # как фичи, а не как готовый ответ.
    last_day_demand = (
        history[history["date"] == last_day]
        .set_index(PAIR)["demand"]
        .rename("lag_1")
    )
    lag_7_day = target - pd.Timedelta(days=7)
    lag_7_demand = (
        history[history["date"] == lag_7_day]
        .set_index(PAIR)["demand"]
        .rename("lag_7")
    )

    # Среднее за последние 7 дней истории (окно до last_day включительно);
    # предполагается полная сетка дней (контракт датасета, Q2) — иначе среднее
    # считается по имеющимся дням окна.
    rolling_mean_7 = (
        history[history["date"] > last_day - pd.Timedelta(days=7)]
        .groupby(PAIR)["demand"]
        .mean()
        .rename("rolling_mean_7")
    )

    # Уровень пары: среднее по ВСЕЙ доступной истории пары (только прошлое).
    expanding_mean_pair = (
        history.groupby(PAIR)["demand"].mean().rename("expanding_mean_pair")
    )

    return (
        features.set_index(PAIR)
        .join(last_day_demand, how="left")
        .join(lag_7_demand, how="left")
        .join(rolling_mean_7, how="left")
        .join(expanding_mean_pair, how="left")
        .reset_index()[PAIR + FEATURE_COLUMNS]
    )
