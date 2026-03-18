import pandas as pd

from models.features import FeatureConfig, build_feature_table


def test_build_feature_table_includes_requested_domains():
    tables = {
        "open_banking_accounts": pd.DataFrame({"bank_id": ["001"], "ref_date": ["2024-01-01"]}),
        "open_banking_balances": pd.DataFrame(
            {
                "bank_id": ["001", "001"],
                "ref_date": ["2024-01-01", "2024-01-02"],
                "available_amount": [100.0, 120.0],
            }
        ),
        "financial_statements": pd.DataFrame(
            {
                "bank_id": ["001"],
                "ref_date": ["2024-01-02"],
                "total_assets": [1000.0],
                "total_liabilities": [800.0],
                "current_assets": [500.0],
                "current_liabilities": [250.0],
                "net_income": [80.0],
                "equity": [200.0],
                "non_performing_loans": [20.0],
                "total_loans": [500.0],
            }
        ),
        "regulatory_events": pd.DataFrame(
            {
                "bank_id": ["001", "001"],
                "ref_date": ["2024-01-02", "2024-01-02"],
                "event_type": ["warning", "penalty"],
            }
        ),
        "news_sentiment_daily": pd.DataFrame(
            {
                "ref_date": ["2024-01-02"],
                "avg_sentiment": [-0.5],
                "negative_volume": [10],
            }
        ),
        "security_cve_daily": pd.DataFrame({"ref_date": ["2024-01-02"], "cve_count": [4]}),
        "operational_telemetry": pd.DataFrame(
            {"bank_id": ["001"], "ref_date": ["2024-01-02"], "downtime_minutes": [30]}
        ),
    }

    df = build_feature_table(tables, FeatureConfig())

    assert not df.empty
    expected_cols = {
        "capital_ratio",
        "liquidity_ratio",
        "roe",
        "npl_ratio",
        "deposit_volatility",
        "regulatory_risk",
        "avg_sentiment",
        "negative_volume",
        "security_incidents",
        "downtime_minutes",
    }
    assert expected_cols.issubset(set(df.columns))
