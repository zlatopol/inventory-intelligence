"""Оценка LightGBM на реальных данных Kaggle: охота за планкой moving_average.

Запуск: .venv/bin/python scripts/evaluate_model.py [max_pairs] [retrain_every]
Планка (50 пар): moving_average_7 — MAE 7.67 / WAPE 16.2%.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.baseline import walk_forward_evaluate  # noqa: E402
from app.ml.features import FEATURE_COLUMNS  # noqa: E402
from app.ml.metrics import mae, wape  # noqa: E402
from app.ml.model import LightGBMModel  # noqa: E402
from app.ml.sources import load_from_kaggle_csv  # noqa: E402
from app.ml.tracking import log_evaluation  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"
# 8, а не 7: lag_7 = shift(7) выкалывает первые 7 дней каждой пары —
# при 7 днях истории обучающая таблица ПУСТА (поймано живым прогоном).
WARMUP = 8


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    retrain_every = int(sys.argv[2]) if len(sys.argv) > 2 else 28

    dataset = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)
    start, end = dataset["date"].min().date(), dataset["date"].max().date()

    model = LightGBMModel(retrain_every=retrain_every)
    result = walk_forward_evaluate(dataset, model.forecast, warmup=WARMUP)
    m, w = mae(result["actual"], result["prediction"]), wape(
        result["actual"], result["prediction"]
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, prefix="predictions_"
    ) as tmp:
        result.to_csv(tmp.name, index=False)
        run_id = log_evaluation(
            model_name="lightgbm",
            params={
                "source": "kaggle/store-item-demand",
                "max_pairs": max_pairs,
                "retrain_every": retrain_every,
                "features": 8,
                "dataset_start": str(start),
                "dataset_end": str(end),
                "warmup": WARMUP,
            },
            metrics={"mae": m, "wape": w},
            predictions_csv=Path(tmp.name),
        )

    print(f"Датасет: {len(dataset)} строк ({max_pairs} пар), {start} → {end}")
    print(f"{'модель':<22} {'MAE (шт)':>10} {'WAPE (%)':>10}  {'run':>10}")
    print(f"{'lightgbm':<22} {m:>10.2f} {w:>10.1f}  {run_id[:8]:>10}")
    print("\nПланка: moving_average_7 — MAE 7.67 / WAPE 16.2")

    # --- Какие гипотезы оплатились: важности фичей --------------------
    print("\nFeature importance (гипотезы H1–H4):")
    importances = sorted(
        zip(FEATURE_COLUMNS, model._regressor.feature_importances_),
        key=lambda kv: -kv[1],
    )
    total = sum(value for _, value in importances)
    for name, value in importances:
        share = value / total * 100
        print(f"  {name:<20} {share:5.1f}%  {'#' * int(share)}")

    # --- Разбор ошибок: где модель ошибается сильнее ------------------
    result["abs_error"] = (result["actual"] - result["prediction"]).abs()
    by_dow = result.groupby(result["date"].dt.dayofweek)["abs_error"].mean()
    print("\nMAE по дням недели (пн=0):")
    for i, value in by_dow.items():
        print(f"  {['пн','вт','ср','чт','пт','сб','вс'][i]}: {value:5.2f}  "
              f"{'#' * int(value)}")

    worst = (
        result.groupby(["store_id", "product_id"])["abs_error"]
        .mean().nlargest(3).round(2)
    )
    print("\nХудшие пары (MAE):", dict(worst))


if __name__ == "__main__":
    main()
