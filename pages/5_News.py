"""
pages/5_News.py
-----------------
Pulls financial headlines via NewsAPI (or sample data if no API key is
configured) and classifies each headline's sentiment as Positive,
Neutral, or Negative using a lightweight keyword-based classifier
(see utils/api.py::analyze_sentiment).
"""

import streamlit as st
from utils import api, helpers

st.set_page_config(page_title="Market News", page_icon="📰", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("📰 Market News & Sentiment")
st.caption("Latest headlines with automatic sentiment classification.")

query = st.text_input("Search news for", value="stock market")
page_size = st.slider("Number of articles", 5, 20, 10)

with st.spinner("Fetching news..."):
    articles, using_fallback = api.get_news(query=query, page_size=page_size)

if using_fallback:
    st.info(
        "ℹ️ Showing **sample headlines** because no `NEWSAPI_KEY` environment variable is set "
        "(or the live request failed). Get a free key at https://newsapi.org and set it as an "
        "environment variable named `NEWSAPI_KEY` to see live headlines."
    )

if not articles:
    st.warning("No articles found for this query.")
    st.stop()

sentiment_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

for article in articles:
    text_for_sentiment = f"{article['title']} {article.get('description', '')}"
    sentiment = api.analyze_sentiment(text_for_sentiment)
    sentiment_counts[sentiment] += 1

    st.markdown(
        f"""
        <div class="news-card">
            <div class="news-meta">{article['source']} · {article['publishedAt']}</div>
            <div style="font-size:1.05rem; font-weight:700; margin-bottom:6px;">
                <a href="{article['url']}" target="_blank" style="text-decoration:none; color:inherit;">{article['title']}</a>
            </div>
            <div style="margin-bottom:8px; opacity:0.85;">{article.get('description', 'No summary available.')}</div>
            {helpers.sentiment_badge_html(sentiment)}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.markdown('<div class="section-title">Sentiment Breakdown</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.metric("🟢 Positive", sentiment_counts["Positive"])
c2.metric("⚪ Neutral", sentiment_counts["Neutral"])
c3.metric("🔴 Negative", sentiment_counts["Negative"])

st.caption(
    "Sentiment is determined with a simple keyword-based classifier for transparency and "
    "speed - it's a good demonstration of the concept, not a production-grade NLP model."
)
