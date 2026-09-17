"""
Aggregate stats across every statement ever run through this app.

This reads history.py's own tables, so it needs zero new instrumentation
to start giving numbers. Use impact_report.py to print a resume-ready
summary at any point.

These are usage/volume numbers (statements processed, money categorized),
not visitor counts. See sessions.py for that half.
"""

from src.history import connect


def totals():
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*)               AS statements,
                COALESCE(SUM(transactions), 0) AS transactions,
                COALESCE(SUM(money_in), 0)     AS money_in,
                COALESCE(SUM(money_out), 0)    AS money_out,
                MIN(uploaded_at)       AS first_run,
                MAX(uploaded_at)       AS last_run
            FROM statement_runs
            """
        ).fetchone()

    if not row or not row["statements"]:
        return None

    return {
        "statements": int(row["statements"]),
        "transactions": int(row["transactions"]),
        "money_in": float(row["money_in"]),
        "money_out": float(row["money_out"]),
        "money_moved": float(row["money_in"]) + float(row["money_out"]),
        "first_run": row["first_run"],
        "last_run": row["last_run"],
    }


def merchants_known():
    """Distinct payees the classifier has ever seen, across statements."""
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT(DISTINCT payee) AS n FROM month_payee"
        ).fetchone()
    return int(row["n"]) if row else 0


def categories_used():
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT(DISTINCT category) AS n FROM month_category"
        ).fetchone()
    return int(row["n"]) if row else 0
