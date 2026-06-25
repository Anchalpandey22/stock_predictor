"""
pages/4_Portfolio.py
----------------------
Lets the user log stock holdings (symbol, quantity, purchase price) and
automatically calculates current value, profit/loss, and return % for
each holding plus the portfolio total. All data lives in SQLite.
"""

import streamlit as st
import pandas as pd
from datetime import date

from database import db
from utils import api, helpers, charts
import plotly.graph_objects as go

st.set_page_config(page_title="Portfolio Tracker", page_icon="💼", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("💼 Portfolio Tracker")
st.caption("Log your holdings and track real-time profit/loss. Data is stored in SQLite.")

with st.expander("➕ Add a new holding", expanded=False):
    with st.form("add_holding_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        symbol = c1.text_input("Symbol", placeholder="e.g. AAPL")
        quantity = c2.number_input("Quantity", min_value=0.0001, value=1.0, step=1.0)
        buy_price = c3.number_input("Buy price ($)", min_value=0.0001, value=100.0, step=1.0)
        buy_date = c4.date_input("Purchase date", value=date.today())
        submitted = st.form_submit_button("Add Holding")

        if submitted:
            symbol = symbol.strip().upper()
            if not helpers.is_valid_ticker_format(symbol):
                st.error("Please enter a valid ticker symbol.")
            else:
                info = api.get_stock_info(symbol)
                if info is None:
                    st.error(f"Couldn't validate '{symbol}'. Check the spelling and try again.")
                else:
                    db.add_portfolio_entry(symbol, quantity, buy_price, buy_date)
                    st.success(f"Added {quantity} shares of {symbol} @ ${buy_price:.2f}")
                    st.rerun()

st.divider()

portfolio_df = db.get_portfolio()

if portfolio_df.empty:
    st.info("📭 Your portfolio is empty. Add a holding above to get started.")
    st.stop()

rows = []
for _, r in portfolio_df.iterrows():
    info = api.get_stock_info(r["symbol"])
    current_price = info["current_price"] if info else None
    cost_basis = r["quantity"] * r["buy_price"]
    current_value = (r["quantity"] * current_price) if current_price else None
    pnl = (current_value - cost_basis) if current_value is not None else None
    pnl_pct = (pnl / cost_basis * 100) if (pnl is not None and cost_basis) else None
    rows.append({
        "id": r["id"],
        "Symbol": r["symbol"],
        "Quantity": r["quantity"],
        "Buy Price": r["buy_price"],
        "Buy Date": r["buy_date"],
        "Current Price": current_price,
        "Cost Basis": cost_basis,
        "Current Value": current_value,
        "P/L ($)": pnl,
        "P/L (%)": pnl_pct,
    })

table_df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# PORTFOLIO TOTALS
# ---------------------------------------------------------------------------
total_cost = table_df["Cost Basis"].sum()
total_value = table_df["Current Value"].sum(skipna=True)
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

m1, m2, m3, m4 = st.columns(4)
cls = "kpi-up" if total_pnl >= 0 else "kpi-down"
arrow = "▲" if total_pnl >= 0 else "▼"
m1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Invested</div>
    <div class="kpi-value">{helpers.fmt_currency(total_cost)}</div></div>""", unsafe_allow_html=True)
m2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Current Value</div>
    <div class="kpi-value">{helpers.fmt_currency(total_value)}</div></div>""", unsafe_allow_html=True)
m3.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total P/L</div>
    <div class="kpi-value {cls}">{arrow} {helpers.fmt_currency(total_pnl)}</div></div>""", unsafe_allow_html=True)
m4.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Return</div>
    <div class="kpi-value {cls}">{arrow} {helpers.fmt_pct(total_pnl_pct)}</div></div>""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# HOLDINGS TABLE
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)

display_df = table_df.drop(columns=["id"]).copy()
for col in ["Buy Price", "Current Price", "Cost Basis", "Current Value", "P/L ($)"]:
    display_df[col] = display_df[col].map(helpers.fmt_currency)
display_df["P/L (%)"] = table_df["P/L (%)"].map(helpers.fmt_pct)
st.dataframe(display_df, use_container_width=True, hide_index=True)

# Delete controls
st.markdown('<div class="section-title">Manage Holdings</div>', unsafe_allow_html=True)
del_cols = st.columns(4)
for i, (_, r) in enumerate(table_df.iterrows()):
    col = del_cols[i % 4]
    if col.button(f"🗑️ Remove {r['Symbol']} (#{r['id']})", key=f"del_holding_{r['id']}"):
        db.delete_portfolio_entry(int(r["id"]))
        st.rerun()

# ---------------------------------------------------------------------------
# ALLOCATION CHART
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Portfolio Allocation (by Current Value)</div>', unsafe_allow_html=True)
alloc_df = table_df.dropna(subset=["Current Value"])
if not alloc_df.empty:
    fig = go.Figure(go.Pie(labels=alloc_df["Symbol"], values=alloc_df["Current Value"], hole=0.45))
    fig.update_layout(template="plotly_dark", height=420, paper_bgcolor="rgba(0,0,0,0)",
                       margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

csv_bytes = helpers.df_to_csv_bytes(table_df.drop(columns=["id"]))
excel_bytes = helpers.df_to_excel_bytes(table_df.drop(columns=["id"]), sheet_name="Portfolio")
pdf_bytes = helpers.df_to_pdf_bytes(display_df, title="Portfolio Report")

c1, c2, c3 = st.columns(3)
c1.download_button("⬇️ Export CSV", csv_bytes, "portfolio.csv", "text/csv", use_container_width=True)
c2.download_button("⬇️ Export Excel", excel_bytes, "portfolio.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
c3.download_button("⬇️ Export PDF", pdf_bytes, "portfolio.pdf", "application/pdf", use_container_width=True)
