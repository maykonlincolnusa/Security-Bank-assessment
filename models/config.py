import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSettings:
    db_url: str
    experiment_dir: str
    random_seed: int
    mlflow_tracking_uri: str
    dvc_remote: str
    default_model_set: str
    default_missing_strategy: str
    default_cv_mode: str
    default_cost_fp: float
    default_cost_fn: float


def load_settings() -> ModelSettings:
    return ModelSettings(
        db_url=os.getenv("ETL_DB_URL", "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"),
        experiment_dir=os.getenv("MODEL_EXPERIMENT_DIR", "models/output"),
        random_seed=int(os.getenv("MODEL_RANDOM_SEED", "42")),
        mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI", ""),
        dvc_remote=os.getenv("DVC_REMOTE", "nao_especificado"),
        default_model_set=os.getenv("MODEL_SET", "all"),
        default_missing_strategy=os.getenv("MISSING_STRATEGY", "median"),
        default_cv_mode=os.getenv("CV_MODE", "purged"),
        default_cost_fp=float(os.getenv("COST_FP", "1.0")),
        default_cost_fn=float(os.getenv("COST_FN", "5.0")),
    )
