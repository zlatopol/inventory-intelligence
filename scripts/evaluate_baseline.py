"""Живая оценка baselines на данных из БД + MLflow-трекинг каждого прогона.

Запуск (БД с сид-данными): .venv/bin/python scripts/evaluate_baseline.py
Просмотр прогонов: .venv/bin/mlflow ui --port 5000 → http://localhost:5000
"""
import sys
import tempfile
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
from app.ml.tracking import log_evaluation  # noqa: E402
from app.shared.db import get_engine  # noqa: E402

MODELS = {
    "naive (вчера)": naive_forecast,
    "moving_average_7": moving_average_forecast,
    "seasonal_naive_7": seasonal_naive_forecast,
}
WARMUP = 7


def main() -> None:
    with sessionmaker(bind=get_engine())() as session:
        events = load_shipment_events(session)
    start, end = events["occurred_at"].min().date(), events["occurred_at"].max().date()
    dataset = build_demand_dataset(events, start, end)

    # Границы датасета — наша «версия данных»: два прогона на разных данных
    # нельзя сравнивать, не зная этого (параметр в каждом Run).
    data_params = {
        "dataset_start": str(start),
        "dataset_end": str(end),
        "dataset_rows": len(dataset),
        "warmup": WARMUP,
    }

    print(f"Датасет: {len(dataset)} строк, {start} → {end}")
    print(f"{'модель':<22} {'MAE (шт)':>10} {'WAPE (%)':>10}  {'run':>10}")
    for name, model in MODELS.items():
        result = walk_forward_evaluate(dataset, model, warmup=WARMUP)
        m, w = mae(result["actual"], result["prediction"]), wape(
            result["actual"], result["prediction"]
        )
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            result.to_csv(tmp.name, index=False)
            run_id = log_evaluation(
                model_name=name,
                params=data_params,
                metrics={"mae": m, "wape": w},
                predictions_csv=Path(tmp.name),
            )
        print(f"{name:<22} {m:>10.2f} {w:>10.1f}  {run_id[:8]:>10}")


if __name__ == "__main__":
    main()
