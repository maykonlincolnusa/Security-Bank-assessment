import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSettings:
    db_url: str
    experiment_dir: str
    random_seed: int


def load_settings() -> ModelSettings:
    return ModelSettings(
        db_url=os.getenv("ETL_DB_URL", "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"),
        experiment_dir=os.getenv("MODEL_EXPERIMENT_DIR", "models/output"),
        random_seed=int(os.getenv("MODEL_RANDOM_SEED", "42")),
    )
