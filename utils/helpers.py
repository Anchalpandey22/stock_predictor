"""
helpers.py
----------
Small shared utility functions used across pages: number formatting,
ticker validation, CSV/Excel/PDF export helpers, and sentiment badge
rendering. Keeping these here avoids repeating the same formatting logic
on every page.
"""

import io
import re
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

TICKER_PATTERN = re.compile(r"^[A-Za-z\.\-\^]{1,10}$")


def is_valid_ticker_format(symbol: str) -> bool:
    """Lightweight format check (not a live lookup) - rejects empty
    strings, spaces, and obviously invalid input before we even hit the
    network."""
    if not symbol:
        return False
    return bool(TICKER_PATTERN.match(symbol.strip()))


def fmt_currency(value, decimals=2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"${value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_large_number(value) -> str:
    """Formats large numbers like market cap into a readable form,
    e.g. 2_950_000_000_000 -> '$2.95T'."""
    if value is None or pd.isna(value):
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"${value/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"${value/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"${value/1e6:.2f}M"
    if abs_v >= 1e3:
        return f"${value/1e3:.2f}K"
    return f"${value:.2f}"


def fmt_pct(value, decimals=2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{value:+.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def fmt_volume(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if value >= 1e9:
        return f"{value/1e9:.2f}B"
    if value >= 1e6:
        return f"{value/1e6:.2f}M"
    if value >= 1e3:
        return f"{value/1e3:.2f}K"
    return f"{value:.0f}"


def sentiment_badge_html(sentiment: str) -> str:
    """Returns a small colored HTML badge for a sentiment label, used with
    st.markdown(..., unsafe_allow_html=True)."""
    colors_map = {
        "Positive": "#16C784",
        "Negative": "#EA3943",
        "Neutral": "#8a8f98",
    }
    color = colors_map.get(sentiment, "#8a8f98")
    return (
        f'<span style="background-color:{color}22;color:{color};'
        f'border:1px solid {color};padding:2px 10px;border-radius:12px;'
        f'font-size:0.78rem;font-weight:600;">{sentiment}</span>'
    )


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def df_to_excel_bytes(df: pd.DataFrame, sheet_name="Sheet1") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


def df_to_pdf_bytes(df: pd.DataFrame, title: str = "Report") -> bytes:
    """Renders a DataFrame as a simple, clean PDF table using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
        Spacer(1, 16),
    ]

    if df is None or df.empty:
        elements.append(Paragraph("No data available.", styles["Normal"]))
    else:
        display_df = df.copy().astype(str)
        table_data = [list(display_df.columns)] + display_df.values.tolist()
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


def check_alert_condition(price: float, condition: str, target: float) -> bool:
    if condition == ">":
        return price > target
    if condition == "<":
        return price < target
    if condition == ">=":
        return price >= target
    if condition == "<=":
        return price <= target
    return False
