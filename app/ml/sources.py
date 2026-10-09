"""Источники данных для ML — два адаптера с единым контрактом выхода.

Выход всегда: [date (datetime64, наивная полночь в бизнес-таймзоне), store_id,
product_id, demand] — по одной строке на (пара, день), полная сетка с нулями
(контракт датасета, Q1–Q3), отсортировано по трём колонкам, индекс сброшен.
Оба адаптера взаимозаменяемы: evaluate-скрипт не знает, откуда данные
(наша система / Kaggle).

Граница дня = бизнес-таймзона (ADR-0007): stock_event хранит МОМЕНТ (UTC),
днём спроса события считается его локальный календарный день. Kaggle-CSV уже
дневной — конвертация там не нужна.
"""
import pandas as pd

from app.ml.dataset import build_demand_dataset, load_shipment_events
from app.shared.config import get_settings

CONTRACT_COLUMNS = ["date", "store_id", "product_id", "demand"]


def _empty_demand() -> pd.DataFrame:
    """Пустой выход контракта (событий нет) — с честными dtype колонок."""
    return pd.DataFrame(
        {
            "date": pd.Series(dtype="datetime64[ns]"),
            "store_id": pd.Series(dtype="int64"),
            "product_id": pd.Series(dtype="int64"),
            "demand": pd.Series(dtype="int64"),
        }
    )


def load_from_stock_event(session, start=None, end=None) -> pd.DataFrame:
    """Спрос из событий НАШЕЙ системы (stock_event, ADR-0006).

    События → дневной спрос: локальный день события (ADR-0007), сумма
    количества по (день, пара), досыпка нулевых дней сеткой. Фильтры
    start/end действуют на ЛОКАЛЬНЫЙ день, границы включительно.
    """
    events = load_shipment_events(session)
    if events.empty:
        return _empty_demand()

    # Порядок обязателен: tz_convert ДО tz_localize(None) — сброс зоны первым
    # принял бы UTC за локальное время и уложил ночь во «вчера».
    local_days = (
        pd.to_datetime(events["occurred_at"], utc=True)
        .dt.tz_convert(get_settings().business_timezone)
        .dt.tz_localize(None)
        .dt.normalize()  # день события = локальная полночь
    )
    events = events.assign(occurred_at=local_days)

    if start is not None:
        events = events[events["occurred_at"] >= pd.Timestamp(start)]
    if end is not None:
        events = events[events["occurred_at"] <= pd.Timestamp(end)]
    if events.empty:
        return _empty_demand()

    # Сетка = наблюдаемый период (или заданные границы); нули досыпает
    # build_demand_dataset — Q2: иначе средние систематически завышены.
    grid_start = start or events["occurred_at"].min().date()
    grid_end = end or events["occurred_at"].max().date()
    return build_demand_dataset(events, grid_start, grid_end)


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