"""
pages/2_Compare_Stocks.py
---------------------------
Compare several stocks side-by-side: normalized performance, growth %,
volume, and a summary table.
"""

import streamlit as st
import pandas as pd

from utils import api, charts, helpers

st.set_page_config(page_title="Compare Stocks", page_icon="⚖️", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("⚖️ Multi-Stock Comparison")
st.caption("Compare price performance, growth, and volume across several stocks at once.")

default_symbols = "AAPL, TSLA, MSFT, NVDA, GOOGL"
symbols_raw = st.text_input("Enter ticker symbols, separated by commas", value=default_symbols)
symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]

col1, col2 = st.columns(2)
with col1:
    period = st.selectbox("Time period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
with col2:
    normalize = st.checkbox("Normalize to base 100 (recommended for comparing different price scales)", value=True)

if not symbols:
    st.info("Enter at least one ticker symbol above, e.g. AAPL, TSLA, MSFT.")
    st.stop()

if len(symbols) > 8:
    st.warning("Showing the first 8 symbols only - that keeps charts readable.")
    symbols = symbols[:8]

data = {}
summary_rows = []
invalid = []

with st.spinner("Fetching data for all symbols..."):
    for sym in symbols:
        if not helpers.is_valid_ticker_format(sym):
            invalid.append(sym)
            continue
        hist = api.get_stock_history(sym, period=period)
        info = api.get_stock_info(sym)
        if hist.empty or info is None:
            invalid.append(sym)
            continue
        data[sym] = hist
        start_price = hist["Close"].iloc[0]
        end_price = hist["Close"].iloc[-1]
        growth_pct = (end_price - start_price) / start_price * 100 if start_price else 0
        summary_rows.append({
            "Symbol": sym,
            "Current Price": info["current_price"],
            "Period Growth %": growth_pct,
            "Day Change %": info["pct_change"],
            "Volume": info["volume"],
            "Market Cap": info["market_cap"],
        })

if invalid:
    st.warning(f"⚠️ Could not retrieve data for: {', '.join(invalid)}. Check the symbols and try again.")

if not data:
    st.error("No valid symbols to compare.")
    st.stop()

st.markdown('<div class="section-title">Normalized Price Performance</div>', unsafe_allow_html=True)
st.plotly_chart(charts.comparison_line_chart(data, normalize=normalize), use_container_width=True,
                 config={"displaylogo": False})

st.markdown('<div class="section-title">Summary</div>', unsafe_allow_html=True)
summary_df = pd.DataFrame(summary_rows)
display_df = summary_df.copy()
display_df["Current Price"] = display_df["Current Price"].map(helpers.fmt_currency)
display_df["Period Growth %"] = display_df["Period Growth %"].map(helpers.fmt_pct)
display_df["Day Change %"] = display_df["Day Change %"].map(helpers.fmt_pct)
display_df["Volume"] = display_df["Volume"].map(helpers.fmt_volume)
display_df["Market Cap"] = display_df["Market Cap"].map(helpers.fmt_large_number)
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown('<div class="section-title">Volume Comparison</div>', unsafe_allow_html=True)
latest_volumes = {row["Symbol"]: row["Volume"] for row in summary_rows}
st.plotly_chart(charts.comparison_volume_bar(latest_volumes), use_container_width=True, config={"displaylogo": False})

csv_bytes = helpers.df_to_csv_bytes(summary_df)
st.download_button("⬇️ Download comparison summary as CSV", csv_bytes, file_name="stock_comparison.csv", mime="text/csv")
