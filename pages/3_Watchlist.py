"""
pages/3_Watchlist.py
---------------------
Add, remove, and manage favorite stocks. Stored in SQLite (source of
truth) and mirrored to a CSV file in /data so the project also satisfies
the "store in CSV files" requirement and gives users an easy file to
inspect/export outside the app.
"""

import os
import streamlit as st

from database import db
from utils import api, helpers

st.set_page_config(page_title="Watchlist", page_icon="⭐", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

DATA_DIR = "data"
CSV_PATH = os.path.join(DATA_DIR, "watchlist.csv")
os.makedirs(DATA_DIR, exist_ok=True)


def sync_csv():
    """Mirrors the current SQLite watchlist out to data/watchlist.csv."""
    df = db.get_watchlist()
    df.to_csv(CSV_PATH, index=False)


st.title("⭐ Watchlist")
st.caption("Track the stocks you care about. Saved to SQLite and mirrored to data/watchlist.csv.")

with st.form("add_symbol_form", clear_on_submit=True):
    c1, c2 = st.columns([4, 1])
    new_symbol = c1.text_input("Add a ticker symbol", placeholder="e.g. AAPL")
    submitted = c2.form_submit_button("➕ Add", use_container_width=True)
    if submitted and new_symbol:
        new_symbol = new_symbol.strip().upper()
        if not helpers.is_valid_ticker_format(new_symbol):
            st.error("Invalid ticker format. Use letters only, e.g. AAPL, MSFT.")
        else:
            info = api.get_stock_info(new_symbol)
            if info is None:
                st.error(f"Couldn't validate '{new_symbol}' - it may not be a real/listed ticker.")
            else:
                added = db.add_to_watchlist(new_symbol)
                sync_csv()
                if added:
                    st.success(f"Added {new_symbol} to your watchlist!")
                else:
                    st.info(f"{new_symbol} is already in your watchlist.")

st.divider()

wl_df = db.get_watchlist()

if wl_df.empty:
    st.info("📭 Your watchlist is empty. Add a symbol above to get started, or visit "
             "the **Stock Analysis** page and click 'Add to Watchlist'.")
else:
    st.markdown(f'<div class="section-title">Tracking {len(wl_df)} Symbol(s)</div>', unsafe_allow_html=True)

    for _, row in wl_df.iterrows():
        symbol = row["symbol"]
        info = api.get_stock_info(symbol)
        with st.container():
            cols = st.columns([1.2, 1.5, 1.5, 1.5, 1.5, 1])
            cols[0].markdown(f"### {symbol}")
            if info:
                arrow = "▲" if info["pct_change"] >= 0 else "▼"
                cls = "kpi-up" if info["pct_change"] >= 0 else "kpi-down"
                cols[1].metric("Price", helpers.fmt_currency(info["current_price"]))
                cols[2].markdown(f"<span class='{cls}'>{arrow} {helpers.fmt_pct(info['pct_change'])}</span>",
                                  unsafe_allow_html=True)
                cols[3].caption(f"Volume: {helpers.fmt_volume(info['volume'])}")
                cols[4].caption(f"Added: {row['added_on'][:10]}")
            else:
                cols[1].warning("Data unavailable")
            if cols[5].button("🗑️ Remove", key=f"remove_{symbol}"):
                db.remove_from_watchlist(symbol)
                sync_csv()
                st.rerun()
        st.divider()

    csv_bytes = helpers.df_to_csv_bytes(wl_df)
    st.download_button("⬇️ Export watchlist as CSV", csv_bytes, file_name="watchlist.csv", mime="text/csv")

st.caption(f"📄 Mirrored CSV file location: `{CSV_PATH}`")
