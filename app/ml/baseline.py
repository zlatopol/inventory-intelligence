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

def recursive_forecast(
    history: pd.DataFrame,
    forecast_next,
    days: int,
) -> pd.DataFrame:
    """Рекурсивный горизонт над DataFrame-контрактом — ВСЕ пары сразу.

    forecast_next(train) → [PAIR, prediction] на train.max(date)+1;
    прогноз ДОПИСЫВАЕТСЯ в историю как demand (prediction → demand) —
    и так days раз: день D+2 строится по истории, дополненной прогнозом D+1.
    Выход: [date, PAIR, prediction] — days строк НА КАЖДУЮ пару,
    даты подряд от history.max(date)+1.
    """
    extended = history.copy()
    rows = []
    last_date = history["date"].max()
    for offset in range(1, days + 1):
        target = last_date + pd.Timedelta(days=offset)
        prediction = forecast_next(extended).assign(date=target)
        rows.append(prediction[["date"] + PAIR + ["prediction"]])
        extended = pd.concat(
            [
                extended,
                prediction.rename(columns={"prediction": "demand"})[
                    ["date"] + PAIR + ["demand"]
                ],
            ],
            ignore_index=True,
        )
    return pd.concat(rows, ignore_index=True)


def blocked_horizon_evaluate(
    dataset: pd.DataFrame,
    forecast_next,
    anchors: list[pd.Timestamp],
    days: int = 14,
) -> pd.DataFrame:
    """Блочная (эпизодическая) оценка рекурсивного горизонта.

    Для каждого якоря T: история замораживается (строго < T — граница
    утечки = момент прогноза), рекурсивный прогноз уходит на days дней,
    каждый день сверяется с фактом. Выход: [anchor, k, date, PAIR, actual,
    prediction]; k = 1..days — горизонт (1 = первый день после якоря).
    """
    rows = []
    for anchor in anchors:
        history = dataset[dataset["date"] < anchor]
        actual = dataset[
            (dataset["date"] >= anchor)
            & (dataset["date"] < anchor + pd.Timedelta(days=days))
        ][["date"] + PAIR + ["demand"]].rename(columns={"demand": "actual"})
        predicted = recursive_forecast(history, forecast_next, days)
        merged = actual.merge(predicted, on=["date"] + PAIR, how="left")
        merged["k"] = (merged["date"] - anchor).dt.days + 1
        rows.append(merged.assign(anchor=anchor))
    return pd.concat(rows, ignore_index=True)[
        ["anchor", "k", "date", "store_id", "product_id", "actual", "prediction"]
    ]
