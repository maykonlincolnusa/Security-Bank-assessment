from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score


@dataclass
class FairnessReport:
    by_group: pd.DataFrame
    disparate_impact: float
    equal_opportunity_gap: float


def compute_group_fairness(
    df: pd.DataFrame,
    y_true_col: str,
    y_prob_col: str,
    group_col: str,
    threshold: float = 0.5,
) -> FairnessReport:
    safe = df[[y_true_col, y_prob_col, group_col]].dropna().copy()
    if safe.empty:
        empty = pd.DataFrame(columns=[group_col, "count", "acceptance_rate", "tpr", "accuracy", "roc_auc"])
        return FairnessReport(by_group=empty, disparate_impact=np.nan, equal_opportunity_gap=np.nan)

    safe["y_pred"] = (safe[y_prob_col] >= threshold).astype(int)

    rows: List[Dict] = []
    for group, frame in safe.groupby(group_col):
        y_true = frame[y_true_col].astype(int).to_numpy()
        y_prob = frame[y_prob_col].astype(float).to_numpy()
        y_pred = frame["y_pred"].astype(int).to_numpy()

        acceptance_rate = float(y_pred.mean())
        tpr = float(recall_score(y_true, y_pred, zero_division=0))
        acc = float(accuracy_score(y_true, y_pred))
        auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5

        rows.append(
            {
                group_col: group,
                "count": int(len(frame)),
                "acceptance_rate": acceptance_rate,
                "tpr": tpr,
                "accuracy": acc,
                "roc_auc": auc,
            }
        )

    by_group = pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(drop=True)

    if by_group.empty:
        di = np.nan
        eog = np.nan
    else:
        max_accept = by_group["acceptance_rate"].max()
        min_accept = by_group["acceptance_rate"].min()
        di = float(min_accept / max_accept) if max_accept > 0 else np.nan

        eog = float(by_group["tpr"].max() - by_group["tpr"].min())

    return FairnessReport(by_group=by_group, disparate_impact=di, equal_opportunity_gap=eog)
