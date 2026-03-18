from __future__ import annotations

from models.config import load_settings
from models.data import load_curated_tables
from models.synthetic import generate_synthetic_dataset
from models.train_timeseries import forecast_risk_trend, forecast_risk_trend_lstm


def main():
    settings = load_settings()
    tables = load_curated_tables(settings.db_url)
    cve = tables.get("security_cve_daily")
    if cve is None or cve.empty:
        demo = generate_synthetic_dataset(rows=180)
        cve = demo.groupby("ref_date", as_index=False).agg(cve_count=("security_incidents", "sum"))

    prophet_or_fallback = forecast_risk_trend(cve, date_col="ref_date", value_col="cve_count", periods=30)
    lstm_forecast = forecast_risk_trend_lstm(cve, date_col="ref_date", value_col="cve_count", periods=30)

    print("Prophet/fallback forecast:")
    print(prophet_or_fallback.tail())
    print("LSTM/fallback forecast:")
    print(lstm_forecast.tail())


if __name__ == "__main__":
    main()
