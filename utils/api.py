"""
api.py
------
Centralized module for all external data fetching:
- Live/near-live stock data via yfinance
- Market indices (S&P 500, NASDAQ, Dow Jones)
- Top gainers / losers / most active (from a tracked universe of tickers)
- Cryptocurrency prices (BTC, ETH, DOGE)
- News headlines via NewsAPI (with graceful fallback if no API key/connection)

Every public function here is wrapped in try/except so that network issues,
rate limits, or invalid tickers never crash the Streamlit app. Functions
return None / empty DataFrame on failure, and the calling page is
responsible for showing a friendly empty-state message.
"""

import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
# NewsAPI key can be set as an environment variable. The app still works
# (with sample headlines) if this is not configured - this keeps the
# project runnable out of the box without requiring the user to sign up.
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
NEWSAPI_URL = "https://newsapi.org/v2/everything"

INDEX_TICKERS = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
}

CRYPTO_TICKERS = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Dogecoin": "DOGE-USD",
}

# A reasonably broad universe used to compute "top gainers / losers / most
# active" on the Home page without needing a paid market-wide screener API.
MARKET_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "AMD",
    "INTC", "ORCL", "CRM", "ADBE", "PYPL", "DIS", "BA", "JPM", "V", "MA",
    "WMT", "KO", "PEP", "XOM", "CVX", "PFE", "JNJ", "UNH", "T", "VZ",
]

SECTOR_TICKERS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "ADBE"],
    "Finance": ["JPM", "V", "MA", "GS", "BAC"],
    "Healthcare": ["JNJ", "PFE", "UNH", "MRK", "ABBV"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "OXY"],
    "Consumer Goods": ["WMT", "KO", "PEP", "PG", "COST"],
    "Communication": ["DIS", "NFLX", "T", "VZ", "META"],
}


def _safe_float(value, default=np.nan):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# SINGLE STOCK DATA
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_stock_info(symbol: str):
    """Returns a dict with key fundamentals + latest quote for one symbol.
    Returns None if the symbol is invalid or data could not be retrieved."""
    symbol = symbol.upper().strip()
    if not symbol:
        return None
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        hist = ticker.history(period="5d")
        if hist.empty:
            return None

        last_row = hist.iloc[-1]
        prev_close = info.get("previousClose") or (hist.iloc[-2]["Close"] if len(hist) > 1 else last_row["Close"])
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or last_row["Close"]
        change = current_price - prev_close
        pct_change = (change / prev_close * 100) if prev_close else 0.0

        return {
            "symbol": symbol,
            "name": info.get("shortName", symbol),
            "current_price": _safe_float(current_price),
            "open": _safe_float(info.get("open", last_row.get("Open"))),
            "day_high": _safe_float(info.get("dayHigh", last_row.get("High"))),
            "day_low": _safe_float(info.get("dayLow", last_row.get("Low"))),
            "prev_close": _safe_float(prev_close),
            "volume": _safe_float(info.get("volume", last_row.get("Volume"))),
            "market_cap": _safe_float(info.get("marketCap")),
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "eps": _safe_float(info.get("trailingEps")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "fifty_two_high": _safe_float(info.get("fiftyTwoWeekHigh")),
            "fifty_two_low": _safe_float(info.get("fiftyTwoWeekLow")),
            "change": _safe_float(change),
            "pct_change": _safe_float(pct_change),
            "currency": info.get("currency", "USD"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
        }
    except Exception as e:
        print(f"[api.get_stock_info] Error fetching {symbol}: {e}")
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_stock_history(symbol: str, period="6mo", interval="1d"):
    """Returns OHLCV historical DataFrame for the given symbol, or an empty
    DataFrame if unavailable."""
    symbol = symbol.upper().strip()
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else "Datetime"
        df = df.rename(columns={date_col: "Date"})
        return df
    except Exception as e:
        print(f"[api.get_stock_history] Error fetching {symbol}: {e}")
        return pd.DataFrame()


def validate_ticker(symbol: str) -> bool:
    """Quick check whether a ticker symbol returns any usable data."""
    if not symbol or not symbol.strip():
        return False
    info = get_stock_info(symbol)
    return info is not None


# ---------------------------------------------------------------------------
# MARKET INDICES
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_market_indices():
    """Returns a DataFrame with current value and % change for major indices."""
    rows = []
    for name, ticker_symbol in INDEX_TICKERS.items():
        try:
            hist = yf.Ticker(ticker_symbol).history(period="2d")
            if hist.empty:
                continue
            last = hist.iloc[-1]["Close"]
            prev = hist.iloc[-2]["Close"] if len(hist) > 1 else last
            change = last - prev
            pct = (change / prev * 100) if prev else 0
            rows.append({"Index": name, "Value": round(last, 2), "Change": round(change, 2), "% Change": round(pct, 2)})
        except Exception as e:
            print(f"[api.get_market_indices] Error fetching {ticker_symbol}: {e}")
            continue
    return pd.DataFrame(rows)


def get_market_status():
    """Very simple US market-hours heuristic (Mon-Fri, 9:30-16:00 ET).
    Uses an approximate UTC offset - good enough for a student-style
    dashboard, not for production trading systems."""
    now_utc = datetime.utcnow()
    et_time = now_utc - timedelta(hours=4)
    if et_time.weekday() >= 5:
        return "Closed (Weekend)", et_time
    open_time = et_time.replace(hour=9, minute=30, second=0, microsecond=0)
    close_time = et_time.replace(hour=16, minute=0, second=0, microsecond=0)
    if open_time <= et_time <= close_time:
        return "Open", et_time
    return "Closed", et_time


# ---------------------------------------------------------------------------
# GAINERS / LOSERS / MOST ACTIVE
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def get_market_movers(universe=None, top_n=5):
    """Scans a fixed universe of liquid tickers and returns top gainers,
    losers, and most active stocks by volume."""
    universe = universe or MARKET_UNIVERSE
    try:
        data = yf.download(universe, period="2d", group_by="ticker", progress=False, threads=True)
    except Exception as e:
        print(f"[api.get_market_movers] bulk download failed: {e}")
        data = None

    rows = []
    for sym in universe:
        try:
            if data is not None and isinstance(data.columns, pd.MultiIndex) and sym in data.columns.get_level_values(0):
                df = data[sym].dropna()
            else:
                df = yf.Ticker(sym).history(period="2d")
            if df is None or df.empty or len(df) < 2:
                continue
            last_close = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]
            volume = df["Volume"].iloc[-1]
            pct = (last_close - prev_close) / prev_close * 100 if prev_close else 0
            rows.append({"Symbol": sym, "Price": round(last_close, 2), "% Change": round(pct, 2), "Volume": int(volume)})
        except Exception as e:
            print(f"[api.get_market_movers] error on {sym}: {e}")
            continue

    df_all = pd.DataFrame(rows)
    if df_all.empty:
        return df_all, df_all, df_all

    gainers = df_all.sort_values("% Change", ascending=False).head(top_n).reset_index(drop=True)
    losers = df_all.sort_values("% Change", ascending=True).head(top_n).reset_index(drop=True)
    most_active = df_all.sort_values("Volume", ascending=False).head(top_n).reset_index(drop=True)
    return gainers, losers, most_active


# ---------------------------------------------------------------------------
# SECTOR HEATMAP DATA
# ---------------------------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_sector_performance():
    """Returns a long-format DataFrame: Sector, Symbol, % Change - used to
    build the sector heatmap."""
    rows = []
    for sector, tickers in SECTOR_TICKERS.items():
        for sym in tickers:
            try:
                hist = yf.Ticker(sym).history(period="2d")
                if hist.empty or len(hist) < 2:
                    continue
                last = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                pct = (last - prev) / prev * 100 if prev else 0
                rows.append({"Sector": sector, "Symbol": sym, "% Change": round(pct, 2)})
            except Exception as e:
                print(f"[api.get_sector_performance] error on {sym}: {e}")
                continue
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CRYPTOCURRENCY
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_crypto_prices():
    rows = []
    for name, sym in CRYPTO_TICKERS.items():
        try:
            hist = yf.Ticker(sym).history(period="2d")
            if hist.empty:
                continue
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) > 1 else last
            pct = (last - prev) / prev * 100 if prev else 0
            rows.append({"Name": name, "Symbol": sym, "Price (USD)": round(last, 4), "% Change (24h approx)": round(pct, 2)})
        except Exception as e:
            print(f"[api.get_crypto_prices] error on {sym}: {e}")
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=60, show_spinner=False)
def get_crypto_history(symbol: str, period="3mo"):
    try:
        df = yf.Ticker(symbol).history(period=period)
        return df.reset_index() if not df.empty else pd.DataFrame()
    except Exception as e:
        print(f"[api.get_crypto_history] error on {symbol}: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# NEWS + SENTIMENT
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains",
    "growth", "record", "upgrade", "upgrades", "strong", "optimistic", "profit", "profits",
    "rise", "rises", "bullish", "outperform", "boost", "boosts", "high", "wins", "win",
}
_NEGATIVE_WORDS = {
    "fall", "falls", "plunge", "plunges", "drop", "drops", "loss", "losses", "downgrade",
    "downgrades", "weak", "lawsuit", "fraud", "miss", "misses", "bearish", "decline",
    "declines", "cut", "cuts", "crash", "crashes", "low", "warns", "warning", "concern",
    "concerns", "recall", "layoffs", "slump",
}


def analyze_sentiment(text: str) -> str:
    """Very lightweight keyword-based sentiment classifier. Returns one of
    'Positive', 'Neutral', 'Negative'. Intentionally simple (no heavyweight
    NLP dependency) and clearly documented as such."""
    if not text:
        return "Neutral"
    text_lower = text.lower()
    pos_score = sum(1 for w in _POSITIVE_WORDS if w in text_lower)
    neg_score = sum(1 for w in _NEGATIVE_WORDS if w in text_lower)
    if pos_score > neg_score:
        return "Positive"
    elif neg_score > pos_score:
        return "Negative"
    return "Neutral"


def _sample_news(query="stock market"):
    """Fallback sample headlines used when NewsAPI is unreachable or no
    API key has been configured, so the News page always has content."""
    now = datetime.now()
    samples = [
        {
            "title": f"{query.upper()} climbs as investors digest latest earnings reports",
            "source": "Sample Financial Wire",
            "publishedAt": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
            "description": "Shares moved higher in trading today as analysts pointed to stronger than expected quarterly growth and an upbeat outlook for the coming year.",
            "url": "https://www.google.com/search?q=" + query.replace(" ", "+"),
        },
        {
            "title": f"Analysts split on {query} outlook amid mixed economic data",
            "source": "Sample Markets Daily",
            "publishedAt": (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"),
            "description": "Market watchers remain divided, with some flagging valuation concerns while others see room for continued gains over the medium term.",
            "url": "https://www.google.com/search?q=" + query.replace(" ", "+"),
        },
        {
            "title": f"{query.upper()} slips slightly after broader sector pullback",
            "source": "Sample Business Report",
            "publishedAt": (now - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M"),
            "description": "A modest decline followed a wider pullback across the sector, though trading volume remained within normal historical ranges.",
            "url": "https://www.google.com/search?q=" + query.replace(" ", "+"),
        },
    ]
    return samples


def get_news(query="stock market", page_size=10):
    """Fetches news headlines for a query. Falls back to sample headlines
    if NEWSAPI_KEY is not configured or the request fails, so the News
    page is never empty."""
    if not NEWSAPI_KEY:
        return _sample_news(query), True  # True => using fallback sample data

    try:
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": page_size,
            "apiKey": NEWSAPI_KEY,
        }
        response = requests.get(NEWSAPI_URL, params=params, timeout=8)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return _sample_news(query), True

        cleaned = []
        for a in articles:
            cleaned.append({
                "title": a.get("title", "Untitled"),
                "source": (a.get("source") or {}).get("name", "Unknown"),
                "publishedAt": (a.get("publishedAt") or "")[:16].replace("T", " "),
                "description": a.get("description") or "No summary available.",
                "url": a.get("url", "#"),
            })
        return cleaned, False
    except Exception as e:
        print(f"[api.get_news] Error fetching news: {e}")
        return _sample_news(query), True
