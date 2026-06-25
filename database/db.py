"""
database/db.py
---------------
Central SQLite database handler for the Stock Market Dashboard.

All tables are created automatically on first launch (see init_db(),
called once at the top of app.py), so the app works immediately after a
fresh clone with no manual setup step.

Tables:
    watchlist     -> saved tickers the user wants to keep an eye on
    portfolio     -> stocks the user "owns" (symbol, qty, buy price, buy date)
    alerts        -> price alert rules (symbol, condition, target price, status)
    notes         -> free-text notes, optionally linked to a symbol
    activity_log  -> a simple log used for the "Recent Activity" feed on
                      the Home page (e.g. "Added AAPL to watchlist")

Every get_* function returns a pandas DataFrame so pages can hand the
result straight to st.dataframe() or iterate over it with .iterrows().
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "database.db")


def get_connection():
    """Return a new sqlite3 connection. check_same_thread=False because
    Streamlit's execution model can touch this from more than one thread."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create every table if it doesn't already exist. Idempotent - safe
    to call on every single app start."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            added_on TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            buy_price REAL NOT NULL,
            buy_date TEXT NOT NULL,
            created_on TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            condition TEXT NOT NULL CHECK(condition IN ('>', '<', '>=', '<=')),
            target_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_on TEXT NOT NULL,
            triggered_on TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_on TEXT NOT NULL,
            updated_on TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            created_on TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# ACTIVITY LOG
# ---------------------------------------------------------------------------
def log_activity(action: str, details: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO activity_log (action, details, created_on) VALUES (?, ?, ?)",
        (action, details, _now()),
    )
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 8) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT action, details, created_on FROM activity_log ORDER BY id DESC LIMIT ?",
        conn, params=(limit,),
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# WATCHLIST
# ---------------------------------------------------------------------------
def add_to_watchlist(symbol: str) -> bool:
    symbol = symbol.upper().strip()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO watchlist (symbol, added_on) VALUES (?, ?)",
            (symbol, _now()),
        )
        conn.commit()
        log_activity("Added to watchlist", symbol)
        return True
    except sqlite3.IntegrityError:
        return False  # already in watchlist
    finally:
        conn.close()


def remove_from_watchlist(symbol: str):
    symbol = symbol.upper().strip()
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()
    log_activity("Removed from watchlist", symbol)


def get_watchlist() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY added_on DESC", conn)
    conn.close()
    return df


# ---------------------------------------------------------------------------
# PORTFOLIO
# ---------------------------------------------------------------------------
def add_portfolio_entry(symbol, quantity, buy_price, buy_date):
    conn = get_connection()
    conn.execute(
        """INSERT INTO portfolio (symbol, quantity, buy_price, buy_date, created_on)
           VALUES (?, ?, ?, ?, ?)""",
        (symbol.upper().strip(), float(quantity), float(buy_price), str(buy_date), _now()),
    )
    conn.commit()
    conn.close()
    log_activity("Added portfolio holding", f"{symbol.upper()} x{quantity}")


def delete_portfolio_entry(entry_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM portfolio WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    log_activity("Removed portfolio holding", f"id={entry_id}")


def get_portfolio() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, symbol, quantity, buy_price, buy_date FROM portfolio ORDER BY created_on DESC",
        conn,
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# ALERTS
# ---------------------------------------------------------------------------
def add_alert(symbol, condition, target_price):
    conn = get_connection()
    conn.execute(
        """INSERT INTO alerts (symbol, condition, target_price, status, created_on)
           VALUES (?, ?, ?, 'ACTIVE', ?)""",
        (symbol.upper().strip(), condition, float(target_price), _now()),
    )
    conn.commit()
    conn.close()
    log_activity("Created alert", f"{symbol.upper()} {condition} {target_price}")


def get_alerts(status: str = None) -> pd.DataFrame:
    conn = get_connection()
    if status:
        df = pd.read_sql_query(
            "SELECT * FROM alerts WHERE status = ? ORDER BY id DESC", conn, params=(status,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM alerts ORDER BY id DESC", conn)
    conn.close()
    return df


def mark_alert_triggered(alert_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE alerts SET status = 'TRIGGERED', triggered_on = ? WHERE id = ?",
        (_now(), alert_id),
    )
    conn.commit()
    conn.close()


def delete_alert(alert_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# NOTES
# ---------------------------------------------------------------------------
def add_note(title, content, symbol=None):
    now = _now()
    conn = get_connection()
    conn.execute(
        """INSERT INTO notes (symbol, title, content, created_on, updated_on)
           VALUES (?, ?, ?, ?, ?)""",
        (symbol.upper().strip() if symbol else None, title.strip(), content.strip(), now, now),
    )
    conn.commit()
    conn.close()
    log_activity("Added note", title)


def update_note(note_id, title, content):
    conn = get_connection()
    conn.execute(
        "UPDATE notes SET title = ?, content = ?, updated_on = ? WHERE id = ?",
        (title.strip(), content.strip(), _now(), note_id),
    )
    conn.commit()
    conn.close()


def delete_note(note_id):
    conn = get_connection()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()


def get_notes() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM notes ORDER BY updated_on DESC", conn)
    conn.close()
    return df
