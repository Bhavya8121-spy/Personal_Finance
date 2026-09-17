"""
Anonymous session counting for a deployed app.

This is meaningless while the app runs only on your own machine — every
session would be you. It becomes a real number once the app is deployed
(e.g. Streamlit Community Cloud) and other people can open the link.

What's logged: a random id generated fresh per browser tab, and a
timestamp. Nothing identifying — no IP, no name, no email. Call
log_session() once near the top of app.py; it only writes once per tab
thanks to session_state.
"""

import uuid

import streamlit as st

from src.history import connect


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    seen_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def create_session_table():
    with connect() as connection:
        connection.executescript(SCHEMA)


def log_session():
    """
    Record one app open per browser tab. Safe to call on every rerun —
    it only inserts the first time, using Streamlit's session_state as
    the guard.
    """
    if st.session_state.get("_session_logged"):
        return

    session_id = str(uuid.uuid4())

    with connect() as connection:
        connection.execute(
            "INSERT INTO sessions (session_id) VALUES (?)",
            (session_id,),
        )

    st.session_state["_session_logged"] = True


def totals():
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*)                        AS sessions,
                COUNT(DISTINCT DATE(seen_at))   AS days,
                MIN(seen_at)                     AS first_seen,
                MAX(seen_at)                     AS last_seen
            FROM sessions
            """
        ).fetchone()

    if not row or not row["sessions"]:
        return None

    return {
        "sessions": int(row["sessions"]),
        "days": int(row["days"]),
        "first_seen": row["first_seen"],
        "last_seen": row["last_seen"],
    }
