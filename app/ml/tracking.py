"""MLflow experiment tracking (Phase 2, ML track).

Хранилище: локальный sqlite-файл (mlflow.db) — MLflow 3.x перевёл файловый
backend (mlruns/) в maintenance mode (исключение при использовании), а sqlite
остаётся рекомендованным zero-infra вариантом. Артефакты — каталог рядом
со стором (mlartifacts/), чтобы тесты с tmp-стором были полностью изолированы.

Словарь MLflow: Experiment — группа прогонов; Run — одна оценка;
params — что влило (конфиг + границы датасета = наша версия данных),
metrics — что вышло (MAE/WAPE), artifacts — файлы (прогнозы CSV).

UI: .venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow.db
"""
from contextlib import contextmanager
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACKING_URI = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
EXPERIMENT = "baseline-comparison"


def _artifact_root_for(tracking_uri: str) -> str:
    """Артефакты живут рядом со стором: sqlite:///X/mlflow.db → X/mlartifacts."""
    path = Path(tracking_uri.removeprefix("sqlite:///")).parent
    return (path / "mlartifacts").as_uri()


@contextmanager
def run(experiment: str = EXPERIMENT, tracking_uri: str | None = None):
    """Контекст одного Run'а; эксперимент создаётся с явным artifact-root."""
    uri = tracking_uri or DEFAULT_TRACKING_URI
    mlflow.set_tracking_uri(uri)
    client = MlflowClient()
    existing = client.get_experiment_by_name(experiment)
    if existing is None:
        experiment_id = client.create_experiment(
            experiment, artifact_location=_artifact_root_for(uri)
        )
    else:
        experiment_id = existing.experiment_id
    with mlflow.start_run(experiment_id=experiment_id):
        yield mlflow.active_run()


def log_evaluation(
    model_name: str,
    params: dict,
    metrics: dict,
    predictions_csv: Path | None = None,
    tracking_uri: str | None = None,
) -> str:
    """Записать одну оценку; возвращает run_id (ссылка на прогон)."""
    with run(tracking_uri=tracking_uri) as active:
        mlflow.log_params({"model": model_name, **params})
        mlflow.log_metrics(metrics)
        if predictions_csv is not None and predictions_csv.exists():
            mlflow.log_artifact(str(predictions_csv))
        return active.info.run_id
