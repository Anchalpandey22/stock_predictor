"""
pages/10_Notes.py
-------------------
Save personal observations about stocks (or general market notes), edit
them, and delete them. Stored in SQLite.
"""

import streamlit as st
from database import db

st.set_page_config(page_title="Notes", page_icon="📝", layout="wide")

try:
    with open("static/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("📝 Notes")
st.caption("Jot down personal observations, theses, or reminders - optionally linked to a ticker.")

with st.form("add_note_form", clear_on_submit=True):
    c1, c2 = st.columns([1, 3])
    symbol = c1.text_input("Symbol (optional)", placeholder="e.g. AAPL")
    title = c2.text_input("Title", placeholder="e.g. Q3 earnings thoughts")
    content = st.text_area("Note", placeholder="Write your note here...", height=120)
    submitted = st.form_submit_button("💾 Save Note")

    if submitted:
        if not title.strip() or not content.strip():
            st.error("Please provide both a title and some content.")
        else:
            db.add_note(title.strip(), content.strip(), symbol.strip().upper() if symbol.strip() else None)
            st.success("Note saved!")
            st.rerun()

st.divider()

notes_df = db.get_notes()

if notes_df.empty:
    st.info("📭 No notes yet. Add one above.")
    st.stop()

search = st.text_input("🔍 Search notes by title, content, or symbol", "")
if search:
    mask = (
        notes_df["title"].str.contains(search, case=False, na=False)
        | notes_df["content"].str.contains(search, case=False, na=False)
        | notes_df["symbol"].str.contains(search, case=False, na=False)
    )
    notes_df = notes_df[mask]

for _, note in notes_df.iterrows():
    with st.expander(f"📄 {note['title']}" + (f"  ·  {note['symbol']}" if note["symbol"] else "")):
        edit_key = f"editing_{note['id']}"
        if st.session_state.get(edit_key, False):
            new_title = st.text_input("Title", value=note["title"], key=f"title_{note['id']}")
            new_content = st.text_area("Content", value=note["content"], key=f"content_{note['id']}", height=120)
            c1, c2 = st.columns(2)
            if c1.button("💾 Save changes", key=f"save_{note['id']}"):
                db.update_note(int(note["id"]), new_title, new_content)
                st.session_state[edit_key] = False
                st.rerun()
            if c2.button("✖️ Cancel", key=f"cancel_{note['id']}"):
                st.session_state[edit_key] = False
                st.rerun()
        else:
            st.write(note["content"])
            st.caption(f"Created: {note['created_on']}  ·  Last updated: {note['updated_on']}")
            c1, c2 = st.columns(2)
            if c1.button("✏️ Edit", key=f"edit_{note['id']}"):
                st.session_state[edit_key] = True
                st.rerun()
            if c2.button("🗑️ Delete", key=f"delete_{note['id']}"):
                db.delete_note(int(note["id"]))
                st.rerun()
