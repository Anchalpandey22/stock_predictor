"""
app.py
------
Entry point for the Real-Time Stock Market Dashboard.
This file IS the Home page (Streamlit's multipage convention: the script
passed to `streamlit run` is the first/landing page, and everything in
/pages becomes additional sidebar pages automatically).

Run with:
    streamlit run app.py
"""

import time
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from database import db
from utils import api, helpers

# ---------------------------------------------------------------------------
# PAGE CONFIG (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Real-Time Stock Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# ONE-TIME SETUP: create DB tables if they don't exist yet
# ---------------------------------------------------------------------------
db.init_db()

# ---------------------------------------------------------------------------
# LOAD CUSTOM CSS
# ---------------------------------------------------------------------------
def load_css(path="static/style.css"):
    try:
        with open(path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()

# ---------------------------------------------------------------------------
# SIDEBAR: branding, theme toggle, auto-refresh control
# (these settings are read by every page via st.session_state)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📈 StockSense Dashboard")
    st.caption("Real-time market data, analytics & AI predictions")
    st.divider()

    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = "Off"

    st.session_state.refresh_interval = st.selectbox(
        "Auto-refresh interval",
        ["Off", "5 seconds", "30 seconds", "60 seconds"],
        index=["Off", "5 seconds", "30 seconds", "60 seconds"].index(st.session_state.refresh_interval),
        help="Automatically reruns the app to pull fresh data at the chosen interval.",
    )

    st.divider()
    st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("Built with Streamlit · yfinance · Plotly · scikit-learn")

# Apply auto-refresh based on sidebar selection
_interval_map = {"5 seconds": 5000, "30 seconds": 30000, "60 seconds": 60000}
if st.session_state.refresh_interval in _interval_map:
    st_autorefresh(interval=_interval_map[st.session_state.refresh_interval], key="home_autorefresh")

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
status, current_time = api.get_market_status()
status_class = "chip-open" if status == "Open" else "chip-closed"

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("📊 Market Overview")
    st.caption("Live snapshot of major indices, top movers, and market activity")
with col_h2:
    st.markdown(
        f"""
        <div style="text-align:right; padding-top: 18px;">
            <span class="chip {status_class}">● MARKET {status.upper()}</span><br/>
            <span style="font-size:0.8rem; opacity:0.7;">
                {current_time.strftime('%A, %d %B %Y — %I:%M:%S %p')} (ET, approx.)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# MAJOR INDICES
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Major Indices</div>', unsafe_allow_html=True)

with st.spinner("Fetching index data..."):
    indices_df = api.get_market_indices()

if indices_df.empty:
    st.warning("⚠️ Could not retrieve index data right now. This usually means a temporary "
               "connectivity issue with Yahoo Finance — try refreshing in a moment.")
else:
    cols = st.columns(len(indices_df))
    for col, (_, row) in zip(cols, indices_df.iterrows()):
        css_class = "kpi-up" if row["% Change"] >= 0 else "kpi-down"
        arrow = "▲" if row["% Change"] >= 0 else "▼"
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{row['Index']}</div>
                    <div class="kpi-value">{row['Value']:,.2f}</div>
                    <div class="kpi-sub {css_class}">{arrow} {row['Change']:+.2f} ({row['% Change']:+.2f}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.divider()

# ---------------------------------------------------------------------------
# TOP GAINERS / LOSERS / MOST ACTIVE
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Top Gainers, Losers & Most Active</div>', unsafe_allow_html=True)

with st.spinner("Scanning market movers..."):
    gainers, losers, most_active = api.get_market_movers()

tab1, tab2, tab3 = st.tabs(["🟢 Top Gainers", "🔴 Top Losers", "🔵 Most Active"])

def render_movers_table(df, highlight="green"):
    if df.empty:
        st.info("No data available right now.")
        return
    display = df.copy()
    display["% Change"] = display["% Change"].map(lambda v: f"{v:+.2f}%")
    display["Price"] = display["Price"].map(lambda v: f"${v:,.2f}")
    display["Volume"] = display["Volume"].map(helpers.fmt_volume)
    st.dataframe(display, use_container_width=True, hide_index=True)

with tab1:
    render_movers_table(gainers)
with tab2:
    render_movers_table(losers)
with tab3:
    render_movers_table(most_active)

st.divider()

# ---------------------------------------------------------------------------
# QUICK WATCHLIST PREVIEW + RECENT ACTIVITY
# ---------------------------------------------------------------------------
col_a, col_b = st.columns(2)

with col_a:
    st.markdown('<div class="section-title">Your Watchlist (Quick View)</div>', unsafe_allow_html=True)
    wl_df = db.get_watchlist()
    if wl_df.empty:
        st.info("Your watchlist is empty. Add symbols from the **Watchlist** page in the sidebar.")
    else:
        for _, row in wl_df.head(6).iterrows():
            info = api.get_stock_info(row["symbol"])
            if info:
                arrow = "▲" if info["pct_change"] >= 0 else "▼"
                cls = "kpi-up" if info["pct_change"] >= 0 else "kpi-down"
                st.markdown(
                    f"""<div class="stock-row">
                        <b>{row['symbol']}</b> — {helpers.fmt_currency(info['current_price'])}
                        &nbsp; <span class="{cls}">{arrow} {info['pct_change']:+.2f}%</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        if len(wl_df) > 6:
            st.caption(f"+{len(wl_df) - 6} more — view full list on the Watchlist page.")

with col_b:
    st.markdown('<div class="section-title">Recent Activity</div>', unsafe_allow_html=True)
    activity_df = db.get_recent_activity(limit=8)
    if activity_df.empty:
        st.info("No activity yet. Start by adding a stock to your watchlist or portfolio!")
    else:
        for _, row in activity_df.iterrows():
            st.caption(f"🕒 {row['created_on']} — **{row['action']}** {row['details'] or ''}")

st.divider()
st.caption(
    "Data provided by Yahoo Finance (via yfinance) and CoinGecko-style public market data. "
    "Prices may be delayed by a few minutes. This dashboard is a student/educational project "
    "and is **not** intended to be used for real investment decisions."
)
