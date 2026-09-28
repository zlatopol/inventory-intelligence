"""Unit tests for the MLflow tracking wrapper — tmp store, no real mlruns/."""
import mlflow
import pandas as pd

from app.ml.tracking import log_evaluation


def tmp_store(tmp_path):
    """Изолированный sqlite-стор в tmp (рабочий mlflow.db не трогаем)."""
    return f"sqlite:///{tmp_path / 'mlflow.db'}"


def test_logged_run_stores_params_metrics_and_artifact(tmp_path):
    # ARRANGE
    store = tmp_store(tmp_path)

    # ACT: одна оценка, как из evaluate-скрипта
    predictions = tmp_path / "predictions.csv"
    pd.DataFrame({"actual": [1, 2], "prediction": [1, 2]}).to_csv(predictions, index=False)
    run_id = log_evaluation(
        model_name="naive (вчера)",
        params={"warmup": 7, "dataset_rows": 672},
        metrics={"mae": 3.79, "wape": 21.5},
        predictions_csv=predictions,
        tracking_uri=store,
    )

    # ASSERT: прогон читается из store — params, metrics, artifact на месте
    mlflow.set_tracking_uri(store)
    runs = mlflow.search_runs(experiment_names=["baseline-comparison"])
    row = runs[runs["run_id"] == run_id].iloc[0]

    assert row["params.model"] == "naive (вчера)"
    assert row["params.warmup"] == "7"  # params хранятся строками
    assert row["metrics.mae"] == 3.79
    assert row["metrics.wape"] == 21.5

    artifacts = mlflow.artifacts.list_artifacts(run_id=run_id)
    assert any(a.path == "predictions.csv" for a in artifacts)


def test_each_evaluation_is_a_separate_run(tmp_path):
    # Три оценки → три Run'а в одном эксперименте (история не затирается)
    store = tmp_store(tmp_path)
    for i, name in enumerate(["naive", "snaive", "ma"]):
        log_evaluation(name, {"i": i}, {"mae": float(i)}, tracking_uri=store)

    mlflow.set_tracking_uri(store)
    runs = mlflow.search_runs(experiment_names=["baseline-comparison"])
    assert len(runs) == 3
    assert set(runs["params.model"]) == {"naive", "snaive", "ma"}
