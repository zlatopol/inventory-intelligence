"""Baselines спроса (Phase 2, ML track) — планка для будущих моделей.

Контракт модели: forecast(train) → DataFrame[store_id, product_id, prediction],
где prediction — прогноз на СЛЕДУЮЩИЙ день после train.max(date).
По сетке данных предполагается полнота (Q2) — пропущенных паро-дней нет.
"""
import pandas as pd

PAIR = ["store_id", "product_id"]


def naive_forecast(train: pd.DataFrame) -> pd.DataFrame:
    """Завтра = вчера: последнее наблюдение каждой пары."""
    last = (
        train.sort_values("date")
        .groupby(PAIR, as_index=False)
        .tail(1)[PAIR + ["demand"]]
        .rename(columns={"demand": "prediction"})
    )
    return last[PAIR + ["prediction"]]


def seasonal_naive_forecast(train: pd.DataFrame, lag: int = 7) -> pd.DataFrame:
    """Завтра = тот же день прошлой недели (лаг 7 = недельная сезонность).

    Целевой день = train.max(date) + 1; берём значение пары в день (цель − lag).
    """
    target_day = train["date"].max() + pd.Timedelta(days=1)
    lookback_day = target_day - pd.Timedelta(days=lag)
    history = train[train["date"] == lookback_day][PAIR + ["demand"]]
    return history.rename(columns={"demand": "prediction"})[PAIR + ["prediction"]]


def moving_average_forecast(train: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Среднее за последние `window` дней пары (окно 7 = ровно одна неделя)."""
    means = (
        train.sort_values("date")
        .groupby(PAIR)["demand"]
        .apply(lambda series: series.tail(window).mean())
        .reset_index()
        .rename(columns={"demand": "prediction"})
    )
    return means[PAIR + ["prediction"]]


def walk_forward_evaluate(
    dataset: pd.DataFrame,
    forecast,
    warmup: int = 7,
) -> pd.DataFrame:
    """Скользящая (walk-forward) валидация — Q3 в жёсткой форме.

    Для каждого оценочного дня D: train = всё СТРОГО до D (граница утечки =
    момент прогноза), предсказываем D, сверяем с фактом. Один split —
    одна цифра; walk-forward — кривая честности по всей истории.
    """
    dates = sorted(dataset["date"].unique())
    rows = []
    for day in dates[warmup:]:
        train = dataset[dataset["date"] < day]
        actual = dataset[dataset["date"] == day][PAIR + ["demand"]].rename(
            columns={"demand": "actual"}
        )
        predicted = forecast(train)
        merged = actual.merge(predicted, on=PAIR, how="left")
        rows.append(merged.assign(date=day))
    return pd.concat(rows, ignore_index=True)[
        ["date", "store_id", "product_id", "actual", "prediction"]
    ]
