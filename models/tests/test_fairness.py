import pandas as pd

from models.fairness import compute_group_fairness


def test_compute_group_fairness_returns_table():
    df = pd.DataFrame(
        {
            "trust_label": [1, 0, 1, 0, 1, 1],
            "score_prob": [0.9, 0.2, 0.8, 0.3, 0.7, 0.6],
            "region": ["sudeste", "sudeste", "sul", "sul", "nordeste", "nordeste"],
        }
    )

    report = compute_group_fairness(df, "trust_label", "score_prob", "region")
    assert not report.by_group.empty
    assert "acceptance_rate" in report.by_group.columns
