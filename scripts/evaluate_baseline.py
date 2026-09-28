"""Живая оценка baselines на данных из БД (segregated history from seed.py).

Запуск (БД с сид-данными): .venv/bin/python scripts/evaluate_baseline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.ml.baseline import (  # noqa: E402
    moving_average_forecast,
    naive_forecast,
    seasonal_naive_forecast,
    walk_forward_evaluate,
)
from app.ml.dataset import build_demand_dataset, load_shipment_events  # noqa: E402
from app.ml.metrics import mae, wape  # noqa: E402
from app.shared.db import get_engine  # noqa: E402

MODELS = {
    "naive (вчера)": naive_forecast,
    "moving_average_7": moving_average_forecast,
    "seasonal_naive_7": seasonal_naive_forecast,
}


def main() -> None:
    with sessionmaker(bind=get_engine())() as session:
        events = load_shipment_events(session)
    start, end = events["occurred_at"].min().date(), events["occurred_at"].max().date()
    dataset = build_demand_dataset(events, start, end)

    print(f"Датасет: {len(dataset)} строк, {start} → {end}")
    print(f"{'модель':<22} {'MAE (шт)':>10} {'WAPE (%)':>10}")
    for name, model in MODELS.items():
        result = walk_forward_evaluate(dataset, model)
        print(f"{name:<22} {mae(result['actual'], result['prediction']):>10.2f} "
              f"{wape(result['actual'], result['prediction']):>10.1f}")


if __name__ == "__main__":
    main()
