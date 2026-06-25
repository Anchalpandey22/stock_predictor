"""
pages/9_Alerts.py
--------------------
Create price alert rules like "AAPL > 250" or "TSLA < 300". Alerts are
stored in SQLite and checked live whenever this page loads (or on
auto-refresh) - if the condition is met, the alert is marked TRIGGERED
and a notification banner is shown.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from database import db
from utils import api, helpers

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

_interval_map = {"5 seconds": 5000, "30 seconds": 30000, "60 seconds": 60000}
interval = st.session_state.get("refresh_interval", "Off")
if interval in _interval_map:
    st_autorefresh(interval=_interval_map[interval], key="alerts_autorefresh")

st.title("🔔 Price Alerts")
st.caption('Create rules like "AAPL > 250" or "TSLA < 300" and get notified when they trigger.')

with st.form("add_alert_form", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([2, 1, 1.5, 1])
    symbol = c1.text_input("Symbol", placeholder="e.g. AAPL")
    condition = c2.selectbox("Condition", [">", "<", ">=", "<="])
    target_price = c3.number_input("Target price ($)", min_value=0.0, value=100.0, step=1.0)
    submitted = c4.form_submit_button("🔔 Create", use_container_width=True)

    if submitted:
        symbol = symbol.strip().upper()
        if not helpers.is_valid_ticker_format(symbol):
            st.error("Please enter a valid ticker symbol.")
        else:
            db.add_alert(symbol, condition, target_price)
            st.success(f"Alert created: {symbol} {condition} {target_price}")
            st.rerun()

st.divider()

alerts_df = db.get_alerts()

if alerts_df.empty:
    st.info("📭 No alerts yet. Create one above.")
    st.stop()

# ---------------------------------------------------------------------------
# CHECK ACTIVE ALERTS AGAINST LIVE PRICES
# ---------------------------------------------------------------------------
active_alerts = alerts_df[alerts_df["status"] == "ACTIVE"]
newly_triggered = []

with st.spinner("Checking live prices against active alerts..."):
    for _, alert in active_alerts.iterrows():
        info = api.get_stock_info(alert["symbol"])
        if info is None:
            continue
        if helpers.check_alert_condition(info["current_price"], alert["condition"], alert["target_price"]):
            db.mark_alert_triggered(int(alert["id"]))
            newly_triggered.append((alert["symbol"], alert["condition"], alert["target_price"], info["current_price"]))

if newly_triggered:
    for sym, cond, target, price in newly_triggered:
        st.success(f"🔔 **Alert triggered!** {sym} is now {helpers.fmt_currency(price)}, "
                    f"which satisfies your rule: {sym} {cond} {target}")
    alerts_df = db.get_alerts()  # refresh after updates

st.markdown('<div class="section-title">Active Alerts</div>', unsafe_allow_html=True)
active_df = alerts_df[alerts_df["status"] == "ACTIVE"]
if active_df.empty:
    st.caption("No active alerts.")
else:
    for _, a in active_df.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"""<div class="stock-row">
            <span class="chip chip-open">ACTIVE</span> &nbsp; <b>{a['symbol']}</b> {a['condition']} {a['target_price']}
            &nbsp; <span style="opacity:0.6; font-size:0.8rem;">created {a['created_on']}</span>
        </div>""", unsafe_allow_html=True)
        if c2.button("🗑️ Delete", key=f"del_alert_{a['id']}"):
            db.delete_alert(int(a["id"]))
            st.rerun()

st.markdown('<div class="section-title">Triggered Alerts</div>', unsafe_allow_html=True)
triggered_df = alerts_df[alerts_df["status"] == "TRIGGERED"]
if triggered_df.empty:
    st.caption("No alerts have triggered yet.")
else:
    for _, a in triggered_df.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"""<div class="stock-row">
            <span class="chip chip-closed">TRIGGERED</span> &nbsp; <b>{a['symbol']}</b> {a['condition']} {a['target_price']}
            &nbsp; <span style="opacity:0.6; font-size:0.8rem;">triggered {a['triggered_on']}</span>
        </div>""", unsafe_allow_html=True)
        if c2.button("🗑️ Delete", key=f"del_alert_t_{a['id']}"):
            db.delete_alert(int(a["id"]))
            st.rerun()

st.caption("💡 Tip: turn on auto-refresh in the sidebar (on the Home page) so alerts are checked "
           "continuously without you needing to manually reload this page.")
