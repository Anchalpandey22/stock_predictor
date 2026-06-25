"""
pages/1_Stock_Analysis.py
--------------------------
Search any ticker (AAPL, TSLA, MSFT, NVDA, GOOGL, etc.) and view live
quote data, interactive candlestick/line/area/volume charts, and
technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands) with toggles.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from database import db
from utils import api, indicators, charts, helpers

st.set_page_config(page_title="Stock Analysis", page_icon="🔍", layout="wide")

# Reuse the same CSS + auto-refresh settings as the Home page
try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

_interval_map = {"5 seconds": 5000, "30 seconds": 30000, "60 seconds": 60000}
interval = st.session_state.get("refresh_interval", "Off")
if interval in _interval_map:
    st_autorefresh(interval=_interval_map[interval], key="analysis_autorefresh")

st.title("🔍 Stock Analysis")
st.caption("Search a ticker symbol to view live quotes, charts, and technical indicators.")

# ---------------------------------------------------------------------------
# SEARCH BAR
# ---------------------------------------------------------------------------
popular = ["AAPL", "TSLA", "MSFT", "NVDA", "GOOGL", "AMZN", "META"]
col_search, col_quick = st.columns([2, 3])
with col_search:
    symbol_input = st.text_input("Enter ticker symbol", value=st.session_state.get("last_symbol", "AAPL")).strip().upper()
with col_quick:
    st.write("Quick picks:")
    qcols = st.columns(len(popular))
    for c, sym in zip(qcols, popular):
        if c.button(sym, key=f"quick_{sym}"):
            symbol_input = sym

st.session_state["last_symbol"] = symbol_input

if not symbol_input:
    st.info("Enter a ticker symbol above to get started, e.g. AAPL, TSLA, MSFT.")
    st.stop()

if not helpers.is_valid_ticker_format(symbol_input):
    st.error("That doesn't look like a valid ticker symbol. Use letters only, e.g. AAPL, MSFT, ^GSPC.")
    st.stop()

with st.spinner(f"Fetching data for {symbol_input}..."):
    info = api.get_stock_info(symbol_input)

if info is None:
    st.error(
        f"❌ Couldn't find data for **{symbol_input}**. Double-check the symbol, or it may be "
        "delisted / unsupported by Yahoo Finance. Try AAPL, MSFT, TSLA, NVDA, or GOOGL."
    )
    st.stop()

# Add a watchlist quick-action right next to the result
col_title, col_action = st.columns([4, 1])
with col_title:
    st.subheader(f"{info['name']} ({info['symbol']})  ·  {info.get('sector', 'N/A')}")
with col_action:
    if st.button("⭐ Add to Watchlist", use_container_width=True):
        added = db.add_to_watchlist(symbol_input)
        st.toast(f"Added {symbol_input} to watchlist!" if added else f"{symbol_input} is already in your watchlist.")

# ---------------------------------------------------------------------------
# KPI ROW
# ---------------------------------------------------------------------------
arrow = "▲" if info["pct_change"] >= 0 else "▼"
css_class = "kpi-up" if info["pct_change"] >= 0 else "kpi-down"

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Current Price</div>
        <div class="kpi-value">{helpers.fmt_currency(info['current_price'])}</div>
        <div class="kpi-sub {css_class}">{arrow} {info['change']:+.2f} ({info['pct_change']:+.2f}%)</div></div>""",
        unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Open</div>
        <div class="kpi-value">{helpers.fmt_currency(info['open'])}</div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Day High / Low</div>
        <div class="kpi-value" style="font-size:1.1rem;">{helpers.fmt_currency(info['day_high'])} / {helpers.fmt_currency(info['day_low'])}</div></div>""",
        unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Volume</div>
        <div class="kpi-value">{helpers.fmt_volume(info['volume'])}</div></div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Market Cap</div>
        <div class="kpi-value" style="font-size:1.25rem;">{helpers.fmt_large_number(info['market_cap'])}</div></div>""",
        unsafe_allow_html=True)
with k6:
    pe = f"{info['pe_ratio']:.2f}" if info['pe_ratio'] and info['pe_ratio'] == info['pe_ratio'] else "N/A"
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">P/E Ratio</div>
        <div class="kpi-value">{pe}</div></div>""", unsafe_allow_html=True)

k7, k8, k9 = st.columns(3)
with k7:
    eps = f"{info['eps']:.2f}" if info['eps'] and info['eps'] == info['eps'] else "N/A"
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">EPS</div><div class="kpi-value">{eps}</div></div>""",
                unsafe_allow_html=True)
with k8:
    div_yield = info.get("dividend_yield")
    div_text = f"{div_yield * 100:.2f}%" if div_yield and div_yield == div_yield else "N/A"
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Dividend Yield</div><div class="kpi-value">{div_text}</div></div>""",
                unsafe_allow_html=True)
with k9:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">52-Week Range</div>
        <div class="kpi-value" style="font-size:1.05rem;">{helpers.fmt_currency(info['fifty_two_low'])} – {helpers.fmt_currency(info['fifty_two_high'])}</div></div>""",
        unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# CHART CONTROLS
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Price Chart</div>', unsafe_allow_html=True)

ctrl1, ctrl2, ctrl3 = st.columns([1.3, 1, 2.5])
with ctrl1:
    period = st.selectbox("Time period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
with ctrl2:
    chart_type = st.selectbox("Chart type", ["Candlestick", "Line", "Area"])
with ctrl3:
    st.write("Indicators:")
    ind_cols = st.columns(5)
    show_sma20 = ind_cols[0].checkbox("SMA 20")
    show_sma50 = ind_cols[1].checkbox("SMA 50")
    show_sma200 = ind_cols[2].checkbox("SMA 200")
    show_ema = ind_cols[3].checkbox("EMA 20")
    show_bb = ind_cols[4].checkbox("Bollinger")

show_rsi = st.checkbox("Show RSI panel", value=False)
show_macd = st.checkbox("Show MACD panel", value=False)
show_volume = st.checkbox("Show Volume panel", value=True)

with st.spinner("Loading historical data..."):
    hist = api.get_stock_history(symbol_input, period=period)

if hist.empty:
    st.warning("No historical data available for this symbol/period combination.")
    st.stop()

ind_df = indicators.compute_all_indicators(hist)

sma_windows = []
if show_sma20: sma_windows.append(20)
if show_sma50: sma_windows.append(50)
if show_sma200: sma_windows.append(200)

if chart_type == "Candlestick":
    fig = charts.candlestick_chart(hist, symbol_input, indicators_df=ind_df,
                                    show_sma=sma_windows, show_ema=show_ema, show_bbands=show_bb)
elif chart_type == "Line":
    fig = charts.line_chart(hist, symbol_input)
else:
    fig = charts.area_chart(hist, symbol_input)

st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})
st.caption("💡 Tip: scroll/drag to zoom and pan, double-click to reset, hover for exact values, "
           "and use the camera icon in the chart toolbar to download a PNG.")

if show_volume:
    st.plotly_chart(charts.volume_chart(hist, symbol_input), use_container_width=True, config={"displaylogo": False})

if show_rsi:
    st.plotly_chart(charts.rsi_chart(ind_df), use_container_width=True, config={"displaylogo": False})
    latest_rsi = ind_df["RSI"].iloc[-1]
    st.caption(f"Latest RSI: {latest_rsi:.2f} → **{indicators.rsi_signal(latest_rsi)}**")

if show_macd:
    st.plotly_chart(charts.macd_chart(ind_df), use_container_width=True, config={"displaylogo": False})
    st.caption(f"Latest MACD signal: **{indicators.macd_signal_text(ind_df['MACD'].iloc[-1], ind_df['MACD_Signal'].iloc[-1])}**")

st.divider()
st.markdown('<div class="section-title">Raw Historical Data</div>', unsafe_allow_html=True)
st.dataframe(hist.tail(60).sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

csv_bytes = helpers.df_to_csv_bytes(hist)
st.download_button("⬇️ Download history as CSV", csv_bytes, file_name=f"{symbol_input}_history.csv", mime="text/csv")
