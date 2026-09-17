"""
Run the new modules against fake data, without Streamlit and without
touching your engine or Gemini.

    python smoke_test.py

If this prints numbers and sentences, the analytics layer is wired
correctly and any problem is in the interface, not the logic.
"""

import os
import random
import tempfile
from datetime import date, timedelta

import pandas as pd

# Keep the smoke test out of your real database
os.environ.setdefault("FINANCE_DB", os.path.join(tempfile.gettempdir(), "smoke.db"))

from src import analytics, commentary, goals, habits, history, investments, planner


MERCHANTS = [
    ("Starbucks", "Food & Dining", -6.50, 22),
    ("Chipotle", "Food & Dining", -14.20, 9),
    ("Amazon", "Shopping", -38.00, 7),
    ("Netflix", "Subscriptions", -15.49, 3),
    ("Spotify", "Subscriptions", -11.99, 3),
    ("Shell", "Transport", -45.00, 5),
    ("Kroger", "Groceries", -82.00, 6),
    ("City Rent", "Housing", -1450.00, 3),
    ("Robinhood", "Investments", -200.00, 3),
    ("Employer Payroll", "Income", 2600.00, 3),
]


def fake_statement(months=3, seed=7):
    random.seed(seed)
    start = date.today().replace(day=1) - timedelta(days=30 * months)
    rows = []

    for name, category, amount, count in MERCHANTS:
        for _ in range(count):
            offset = random.randint(0, 30 * months)
            jitter = 1 if abs(amount) > 500 else random.uniform(0.85, 1.15)
            rows.append({
                "Date": start + timedelta(days=offset),
                "Description": f"{name.upper()} #{random.randint(1000, 9999)}",
                "Amount": round(amount * jitter, 2),
                "Merchant": name,
                "Category": category,
                "Subcategory": "General",
                "Review Required": False,
                "Review Reason": None,
                "Source": "merchant_database",
                "Merchant Confidence": 0.9,
                "Category Confidence": 0.9,
                "Transaction Type": "debit" if amount < 0 else "credit",
            })

    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)


def show(title):
    print("\n" + title)
    print("-" * len(title))


if __name__ == "__main__":

    df = fake_statement()

    # ---- analytics
    summary = analytics.summarize(df)
    show("Summary")
    print(f"transactions : {summary['transactions']}")
    print(f"money in     : {summary['money_in']:,.2f}")
    print(f"money out    : {summary['money_out']:,.2f}")
    print(f"net          : {summary['net']:,.2f}")
    print(f"months       : {summary['month_count']}")
    print(f"essentials   : {summary['essentials']:,.2f}")
    print(f"discretionary: {summary['discretionary']:,.2f}")
    print(f"trend ok     : {analytics.enough_for_trend(summary)}")

    # ---- history (writes to a temp db)
    history.create_history_tables()
    run_id = history.save_run(df, summary)
    print(f"history run  : {run_id}, total runs {history.run_count()}")

    # ---- habits
    leaks = habits.add_history(habits.find_leaks(df), history.merchant_history)
    show("Leaks")
    for leak in leaks:
        print(f"{leak['payee']:<20} {leak['visits']:>3} visits  "
              f"{leak['annual_cost']:>10,.0f}/yr  repeat={leak['is_repeat']}")

    show("Recurring")
    for item in habits.find_recurring(df):
        if item["is_subscription"]:
            print(f"{item['payee']:<20} every {item['cadence_days']:.0f}d  "
                  f"{item['average']:,.2f}")

    # ---- commentary
    show("Commentary")
    for line in commentary.generate(summary, leaks, currency="$"):
        print(f"[{line['kind']}] {line['text']}")

    # ---- investments
    detection = investments.detect(df)
    show("Investments")
    print(investments.prompt_text(detection) or "nothing detected")

    # ---- planner
    capacity = planner.capacity(summary)
    fund = planner.emergency_fund(summary)
    show("Planner")
    print(f"monthly spare : {capacity['monthly_spare']:,.2f}")
    print(f"buffer target : {fund['target_low']:,.0f} to {fund['target_high']:,.0f}")
    band = planner.horizon_guidance(10)
    print(f"10y horizon   : {band['label']} / {band['typical_mix']}")

    # ---- goals
    show("Goal: 40,000 car in 4 years")
    plan = goals.allocate(40000, 4, main_savings=500, main_investing=150)
    print(f"needed monthly    : {plan['required_monthly']:,.2f}")
    print(f"goal savings      : {plan['goal_savings']:,.2f}")
    print(f"goal investing    : {plan['goal_investing']:,.2f}")
    print(f"main savings left : {plan['remaining_savings']:,.2f}")
    print(f"main invest left  : {plan['remaining_investing']:,.2f}")
    print(f"feasible          : {plan['feasible']}")
    print(f"projected value   : {plan['projected_value']:,.2f}")

    print("\nAll modules ran.")
