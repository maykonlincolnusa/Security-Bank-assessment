from __future__ import annotations

from pathlib import Path

import pandas as pd

from models.config import load_settings
from models.data import load_curated_tables
from models.features import FeatureConfig, build_feature_table
from models.synthetic import generate_synthetic_dataset


def main() -> None:
    settings = load_settings()
    output_dir = Path(settings.experiment_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables = load_curated_tables(settings.db_url)
    features = build_feature_table(tables, FeatureConfig())

    if features.empty:
        features = generate_synthetic_dataset()

    # Mark unavailable private sources explicitly for auditability.
    if "private_source_status" not in features.columns:
        features["private_source_status"] = "nao especificado"

    path = output_dir / "training_dataset.csv"
    features.to_csv(path, index=False)

    print(f"Saved dataset to {path}")
    print(f"Rows={len(features)}, Cols={len(features.columns)}")


if __name__ == "__main__":
    main()
