"""Demand dataset over stock_event (Phase 2, ML track).

Контракт зафиксирован дизайн-Q&A (2026-09-25):
- Q1: гранулярность — ДЕНЬ (сезонность у нас дневная);
- Q2: нулевые строки СОЗДАЮТСЯ (полная сетка пара × день) — иначе средняя
  систематически завышена (intermittent demand);
- Q3: только хронологические разрезы; граница утечки = момент прогноза
  (предсказывая день D+1 в конце дня D, день D использовать МОЖНО — он прошло).
"""
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import StockEvent

DEMAND_COLUMNS = ["date", "store_id", "product_id", "demand"]


def load_shipment_events(session: Session) -> pd.DataFrame:
    """ADR-0006: события — источник правды; берём только shipment (спрос)."""
    rows = session.execute(
        select(
            StockEvent.occurred_at,
            StockEvent.store_id,
            StockEvent.product_id,
            StockEvent.quantity,
        )
        .where(StockEvent.event_type == "shipment")
        .order_by(StockEvent.occurred_at)
    ).all()
    return pd.DataFrame(rows, columns=["occurred_at", "store_id", "product_id", "quantity"])


def build_demand_dataset(
    events: pd.DataFrame, start: date, end: date
) -> pd.DataFrame:
    """Агрегирует события до (день, магазин, товар) → спрос; досыпает нули.

    Сетка: все пары (встреченные в events) × все дни [start, end] —
    отсутствующая пара получает demand=0 (Q2).
    """
    events = events.assign(
        # psycopg returns tz-aware datetimes, the grid index is naive —
        # drop the zone before normalizing, or reindex matches NOTHING
        # (and silently fills zeros: the bug caught by the weekday check).
        date=pd.to_datetime(events["occurred_at"]).dt.tz_localize(None).dt.normalize()
    )
    daily = events.groupby(
        ["date", "store_id", "product_id"], as_index=False
    )["quantity"].sum()
    full_grid = pd.MultiIndex.from_product(
        [
            pd.date_range(start, end, freq="D"),
            sorted(events["store_id"].unique()),
            sorted(events["product_id"].unique()),
        ],
        names=["date", "store_id", "product_id"],
    )
    dataset = (
        daily.set_index(["date", "store_id", "product_id"])
        .reindex(full_grid, fill_value=0)
        .reset_index()
        .rename(columns={"quantity": "demand"})
    )
    return dataset[DEMAND_COLUMNS].sort_values(["date", "store_id", "product_id"]).reset_index(drop=True)


def chronological_split(
    dataset: pd.DataFrame, split_date: date
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Q3: train — строго ДО split_date, test — с split_date включительно.

    Граница = момент прогноза: всё, что правее, — «будущее», недоступно фичам.
    """
    ts = pd.Timestamp(split_date)
    train = dataset[dataset["date"] < ts]
    test = dataset[dataset["date"] >= ts]
    return train, test
