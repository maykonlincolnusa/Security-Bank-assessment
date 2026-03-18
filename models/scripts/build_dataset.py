from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from models.config import load_settings
from models.data import load_curated_tables
from models.features import FeatureConfig, build_feature_table
from models.synthetic import generate_synthetic_dataset


def main():
    settings = load_settings()
    output_dir = Path(settings.experiment_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables = load_curated_tables(settings.db_url)
    features = build_feature_table(tables, FeatureConfig())
    if features.empty:
        features = generate_synthetic_dataset()
    elif "trust_label" not in features.columns:
        def _num(col: str) -> pd.Series:
            if col in features.columns:
                return pd.to_numeric(features[col], errors="coerce").fillna(0)
            return pd.Series([0.0] * len(features), index=features.index)

        risk = (
            0.35 * _num("npl_ratio")
            + 0.25 * _num("deposit_volatility")
            + 0.15 * _num("security_incidents")
            + 0.10 * _num("regulatory_risk")
            + 0.15 * _num("downtime_minutes")
            - 0.20 * _num("capital_ratio")
            - 0.10 * _num("roe")
        )
        threshold = np.nanmedian(risk.to_numpy()) if len(risk) else 0.0
        features["trust_label"] = (risk < threshold).astype(int)

    path = output_dir / "training_dataset.csv"
    features.to_csv(path, index=False)
    print(f"Saved dataset to {path}")


if __name__ == "__main__":
    main()
