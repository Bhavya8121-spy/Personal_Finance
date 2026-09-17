"""
Memory across uploads.

Your engine already remembers merchants. This remembers *statements*, so
the app can say "this is the fourth month running" instead of judging a
habit from a single file.

Nothing personal is stored beyond what is needed for that: a month, a
payee name, and totals. No raw statement rows, no account numbers.
"""

import os
import sqlite3
from contextlib import contextmanager

from src.analytics import normalize


# ----------------------------------------------------------------------
# Finding your existing database
#
# src/database.py already owns the connection. We try to reuse its path so
# everything lives in one file. If the name does not match, set FINANCE_DB
# or edit DEFAULT_DB below.
# ----------------------------------------------------------------------

DEFAULT_DB = "data/app.db"

CANDIDATE_NAMES = (
    "DB_PATH", "DATABASE_PATH", "DB_FILE", "DB_NAME", "DATABASE", "DB",
)


def db_path():
    try:
        import src.database as database
    except Exception:
        database = None

    if database is not None:
        for name in CANDIDATE_NAMES:
            value = getattr(database, name, None)
            if isinstance(value, str) and value.endswith((".db", ".sqlite", ".sqlite3")):
                return value

    return os.environ.get("FINANCE_DB", DEFAULT_DB)


@contextmanager
def connect():
    path = db_path()
    folder = os.path.dirname(path)

    if folder:
        os.makedirs(folder, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS statement_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uploaded_at   TEXT NOT NULL DEFAULT (datetime('now')),
    period_start  TEXT,
    period_end    TEXT,
    transactions  INTEGER,
    money_in      REAL,
    money_out     REAL
);

CREATE TABLE IF NOT EXISTS month_category (
    run_id    INTEGER,
    month     TEXT,
    category  TEXT,
    spent     REAL,
    txn_count INTEGER,
    FOREIGN KEY (run_id) REFERENCES statement_runs(id)
);

CREATE TABLE IF NOT EXISTS month_payee (
    run_id    INTEGER,
    month     TEXT,
    payee     TEXT,
    spent     REAL,
    txn_count INTEGER,
    FOREIGN KEY (run_id) REFERENCES statement_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_month_payee ON month_payee(payee);
CREATE INDEX IF NOT EXISTS idx_month_category ON month_category(category);
"""


def create_history_tables():
    """Call once at startup, next to your existing create_tables()."""
    with connect() as connection:
        connection.executescript(SCHEMA)


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------

def save_run(results_df, summary):
    """Record one analysed statement. Returns the run id."""
    df = normalize(results_df)
    spending = df[df["Spent"] > 0]

    with connect() as connection:

        cursor = connection.execute(
            """
            INSERT INTO statement_runs
                (period_start, period_end, transactions, money_in, money_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(summary["start"].date()) if summary["start"] is not None else None,
                str(summary["end"].date()) if summary["end"] is not None else None,
                summary["transactions"],
                summary["money_in"],
                summary["money_out"],
            ),
        )

        run_id = cursor.lastrowid

        by_category = (
            spending.groupby(["Month", "Category"])
            .agg(spent=("Spent", "sum"), count=("Description", "count"))
            .reset_index()
        )

        connection.executemany(
            "INSERT INTO month_category (run_id, month, category, spent, txn_count)"
            " VALUES (?, ?, ?, ?, ?)",
            [
                (run_id, row.Month, row.Category, float(row.spent), int(row.count))
                for row in by_category.itertuples()
            ],
        )

        by_payee = (
            spending.groupby(["Month", "Payee"])
            .agg(spent=("Spent", "sum"), count=("Description", "count"))
            .reset_index()
        )

        connection.executemany(
            "INSERT INTO month_payee (run_id, month, payee, spent, txn_count)"
            " VALUES (?, ?, ?, ?, ?)",
            [
                (run_id, row.Month, row.Payee, float(row.spent), int(row.count))
                for row in by_payee.itertuples()
            ],
        )

    return run_id


# ----------------------------------------------------------------------
# Reading
# ----------------------------------------------------------------------

def merchant_history(payee):
    """
    Everything we know about one payee across every upload. Shaped for
    habits.add_history().
    """
    with connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT month) AS months_seen,
                   SUM(spent)            AS lifetime_total,
                   SUM(txn_count)        AS lifetime_count,
                   MIN(month)            AS first_seen
            FROM month_payee
            WHERE payee = ?
            """,
            (payee,),
        ).fetchone()

    if not row or not row["months_seen"]:
        return None

    return {
        "months_seen": int(row["months_seen"]),
        "lifetime_total": float(row["lifetime_total"] or 0),
        "lifetime_count": int(row["lifetime_count"] or 0),
        "first_seen": row["first_seen"],
    }


def category_history(limit_months=12):
    """Spend per category per month across all uploads, newest last."""
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT month, category, SUM(spent) AS spent
            FROM month_category
            GROUP BY month, category
            ORDER BY month
            """
        ).fetchall()

    return [dict(row) for row in rows]


def run_count():
    """How many statements this user has analysed. Gates the history UI."""
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM statement_runs"
        ).fetchone()

    return int(row["total"]) if row else 0
