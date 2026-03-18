from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class PreprocessConfig:
    target_col: str = "trust_label"
    id_col: str = "bank_id"
    missing_strategy: str = "median"  # median | mean | knn
    add_missing_flags: bool = True


class MissingFlagTransformer(BaseEstimator, TransformerMixin):
    """Add binary indicators for missingness before imputation."""

    def __init__(self, columns: List[str]):
        self.columns = columns

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        safe = pd.DataFrame(X).copy()
        for col in self.columns:
            if col in safe.columns:
                safe[f"{col}_is_missing"] = safe[col].isna().astype(int)
        return safe


class GroupMedianImputer(BaseEstimator, TransformerMixin):
    """Simple group-wise imputer for homogeneous-bank segments.

    If the grouping column is not available, falls back to global median.
    """

    def __init__(self, group_col: str = "bank_size_cluster"):
        self.group_col = group_col
        self.global_medians_: dict = {}
        self.group_medians_: dict = {}

    def fit(self, X, y=None):
        safe = pd.DataFrame(X).copy()
        numeric_cols = safe.select_dtypes(include=[np.number]).columns.tolist()
        self.global_medians_ = {c: float(safe[c].median()) for c in numeric_cols}

        if self.group_col in safe.columns:
            grouped = safe.groupby(self.group_col)
            self.group_medians_ = {
                group: frame[numeric_cols].median(numeric_only=True).to_dict()
                for group, frame in grouped
            }
        return self

    def transform(self, X):
        safe = pd.DataFrame(X).copy()
        numeric_cols = safe.select_dtypes(include=[np.number]).columns.tolist()

        for col in numeric_cols:
            if self.group_col in safe.columns and self.group_medians_:
                safe[col] = safe.apply(
                    lambda row: row[col]
                    if pd.notna(row[col])
                    else self.group_medians_.get(row.get(self.group_col), {}).get(col, self.global_medians_.get(col, 0.0)),
                    axis=1,
                )
            else:
                safe[col] = safe[col].fillna(self.global_medians_.get(col, 0.0))

        return safe


def build_preprocess_pipeline(
    df: pd.DataFrame,
    target_col: str,
    config: Optional[PreprocessConfig] = None,
) -> Tuple[Pipeline, List[str]]:
    cfg = config or PreprocessConfig(target_col=target_col)

    feature_cols = [c for c in df.columns if c != target_col]
    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]

    numeric_imputer = _build_numeric_imputer(cfg.missing_strategy)
    numeric_steps = [
        ("imputer", numeric_imputer),
        ("scaler", StandardScaler()),
    ]

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    transformers = [("num", Pipeline(steps=numeric_steps), numeric_cols)]
    if categorical_cols:
        transformers.append(("cat", categorical_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    pipeline = Pipeline(steps=[("preprocess", preprocessor)])
    return pipeline, feature_cols


def split_xy(df: pd.DataFrame, target_col: str):
    X = df.drop(columns=[target_col])
    y = df[target_col].astype(int)
    return X, y


def prepare_feature_frame(
    df: pd.DataFrame,
    target_col: str = "trust_label",
    add_missing_flags: bool = True,
) -> pd.DataFrame:
    safe = df.copy()
    numeric_cols = safe.drop(columns=[target_col], errors="ignore").select_dtypes(include=[np.number]).columns

    if add_missing_flags:
        for col in numeric_cols:
            safe[f"{col}_is_missing"] = safe[col].isna().astype(int)
    return safe


def _build_numeric_imputer(strategy: str):
    strategy = (strategy or "median").lower()
    if strategy == "knn":
        return KNNImputer(n_neighbors=5)
    if strategy == "mean":
        return SimpleImputer(strategy="mean")
    return SimpleImputer(strategy="median")
