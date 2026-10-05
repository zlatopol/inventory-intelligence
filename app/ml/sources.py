"""Источники данных для ML — два адаптера с единым контрактом выхода.

Выход всегда: [date (datetime64), store_id, product_id, demand],
отсортировано по трём колонкам, индекс сброшен. Оба адаптера взаимозаменяемы:
evaluate-скрипт не знает, откуда данные (наша система / Kaggle).
"""
import pandas as pd

from app.ml.dataset import load_shipment_events

CONTRACT_COLUMNS = ["date", "store_id", "product_id", "demand"]


def load_from_stock_event(session, start=None, end=None) -> pd.DataFrame:
    """Спрос из событий НАШЕЙ системы (stock_event, ADR-0006)."""
    events = load_shipment_events(session)
    if start is not None:
        events = events[events["occurred_at"] >= pd.Timestamp(start)]
    if end is not None:
        events = events[events["occurred_at"] <= pd.Timestamp(end)]
    dataset = events.rename(
        columns={"occurred_at": "date", "quantity": "demand"}
    )
    return (
        dataset[CONTRACT_COLUMNS]
        .sort_values(CONTRACT_COLUMNS[:3])
        .reset_index(drop=True)
    )


def load_from_kaggle_csv(path, start=None, end=None, max_pairs=None) -> pd.DataFrame:
    """Спрос из CSV соревнования «Store Item Demand».

    max_pairs — первые N ПАР (store, item) в детерминированном (sorted) порядке:
    «первые N строк» дало бы одну-две пары за пару дней — прогоны несравнимы.
    """
    df = pd.read_csv(path, parse_dates=["date"])

    required = {"date", "store", "item", "sales"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Kaggle CSV: ожидались колонки {sorted(required)}, "
            f"отсутствуют {sorted(missing)}"
        )

    df = df.rename(
        columns={"store": "store_id", "item": "product_id", "sales": "demand"}
    )
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)]
    if max_pairs is not None:
        first_pairs = sorted(
            df[["store_id", "product_id"]].drop_duplicates().itertuples(
                index=False, name=None
            )
        )[:max_pairs]
        df = df[df.set_index(["store_id", "product_id"]).index.isin(first_pairs)]

    return (
        df[CONTRACT_COLUMNS]
        .sort_values(CONTRACT_COLUMNS[:3])
        .reset_index(drop=True)
    )