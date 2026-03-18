from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Iterable, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit


@dataclass(frozen=True)
class TemporalValidationConfig:
    n_splits: int = 5
    purge_gap: int = 3
    min_train_size: int = 60


class PurgedTimeSeriesSplit:
    """Time-based cross-validation with a purge gap to reduce leakage.

    The splitter expects a dataframe with a date column. Data is sorted by date,
    then each fold reserves a chronological validation window and removes samples
    within `purge_gap` days between train and validation boundaries.
    """

    def __init__(self, n_splits: int = 5, purge_gap: int = 3):
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        self.n_splits = n_splits
        self.purge_gap = max(0, int(purge_gap))

    def split(
        self,
        X: pd.DataFrame,
        date_col: str = "ref_date",
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        if date_col not in X.columns:
            tscv = TimeSeriesSplit(n_splits=self.n_splits)
            for train_idx, test_idx in tscv.split(X):
                yield train_idx, test_idx
            return

        safe = X.copy()
        safe[date_col] = pd.to_datetime(safe[date_col], errors="coerce")
        safe = safe.dropna(subset=[date_col]).sort_values(date_col).reset_index()

        unique_dates = safe[date_col].drop_duplicates().sort_values().to_list()
        if len(unique_dates) <= self.n_splits:
            raise ValueError("Not enough unique dates for temporal CV")

        test_dates_per_fold = max(1, len(unique_dates) // (self.n_splits + 1))

        for fold in range(self.n_splits):
            test_start_pos = (fold + 1) * test_dates_per_fold
            test_end_pos = min(len(unique_dates), test_start_pos + test_dates_per_fold)

            test_dates = set(unique_dates[test_start_pos:test_end_pos])
            if not test_dates:
                continue

            test_start_date = min(test_dates)
            purge_threshold = test_start_date - pd.Timedelta(days=self.purge_gap)

            train_mask = safe[date_col] < purge_threshold
            test_mask = safe[date_col].isin(test_dates)

            train_idx = safe.loc[train_mask, "index"].to_numpy(dtype=int)
            test_idx = safe.loc[test_mask, "index"].to_numpy(dtype=int)

            if len(train_idx) == 0 or len(test_idx) == 0:
                continue

            yield np.sort(train_idx), np.sort(test_idx)


def temporal_train_test_split(
    df: pd.DataFrame,
    date_col: str = "ref_date",
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()

    safe = df.copy()
    if date_col not in safe.columns:
        split_point = int(len(safe) * (1 - test_size))
        return safe.iloc[:split_point].copy(), safe.iloc[split_point:].copy()

    safe[date_col] = pd.to_datetime(safe[date_col], errors="coerce")
    safe = safe.sort_values(date_col).reset_index(drop=True)

    split_point = max(1, int(len(safe) * (1 - test_size)))
    return safe.iloc[:split_point].copy(), safe.iloc[split_point:].copy()


def iter_temporal_windows(
    dates: Iterable[pd.Timestamp],
    train_window: int,
    test_window: int,
) -> Generator[Tuple[pd.Timestamp, pd.Timestamp], None, None]:
    """Utility for sliding-window documentation and experiments."""

    ordered = sorted(pd.to_datetime(list(dates), errors="coerce"))
    ordered = [d for d in ordered if pd.notna(d)]

    for start in range(0, max(0, len(ordered) - train_window - test_window + 1), test_window):
        train_end = ordered[start + train_window - 1]
        test_end = ordered[start + train_window + test_window - 1]
        yield train_end, test_end
