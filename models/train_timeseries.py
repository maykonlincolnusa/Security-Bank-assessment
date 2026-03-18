from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


try:
    from prophet import Prophet
except Exception:  # pragma: no cover
    Prophet = None

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None
    nn = None


@dataclass
class LSTMConfig:
    lookback: int = 14
    hidden_dim: int = 32
    epochs: int = 40
    lr: float = 1e-3


class RiskLSTM(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


def forecast_risk_trend(df: pd.DataFrame, date_col: str, value_col: str, periods: int = 30) -> pd.DataFrame:
    if df.empty:
        return df

    safe = df[[date_col, value_col]].dropna().copy()
    safe[date_col] = pd.to_datetime(safe[date_col], errors="coerce")
    safe = safe.dropna().sort_values(date_col)

    if Prophet is not None:
        model = Prophet()
        train = safe.rename(columns={date_col: "ds", value_col: "y"})
        model.fit(train)
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    return _fallback_forecast(safe, date_col, value_col, periods)


def forecast_risk_trend_lstm(df: pd.DataFrame, date_col: str, value_col: str, periods: int = 30, config: LSTMConfig | None = None) -> pd.DataFrame:
    if config is None:
        config = LSTMConfig()

    safe = df[[date_col, value_col]].dropna().copy()
    safe[date_col] = pd.to_datetime(safe[date_col], errors="coerce")
    safe = safe.dropna().sort_values(date_col)

    if len(safe) <= config.lookback or torch is None:
        return _fallback_forecast(safe, date_col, value_col, periods)

    values = safe[value_col].astype(float).to_numpy()
    mu = values.mean()
    sigma = values.std() + 1e-9
    norm = (values - mu) / sigma

    X_seq = []
    y_seq = []
    for i in range(config.lookback, len(norm)):
        X_seq.append(norm[i - config.lookback : i])
        y_seq.append(norm[i])

    X_t = torch.tensor(np.array(X_seq), dtype=torch.float32).unsqueeze(-1)
    y_t = torch.tensor(np.array(y_seq), dtype=torch.float32).unsqueeze(-1)

    model = RiskLSTM(config.hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr)
    loss_fn = nn.MSELoss()

    model.train()
    for _ in range(config.epochs):
        optimizer.zero_grad()
        pred = model(X_t)
        loss = loss_fn(pred, y_t)
        loss.backward()
        optimizer.step()

    model.eval()
    history = list(norm[-config.lookback :])
    preds = []
    with torch.no_grad():
        for _ in range(periods):
            x = torch.tensor(np.array(history[-config.lookback :]), dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
            nxt = float(model(x).item())
            preds.append(nxt * sigma + mu)
            history.append(nxt)

    last_date = pd.to_datetime(safe[date_col].iloc[-1])
    future_dates = pd.date_range(last_date, periods=periods + 1, freq="D")[1:]
    future = pd.DataFrame(
        {
            "ds": future_dates,
            "yhat": preds,
            "yhat_lower": np.array(preds) * 0.95,
            "yhat_upper": np.array(preds) * 1.05,
        }
    )

    hist = safe.rename(columns={date_col: "ds", value_col: "yhat"})
    hist["yhat_lower"] = hist["yhat"]
    hist["yhat_upper"] = hist["yhat"]
    return pd.concat([hist[["ds", "yhat", "yhat_lower", "yhat_upper"]], future], ignore_index=True)


def _fallback_forecast(df: pd.DataFrame, date_col: str, value_col: str, periods: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"])
    safe = df.copy().sort_values(date_col)
    window = min(7, len(safe))
    safe["yhat"] = safe[value_col].rolling(window=window, min_periods=1).mean()
    last_date = pd.to_datetime(safe[date_col].iloc[-1])
    future_dates = pd.date_range(last_date, periods=periods + 1, freq="D")[1:]
    future = pd.DataFrame({"ds": future_dates, "yhat": safe["yhat"].iloc[-1]})
    history = safe[[date_col, value_col]].rename(columns={date_col: "ds", value_col: "yhat"})
    history["yhat_lower"] = history["yhat"]
    history["yhat_upper"] = history["yhat"]
    future["yhat_lower"] = future["yhat"]
    future["yhat_upper"] = future["yhat"]
    return pd.concat([history, future], ignore_index=True)
