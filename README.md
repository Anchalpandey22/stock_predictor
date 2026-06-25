#  StockSense — Real-Time Stock Market Dashboard

A full-stack, multi-page **Streamlit** dashboard for tracking stocks, building a portfolio,
running simple AI price predictions, reading market news with sentiment tagging, and more —
built as a student/portfolio project using free, public data sources (Yahoo Finance via
`yfinance`, and optionally NewsAPI for headlines).

>  **Disclaimer:** This project is for educational purposes only. Nothing in this dashboard
> — especially the AI Prediction page — is financial advice. Do not use it to make real
> investment decisions.

---

## Features

- **Home / Market Overview** — major indices (S&P 500, NASDAQ, Dow Jones), market open/closed
  status, top gainers, top losers, and most active stocks, plus a quick watchlist preview and
  recent activity feed.
- **Stock Analysis** — search any ticker (AAPL, TSLA, MSFT, NVDA, GOOGL, …) for a live quote
  (price, open, high/low, volume, market cap, P/E, EPS, dividend yield) and interactive
  candlestick / line / area / volume charts with zoom, pan, hover, and PNG export built in via
  Plotly.
- **Technical Indicators** — SMA (20/50/200), EMA (20), RSI (14), MACD (12/26/9), and Bollinger
  Bands, all toggle-able.
- **Compare Stocks** — overlay normalized performance, growth %, and volume for up to 8 tickers
  at once.
- **Watchlist** — add/remove favorite tickers, stored in SQLite and mirrored to
  `data/watchlist.csv`.
- **Portfolio Tracker** — log symbol/quantity/buy price, auto-calculates current value,
  profit/loss, return %, and a portfolio allocation pie chart. Stored in SQLite.
- **News & Sentiment** — headlines via NewsAPI (falls back to clearly-labeled sample headlines
  if no API key is configured) with Positive/Neutral/Negative sentiment badges.
- **AI Prediction** — Linear Regression and Random Forest models trained on lagged price
  features predict the next trading day's close, with an actual-vs-predicted chart on held-out
  test data and an evaluation metric (MAE, R²).
- **Sector Heatmap** — color-coded performance across Technology, Finance, Healthcare, Energy,
  Consumer Goods, and Communication sectors (using representative large-cap baskets).
- **Crypto Dashboard** — live Bitcoin, Ethereum, and Dogecoin prices, 24h % change, and
  historical charts.
- **Price Alerts** — create rules like "AAPL > 250", checked live against current prices, with
  a triggered/active status and notification banner.
- **Notes** — save, edit, search, and delete free-text notes, optionally linked to a ticker.
- **Reports** — export watchlist, portfolio, or any stock's history as CSV, Excel, or PDF, with
  an option to also save a copy into `/reports`.
- **Theming** — dark mode by default (configurable in `.streamlit/config.toml`), custom CSS for
  a clean financial-dashboard look.
- **Auto-refresh** — 5s / 30s / 60s live refresh option in the sidebar via
  `streamlit-autorefresh`.
- **Robust error handling** — invalid tickers, missing data, and network hiccups are caught and
  shown as friendly messages instead of crashing the app.

---

## Project Structure

```
RealTimeStockDashboard/
│
├── app.py                      # Entry point / Home page
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example                 # Template for NEWSAPI_KEY
│
├── .streamlit/
│   └── config.toml              # Theme + server config
│
├── assets/
│   ├── logo.png
│   └── background.jpg
│
├── pages/                       # Streamlit auto-discovers these as sidebar pages
│   ├── 1_Stock_Analysis.py
│   ├── 2_Compare_Stocks.py
│   ├── 3_Watchlist.py
│   ├── 4_Portfolio.py
│   ├── 5_News.py
│   ├── 6_AI_Prediction.py
│   ├── 7_Sector_Heatmap.py
│   ├── 8_Crypto.py
│   ├── 9_Alerts.py
│   ├── 10_Notes.py
│   └── 11_Reports.py
│
├── database/
│   ├── db.py                    # SQLite schema + CRUD helpers
│   └── database.db              # created automatically on first run
│
├── utils/
│   ├── api.py                   # yfinance / crypto / news fetching
│   ├── charts.py                 # Plotly chart builders
│   ├── indicators.py             # SMA / EMA / RSI / MACD / Bollinger
│   ├── prediction.py             # Linear Regression / Random Forest
│   └── helpers.py                # Formatting, validation, CSV/Excel/PDF export
│
├── data/
│   ├── watchlist.csv             # mirrored copy of the SQLite watchlist
│   └── portfolio.csv
│
├── reports/                      # generated report exports land here
├── static/
│   └── style.css                 # custom dashboard styling
└── screenshots/                  # add your own screenshots here for a portfolio README
```

---

##  Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure NewsAPI

The News page works out of the box with sample headlines. For live headlines, get a free key
from [newsapi.org](https://newsapi.org) and set it as an environment variable:

```bash
export NEWSAPI_KEY=your_key_here        # macOS/Linux
setx NEWSAPI_KEY "your_key_here"        # Windows
```

### 3. Run the app 

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. SQLite tables are created automatically on first
launch — there's no manual database setup step.

---

##  Dependencies

See `requirements.txt` for exact pinned versions. Major libraries:

| Library | Purpose |
|---|---|
| `streamlit` | App framework / UI |
| `streamlit-autorefresh` | Live auto-refresh |
| `yfinance` | Stock + crypto market data |
| `pandas` / `numpy` | Data wrangling |
| `plotly` | Interactive charts |
| `ta` | Technical indicators |
| `scikit-learn` | Linear Regression / Random Forest |
| `reportlab` | PDF report generation |
| `openpyxl` | Excel export |
| `requests` | NewsAPI calls |

---

##  Screenshots

> Add your own screenshots to the `/screenshots` folder and reference them here, e.g.:
>
> `![Home page](screenshots/home.png)`

---

##  Deployment

This app deploys cleanly to:

- **Streamlit Community Cloud** — push to a public GitHub repo, then "New app" → point at
  `app.py`. Add `NEWSAPI_KEY` under "Secrets" if you want live news.
- **Render** — create a new Web Service, build command `pip install -r requirements.txt`, start
  command `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
- **Railway** — same start command as Render; Railway auto-detects the `requirements.txt`.

> Note: SQLite is file-based and fine for a single-instance demo deployment, but it is **not**
> suited for multi-instance/horizontally-scaled production use — for that, swap `database/db.py`
> over to a hosted Postgres/MySQL database.

---

##  Future Enhancements

- Swap the keyword-based sentiment classifier for a real NLP model (e.g. VADER or a fine-tuned
  transformer).
- Add user authentication so multiple people can have separate watchlists/portfolios.
- Add more ML models (LSTM/Prophet) for prediction, with proper walk-forward validation.
- Push price-alert notifications via email/SMS instead of in-app banners only.
- Migrate SQLite → Postgres for real multi-user deployments.
- Add options-chain data and dividend-calendar views.

---

##  License & Disclaimer

Built as an educational/student portfolio project. All market data is provided "as is" via
free public sources and may be delayed. This is **not** financial advice — always do your own
research (or consult a licensed financial advisor) before making investment decisions.
