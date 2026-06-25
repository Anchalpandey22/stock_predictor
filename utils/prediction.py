"""
prediction.py
--------------
Simple next-day price prediction using Linear Regression and Random
Forest Regression. This is intentionally a basic, transparent approach
(lag features + day index) rather than a deep learning model - it's meant
to demonstrate the ML workflow end-to-end (train/test split, fit,
evaluate, predict) for a student project, NOT to be used for real trading
decisions. See the disclaimer shown on the AI Prediction page.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


def build_features(df: pd.DataFrame, n_lags: int = 5) -> pd.DataFrame:
    """Builds a simple supervised-learning table: lagged closing prices
    plus a couple of rolling stats as features, with 'Target' = next day's
    close."""
    data = df[["Date", "Close"]].copy().reset_index(drop=True)
    for lag in range(1, n_lags + 1):
        data[f"lag_{lag}"] = data["Close"].shift(lag)
    data["rolling_mean_5"] = data["Close"].rolling(5).mean()
    data["rolling_std_5"] = data["Close"].rolling(5).std()
    data["day_index"] = np.arange(len(data))
    data["Target"] = data["Close"].shift(-1)  # next day's close
    data = data.dropna().reset_index(drop=True)
    return data


def train_and_predict(df: pd.DataFrame, model_type: str = "Linear Regression", n_lags: int = 5):
    """
    Trains the chosen model on historical data and returns a results dict:
        - dates, actual, predicted  -> for the test-set actual-vs-predicted chart
        - mae, r2                   -> evaluation metrics on the test set
        - next_day_prediction       -> forecast for the next trading day
        - model_name
    Returns None if there isn't enough data to train on.
    """
    feat = build_features(df, n_lags=n_lags)
    if len(feat) < 30:
        return None

    feature_cols = [c for c in feat.columns if c.startswith("lag_") or c in (
        "rolling_mean_5", "rolling_std_5", "day_index")]
    X = feat[feature_cols].values
    y = feat["Target"].values
    dates = feat["Date"].values

    X_train, X_test, y_train, y_test, dates_train, dates_test = train_test_split(
        X, y, dates, test_size=0.2, shuffle=False
    )

    if model_type == "Random Forest":
        model = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    else:
        model = LinearRegression()

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds) if len(y_test) > 1 else float("nan")

    # Forecast the very next trading day using the most recent feature row
    last_row = feat[feature_cols].iloc[[-1]].values
    next_day_pred = float(model.predict(last_row)[0])

    return {
        "model_name": model_type,
        "dates": dates_test,
        "actual": y_test,
        "predicted": preds,
        "mae": mae,
        "r2": r2,
        "next_day_prediction": next_day_pred,
        "last_actual_close": float(feat["Close"].iloc[-1]),
    }


def trend_label(last_close: float, next_pred: float) -> str:
    diff_pct = (next_pred - last_close) / last_close * 100 if last_close else 0
    if diff_pct > 0.5:
        return f"Bullish (+{diff_pct:.2f}% expected)"
    elif diff_pct < -0.5:
        return f"Bearish ({diff_pct:.2f}% expected)"
    return f"Flat / Sideways ({diff_pct:+.2f}% expected)"
