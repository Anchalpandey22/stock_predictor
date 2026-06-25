"""
indicators.py
--------------
Technical indicator calculations built on top of the `ta` library.
All functions take a DataFrame with at least a 'Close' column (and
'High'/'Low' where needed) and return the DataFrame with new columns added,
so they can be chained together cleanly inside the Stock Analysis page.
"""

import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands


def add_sma(df: pd.DataFrame, windows=(20, 50, 200)) -> pd.DataFrame:
    """Adds Simple Moving Average columns for each window, e.g. SMA_20."""
    df = df.copy()
    for w in windows:
        if len(df) >= w:
            df[f"SMA_{w}"] = SMAIndicator(close=df["Close"], window=w).sma_indicator()
        else:
            df[f"SMA_{w}"] = pd.NA
    return df


def add_ema(df: pd.DataFrame, window=20) -> pd.DataFrame:
    """Adds an Exponential Moving Average column, EMA_<window>."""
    df = df.copy()
    if len(df) >= window:
        df[f"EMA_{window}"] = EMAIndicator(close=df["Close"], window=window).ema_indicator()
    else:
        df[f"EMA_{window}"] = pd.NA
    return df


def add_rsi(df: pd.DataFrame, window=14) -> pd.DataFrame:
    """Adds Relative Strength Index column 'RSI'."""
    df = df.copy()
    if len(df) >= window:
        df["RSI"] = RSIIndicator(close=df["Close"], window=window).rsi()
    else:
        df["RSI"] = pd.NA
    return df


def add_macd(df: pd.DataFrame, window_slow=26, window_fast=12, window_sign=9) -> pd.DataFrame:
    """Adds MACD, MACD_Signal, and MACD_Diff (histogram) columns."""
    df = df.copy()
    if len(df) >= window_slow:
        macd = MACD(
            close=df["Close"],
            window_slow=window_slow,
            window_fast=window_fast,
            window_sign=window_sign,
        )
        df["MACD"] = macd.macd()
        df["MACD_Signal"] = macd.macd_signal()
        df["MACD_Diff"] = macd.macd_diff()
    else:
        df["MACD"] = pd.NA
        df["MACD_Signal"] = pd.NA
        df["MACD_Diff"] = pd.NA
    return df


def add_bollinger_bands(df: pd.DataFrame, window=20, window_dev=2) -> pd.DataFrame:
    """Adds BB_Upper, BB_Middle, BB_Lower columns."""
    df = df.copy()
    if len(df) >= window:
        bb = BollingerBands(close=df["Close"], window=window, window_dev=window_dev)
        df["BB_Upper"] = bb.bollinger_hband()
        df["BB_Middle"] = bb.bollinger_mavg()
        df["BB_Lower"] = bb.bollinger_lband()
    else:
        df["BB_Upper"] = pd.NA
        df["BB_Middle"] = pd.NA
        df["BB_Lower"] = pd.NA
    return df


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience function that adds every supported indicator at once.
    Used on the Stock Analysis page when 'select all' is toggled."""
    df = add_sma(df, windows=(20, 50, 200))
    df = add_ema(df, window=20)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    return df


def rsi_signal(latest_rsi) -> str:
    """Translates a numeric RSI value into a simple human-readable signal."""
    if pd.isna(latest_rsi):
        return "Not enough data"
    if latest_rsi >= 70:
        return "Overbought"
    if latest_rsi <= 30:
        return "Oversold"
    return "Neutral"


def macd_signal_text(latest_macd, latest_signal) -> str:
    """Translates the MACD line vs signal line crossover into text."""
    if pd.isna(latest_macd) or pd.isna(latest_signal):
        return "Not enough data"
    return "Bullish (MACD above Signal)" if latest_macd > latest_signal else "Bearish (MACD below Signal)"
