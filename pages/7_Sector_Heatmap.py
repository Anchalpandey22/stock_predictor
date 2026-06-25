"""
pages/7_Sector_Heatmap.py
---------------------------
Visualizes sector performance across Technology, Finance, Healthcare,
Energy, Consumer Goods, and Communication using a representative basket
of large-cap stocks per sector (rather than a paid sector-data API).
"""

import streamlit as st
from utils import api, charts

st.set_page_config(page_title="Sector Heatmap", page_icon="🗺️", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("🗺️ Sector Performance Heatmap")
st.caption("Average daily % change across a representative basket of large-cap stocks per sector.")

with st.spinner("Scanning sectors..."):
    sector_df = api.get_sector_performance()

if sector_df.empty:
    st.warning("Could not retrieve sector data right now. Please try again shortly.")
    st.stop()

avg_by_sector = sector_df.groupby("Sector")["% Change"].mean().reset_index()
avg_by_sector = avg_by_sector.rename(columns={"% Change": "pct_change", "Sector": "sector"})

st.plotly_chart(charts.sector_heatmap(avg_by_sector), use_container_width=True, config={"displaylogo": False})

st.markdown('<div class="section-title">Underlying Stocks</div>', unsafe_allow_html=True)
display = sector_df.copy()
display["% Change"] = display["% Change"].map(lambda v: f"{v:+.2f}%")
st.dataframe(display, use_container_width=True, hide_index=True)

st.caption(
    "Sectors are approximated using a basket of 5 representative large-cap stocks each "
    "(e.g. Technology → AAPL, MSFT, NVDA, GOOGL, ADBE). This keeps the dashboard fast and "
    "free to run without a paid sector-data subscription."
)
