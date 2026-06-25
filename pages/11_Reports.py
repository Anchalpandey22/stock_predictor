"""
pages/11_Reports.py
----------------------
Centralized report generation: build a CSV / Excel / PDF report for the
watchlist, portfolio, or a single stock's historical data, and save a
copy into the /reports folder (in addition to letting the user download
it directly).
"""

import os
import streamlit as st
from datetime import datetime

from database import db
from utils import api, helpers

st.set_page_config(page_title="Reports", page_icon="🧾", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

st.title("🧾 Reports")
st.caption("Generate and export reports as CSV, Excel, or PDF. Copies are also saved to /reports.")

report_type = st.selectbox("Report type", ["Watchlist Summary", "Portfolio Summary", "Stock History"])

df = None
title = "Report"

if report_type == "Watchlist Summary":
    wl = db.get_watchlist()
    if wl.empty:
        st.info("Your watchlist is empty - nothing to report yet.")
        st.stop()
    rows = []
    for _, r in wl.iterrows():
        info = api.get_stock_info(r["symbol"])
        if info:
            rows.append({
                "Symbol": r["symbol"], "Price": info["current_price"],
                "Change %": info["pct_change"], "Volume": info["volume"], "Added On": r["added_on"],
            })
    import pandas as pd
    df = pd.DataFrame(rows)
    title = "Watchlist Summary Report"

elif report_type == "Portfolio Summary":
    pf = db.get_portfolio()
    if pf.empty:
        st.info("Your portfolio is empty - nothing to report yet.")
        st.stop()
    rows = []
    for _, r in pf.iterrows():
        info = api.get_stock_info(r["symbol"])
        current_price = info["current_price"] if info else None
        cost = r["quantity"] * r["buy_price"]
        value = (r["quantity"] * current_price) if current_price else None
        pnl = (value - cost) if value is not None else None
        rows.append({
            "Symbol": r["symbol"], "Quantity": r["quantity"], "Buy Price": r["buy_price"],
            "Current Price": current_price, "Cost Basis": cost, "Current Value": value, "P/L": pnl,
        })
    import pandas as pd
    df = pd.DataFrame(rows)
    title = "Portfolio Summary Report"

else:  # Stock History
    symbol = st.text_input("Symbol", value="AAPL").strip().upper()
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
    if symbol and helpers.is_valid_ticker_format(symbol):
        df = api.get_stock_history(symbol, period=period)
        title = f"{symbol} Historical Data Report"
    if df is None or df.empty:
        st.info("Enter a valid symbol to generate a history report.")
        st.stop()

st.markdown('<div class="section-title">Preview</div>', unsafe_allow_html=True)
st.dataframe(df, use_container_width=True, hide_index=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
safe_title = title.replace(" ", "_")

csv_bytes = helpers.df_to_csv_bytes(df)
excel_bytes = helpers.df_to_excel_bytes(df, sheet_name="Report")
pdf_bytes = helpers.df_to_pdf_bytes(df, title=title)

c1, c2, c3 = st.columns(3)
if c1.download_button("⬇️ Download CSV", csv_bytes, f"{safe_title}_{timestamp}.csv", "text/csv", use_container_width=True):
    pass
if c2.download_button("⬇️ Download Excel", excel_bytes, f"{safe_title}_{timestamp}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True):
    pass
if c3.download_button("⬇️ Download PDF", pdf_bytes, f"{safe_title}_{timestamp}.pdf", "application/pdf", use_container_width=True):
    pass

if st.button("💾 Also save a copy to /reports folder"):
    csv_path = os.path.join(REPORTS_DIR, f"{safe_title}_{timestamp}.csv")
    pdf_path = os.path.join(REPORTS_DIR, f"{safe_title}_{timestamp}.pdf")
    with open(csv_path, "wb") as f:
        f.write(csv_bytes)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    st.success(f"Saved to `{csv_path}` and `{pdf_path}`")
