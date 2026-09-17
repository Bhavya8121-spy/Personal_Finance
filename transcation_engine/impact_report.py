"""
Print a plain summary of everything the app has processed so far.

    python impact_report.py

Run this any time. It only reads data/transactions.db — it never talks to
Gemini, never touches your uploads, and never runs analysis itself.
"""

from src import impact, sessions


def line(label, value):
    print(f"{label:<28}{value}")


if __name__ == "__main__":

    stats = impact.totals()

    if not stats:
        print("No statements have been processed yet. Run app.py and upload one.")
    else:
        print("STATEMENT VOLUME")
        print("-" * 40)
        line("Statements processed", stats["statements"])
        line("Transactions classified", f"{stats['transactions']:,}")
        line("Money in (tracked)", f"{stats['money_in']:,.2f}")
        line("Money out (tracked)", f"{stats['money_out']:,.2f}")
        line("Total money moved", f"{stats['money_moved']:,.2f}")
        line("Distinct merchants seen", impact.merchants_known())
        line("Categories in use", impact.categories_used())
        line("First run", stats["first_run"])
        line("Latest run", stats["last_run"])

    print()
    print("SESSIONS")
    print("-" * 40)
    session_stats = sessions.totals()
    if session_stats:
        line("App opens (sessions)", session_stats["sessions"])
        line("Distinct days used", session_stats["days"])
        line("First seen", session_stats["first_seen"])
        line("Last seen", session_stats["last_seen"])
    else:
        print("No sessions logged yet — see sessions.py to enable this.")
