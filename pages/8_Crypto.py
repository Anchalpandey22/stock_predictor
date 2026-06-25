"""
pages/8_Crypto.py
--------------------
Live Bitcoin, Ethereum, and Dogecoin prices, daily % change, and
historical charts (data sourced via yfinance's *-USD tickers, which
mirrors live crypto market prices without needing a separate paid API).
"""

import streamlit as st
from utils import api, charts, helpers

st.set_page_config(page_title="Crypto Dashboard", page_icon="🪙", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("🪙 Cryptocurrency Dashboard")
st.caption("Live prices for Bitcoin, Ethereum, and Dogecoin.")

with st.spinner("Fetching crypto prices..."):
    crypto_df = api.get_crypto_prices()

if crypto_df.empty:
    st.warning("Could not retrieve crypto prices right now. Please try again shortly.")
    st.stop()

cols = st.columns(len(crypto_df))
icons = {"Bitcoin": "₿", "Ethereum": "Ξ", "Dogecoin": "Ð"}
for col, (_, row) in zip(cols, crypto_df.iterrows()):
    pct = row["% Change (24h approx)"]
    cls = "kpi-up" if pct >= 0 else "kpi-down"
    arrow = "▲" if pct >= 0 else "▼"
    with col:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">{icons.get(row['Name'], '')} {row['Name']} ({row['Symbol']})</div>
                <div class="kpi-value">${row['Price (USD)']:,.4f}</div>
                <div class="kpi-sub {cls}">{arrow} {pct:+.2f}%</div>
            </div>""",
            unsafe_allow_html=True,
        )

st.divider()

st.markdown('<div class="section-title">Historical Price Charts</div>', unsafe_allow_html=True)
coin_choice = st.selectbox("Select coin", crypto_df["Name"].tolist())
period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
symbol = crypto_df.loc[crypto_df["Name"] == coin_choice, "Symbol"].iloc[0]

with st.spinner("Loading history..."):
    hist = api.get_crypto_history(symbol, period=period)

if hist.empty:
    st.warning("No historical data available for this coin/period.")
else:
    st.plotly_chart(charts.crypto_history_chart(hist, coin_choice), use_container_width=True,
                     config={"displaylogo": False})
    csv_bytes = helpers.df_to_csv_bytes(hist)
    st.download_button("⬇️ Download history as CSV", csv_bytes, file_name=f"{symbol}_history.csv", mime="text/csv")

st.caption("Crypto prices via Yahoo Finance USD-quoted pairs (e.g. BTC-USD). Markets trade 24/7, "
           "so these prices reflect the live, continuous crypto market rather than fixed exchange hours.")
