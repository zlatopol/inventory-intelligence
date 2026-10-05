"""Оценка baselines на РЕАЛЬНЫХ данных Kaggle через тот же контракт.

Запуск: .venv/bin/python scripts/evaluate_kaggle.py [max_pairs]
  (по умолчанию 50 пар — быстрый прогон; полный датасет — 500)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.baseline import (  # noqa: E402
    moving_average_forecast,
    naive_forecast,
    seasonal_naive_forecast,
    walk_forward_evaluate,
)
from app.ml.metrics import mae, wape  # noqa: E402
from app.ml.sources import load_from_kaggle_csv  # noqa: E402
from app.ml.tracking import log_evaluation  # noqa: E402

MODELS = {
    "naive (вчера)": naive_forecast,
    "moving_average_7": moving_average_forecast,
    "seasonal_naive_7": seasonal_naive_forecast,
}
WARMUP = 7
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    dataset = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)
    start, end = dataset["date"].min().date(), dataset["date"].max().date()

    # data-version параметры: источник ОБЯЗАН отличать прогоны от seed-данных
    data_params = {
        "source": "kaggle/store-item-demand",
        "max_pairs": max_pairs,
        "dataset_start": str(start),
        "dataset_end": str(end),
        "dataset_rows": len(dataset),
        "warmup": WARMUP,
    }

    print(f"Датасет: {len(dataset)} строк ({max_pairs} пар), {start} → {end}")
    print(f"{'модель':<22} {'MAE (шт)':>10} {'WAPE (%)':>10}  {'run':>10}")
    for name, model in MODELS.items():
        result = walk_forward_evaluate(dataset, model, warmup=WARMUP)
        m, w = mae(result["actual"], result["prediction"]), wape(
            result["actual"], result["prediction"]
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, prefix="predictions_"
        ) as tmp:
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
