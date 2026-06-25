"""
pages/6_AI_Prediction.py
--------------------------
Next-day price prediction using Linear Regression and Random Forest
Regression, trained on lagged closing prices. Educational only - see the
disclaimer banner.
"""

import streamlit as st
from utils import api, prediction, charts, helpers

st.set_page_config(page_title="AI Prediction", page_icon="🤖", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("🤖 AI Price Prediction")

st.markdown(
    """<div class="disclaimer-box">
    ⚠️ <b>Educational purposes only.</b> These predictions come from simple Linear Regression
    and Random Forest models trained on a handful of lagged price features. They are
    <b>not</b> financial advice and should never be used to make real investment decisions.
    Stock prices are influenced by countless factors no small model can capture.
    </div>""",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
symbol = c1.text_input("Ticker symbol", value="AAPL").strip().upper()
model_type = c2.selectbox("Model", ["Linear Regression", "Random Forest"])
period = c3.selectbox("Training data period", ["6mo", "1y", "2y", "5y"], index=2)

if not symbol or not helpers.is_valid_ticker_format(symbol):
    st.info("Enter a valid ticker symbol to run a prediction, e.g. AAPL, TSLA, MSFT.")
    st.stop()

with st.spinner("Fetching historical data..."):
    hist = api.get_stock_history(symbol, period=period)

if hist.empty or len(hist) < 40:
    st.error(f"Not enough historical data for {symbol} to train a model. Try a longer period.")
    st.stop()

with st.spinner(f"Training {model_type} model..."):
    result = prediction.train_and_predict(hist, model_type=model_type)

if result is None:
    st.error("Not enough data after feature engineering to train a model. Try a longer period.")
    st.stop()

# ---------------------------------------------------------------------------
# RESULTS
# ---------------------------------------------------------------------------
trend = prediction.trend_label(result["last_actual_close"], result["next_day_prediction"])
trend_css = "kpi-up" if "Bullish" in trend else ("kpi-down" if "Bearish" in trend else "kpi-flat")

m1, m2, m3, m4 = st.columns(4)
m1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Last Close</div>
    <div class="kpi-value">{helpers.fmt_currency(result['last_actual_close'])}</div></div>""", unsafe_allow_html=True)
m2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Next-Day Prediction</div>
    <div class="kpi-value">{helpers.fmt_currency(result['next_day_prediction'])}</div></div>""", unsafe_allow_html=True)
m3.markdown(f"""<div class="kpi-card"><div class="kpi-label">Predicted Trend</div>
    <div class="kpi-value {trend_css}" style="font-size:1.05rem;">{trend}</div></div>""", unsafe_allow_html=True)
m4.markdown(f"""<div class="kpi-card"><div class="kpi-label">Model Accuracy (R²)</div>
    <div class="kpi-value">{result['r2']:.3f}</div></div>""", unsafe_allow_html=True)

st.caption(f"Mean Absolute Error on the test set: {helpers.fmt_currency(result['mae'])} "
           f"— on average, the model's test-set predictions were off by about this much.")

st.divider()
st.markdown('<div class="section-title">Actual vs Predicted (Test Set)</div>', unsafe_allow_html=True)
fig = charts.prediction_chart(result["dates"], result["actual"], result["predicted"], symbol, model_type)
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

st.markdown(
    "**How this works:** the model is trained on the first 80% of the historical data "
    "(by date) and evaluated on the most recent 20% it has never seen, using lagged closing "
    "prices and rolling statistics as features. The chart above compares what actually "
    "happened against what the model would have predicted for those unseen days."
)
