"""
charts.py
---------
Reusable Plotly chart builders for the dashboard. Keeping these in one
place means every page (Stock Analysis, Compare, Crypto, etc.) gets the
same look-and-feel and we're not copy-pasting layout code everywhere.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Shared color palette so charts look consistent across pages
COLOR_UP = "#16C784"
COLOR_DOWN = "#EA3943"
COLOR_LINE = "#2E86FF"
COLOR_GRID = "rgba(150,150,150,0.15)"


def _base_layout(fig, title="", height=480):
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=height,
        margin=dict(l=40, r=30, t=50, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor=COLOR_GRID, rangeslider_visible=False),
        yaxis=dict(showgrid=True, gridcolor=COLOR_GRID),
        hovermode="x unified",
    )
    return fig


def candlestick_chart(df: pd.DataFrame, symbol: str, indicators_df: pd.DataFrame = None,
                       show_sma=(), show_ema=False, show_bbands=False, height=520):
    """Candlestick chart with optional overlay indicators (SMA/EMA/Bollinger)."""
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name=symbol, increasing_line_color=COLOR_UP, decreasing_line_color=COLOR_DOWN,
    ))

    src = indicators_df if indicators_df is not None else df

    for w in show_sma:
        col = f"SMA_{w}"
        if col in src.columns:
            fig.add_trace(go.Scatter(x=src["Date"], y=src[col], mode="lines", name=col, line=dict(width=1.5)))

    if show_ema and "EMA_20" in src.columns:
        fig.add_trace(go.Scatter(x=src["Date"], y=src["EMA_20"], mode="lines", name="EMA 20", line=dict(width=1.5, dash="dot")))

    if show_bbands and "BB_Upper" in src.columns:
        fig.add_trace(go.Scatter(x=src["Date"], y=src["BB_Upper"], mode="lines", name="BB Upper",
                                  line=dict(width=1, color="rgba(150,150,150,0.7)")))
        fig.add_trace(go.Scatter(x=src["Date"], y=src["BB_Lower"], mode="lines", name="BB Lower",
                                  line=dict(width=1, color="rgba(150,150,150,0.7)"), fill="tonexty",
                                  fillcolor="rgba(46,134,255,0.07)"))

    return _base_layout(fig, title=f"{symbol} — Candlestick Chart", height=height)


def line_chart(df: pd.DataFrame, symbol: str, height=420):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name=symbol,
                              line=dict(color=COLOR_LINE, width=2)))
    return _base_layout(fig, title=f"{symbol} — Price (Line)", height=height)


def area_chart(df: pd.DataFrame, symbol: str, height=420):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name=symbol,
                              line=dict(color=COLOR_LINE, width=2), fill="tozeroy",
                              fillcolor="rgba(46,134,255,0.15)"))
    return _base_layout(fig, title=f"{symbol} — Price (Area)", height=height)


def volume_chart(df: pd.DataFrame, symbol: str, height=220):
    colors = [COLOR_UP if c >= o else COLOR_DOWN for c, o in zip(df["Close"], df["Open"])]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color=colors))
    return _base_layout(fig, title=f"{symbol} — Volume", height=height)


def rsi_chart(df: pd.DataFrame, height=220):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], mode="lines", name="RSI", line=dict(color="#FFB020")))
    fig.add_hline(y=70, line_dash="dash", line_color=COLOR_DOWN, opacity=0.6)
    fig.add_hline(y=30, line_dash="dash", line_color=COLOR_UP, opacity=0.6)
    fig.update_yaxes(range=[0, 100])
    return _base_layout(fig, title="RSI (14)", height=height)


def macd_chart(df: pd.DataFrame, height=260):
    fig = make_subplots()
    colors = ["#16C784" if v >= 0 else "#EA3943" for v in df["MACD_Diff"].fillna(0)]
    fig.add_trace(go.Bar(x=df["Date"], y=df["MACD_Diff"], name="Histogram", marker_color=colors))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], mode="lines", name="MACD", line=dict(color="#2E86FF")))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_Signal"], mode="lines", name="Signal", line=dict(color="#FFB020")))
    return _base_layout(fig, title="MACD (12, 26, 9)", height=height)


def comparison_line_chart(data: dict, normalize=True, height=480):
    """data: {symbol: DataFrame(Date, Close)}. If normalize, rebases every
    series to 100 at the start so different-priced stocks are comparable."""
    fig = go.Figure()
    for symbol, df in data.items():
        if df is None or df.empty:
            continue
        series = df["Close"]
        if normalize:
            series = series / series.iloc[0] * 100
        fig.add_trace(go.Scatter(x=df["Date"], y=series, mode="lines", name=symbol, line=dict(width=2)))
    title = "Normalized Performance (Base = 100)" if normalize else "Price Comparison"
    return _base_layout(fig, title=title, height=height)


def comparison_volume_bar(latest_volumes: dict, height=360):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(latest_volumes.keys()), y=list(latest_volumes.values()),
                          marker_color=COLOR_LINE))
    return _base_layout(fig, title="Latest Volume Comparison", height=height)


def sector_heatmap(df: pd.DataFrame, height=420):
    """df needs columns: sector, pct_change"""
    if df is None or df.empty:
        return go.Figure()
    df = df.sort_values("pct_change")
    colors = [COLOR_DOWN if v < 0 else COLOR_UP for v in df["pct_change"]]
    fig = go.Figure(go.Bar(
        x=df["pct_change"], y=df["sector"], orientation="h",
        marker_color=colors, text=[f"{v:+.2f}%" for v in df["pct_change"]], textposition="outside",
    ))
    return _base_layout(fig, title="Sector Performance Heatmap (ETF Proxies)", height=height)


def prediction_chart(dates, actual, predicted, symbol, model_name, height=420):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=actual, mode="lines", name="Actual", line=dict(color=COLOR_LINE, width=2)))
    fig.add_trace(go.Scatter(x=dates, y=predicted, mode="lines", name="Predicted",
                              line=dict(color="#FFB020", width=2, dash="dash")))
    return _base_layout(fig, title=f"{symbol} — {model_name}: Actual vs Predicted", height=height)


def crypto_history_chart(df: pd.DataFrame, name: str, height=380):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["price"] if "price" in df.columns else df["Close"],
                              mode="lines", name=name, line=dict(color="#F7931A", width=2),
                              fill="tozeroy", fillcolor="rgba(247,147,26,0.12)"))
    return _base_layout(fig, title=f"{name} — Price History", height=height)
