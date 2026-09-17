"""
Habit detection.

Two different questions, answered separately:

  find_recurring()  "what charges you on a schedule?"      -> subscriptions
  find_leaks()      "what small thing adds up?"            -> spending leaks

Both work on a single statement. Cross-statement memory (your "show them
this habit is repeated") lives in history.py and is merged in by
add_history().
"""

import statistics

from src.analytics import normalize


# ----------------------------------------------------------------------
# Recurring charges
# ----------------------------------------------------------------------

def find_recurring(results_df, min_hits=3, amount_tolerance=0.15):
    """
    A charge is recurring when the same payee appears several times for a
    similar amount. If those hits are also spaced about a month apart, we
    call it a subscription.
    """
    df = normalize(results_df)
    spending = df[df["Spent"] > 0]

    found = []

    for payee, group in spending.groupby("Payee"):

        if len(group) < min_hits:
            continue

        amounts = group["Spent"].tolist()
        average = statistics.mean(amounts)

        if average <= 0:
            continue

        # How steady is the amount? Low spread means a fixed charge.
        spread = statistics.pstdev(amounts) / average

        dates = group["Date"].dropna().sort_values()
        cadence = None

        if len(dates) >= 2:
            gaps = dates.diff().dropna().dt.days
            gaps = [gap for gap in gaps if gap > 0]
            if gaps:
                cadence = statistics.median(gaps)

        looks_monthly = cadence is not None and 25 <= cadence <= 35
        fixed_amount = spread <= amount_tolerance

        found.append({
            "payee": payee,
            "category": group["Category"].mode().iat[0] if not group["Category"].isna().all() else None,
            "occurrences": int(len(group)),
            "total": float(group["Spent"].sum()),
            "average": float(average),
            "amount_spread": float(spread),
            "cadence_days": float(cadence) if cadence else None,
            "is_subscription": bool(fixed_amount and looks_monthly),
            "monthly_cost": float(average) if looks_monthly else None,
            "annual_cost": float(average * 12) if looks_monthly else None,
        })

    found.sort(key=lambda item: item["total"], reverse=True)
    return found


# ----------------------------------------------------------------------
# Spending leaks
# ----------------------------------------------------------------------

def find_leaks(results_df, min_hits=3, limit=5):
    """
    The discretionary payees you visit most. This is the "here is the exact
    payment to cut" list, ranked by what it costs over a year if nothing
    changes.

    Only discretionary buckets are considered, so rent and medical bills
    never show up here.
    """
    df = normalize(results_df)

    spending = df[(df["Spent"] > 0) & (df["Bucket"] == "discretionary")]

    if spending.empty:
        return []

    months = max(len({m for m in spending["Month"] if m != "Unknown"}), 1)

    leaks = []

    for payee, group in spending.groupby("Payee"):

        if len(group) < min_hits:
            continue

        total = float(group["Spent"].sum())
        per_month = total / months

        leaks.append({
            "payee": payee,
            "category": group["Category"].mode().iat[0] if not group["Category"].isna().all() else None,
            "visits": int(len(group)),
            "total": total,
            "average_ticket": total / len(group),
            "monthly_cost": per_month,
            "annual_cost": per_month * 12,
            "dates": [d for d in group["Date"].dropna().sort_values()],
        })

    leaks.sort(key=lambda item: item["annual_cost"], reverse=True)
    return leaks[:limit]


# ----------------------------------------------------------------------
# Cross-statement memory
# ----------------------------------------------------------------------

def add_history(items, lookup):
    """
    Attach past-statement context to leaks or recurring charges.

    `lookup` is any callable taking a payee name and returning a dict like
    {"months_seen": 4, "lifetime_total": 812.40, "first_seen": "2025-11"}.
    history.merchant_history is the one to pass in.

    Items without history simply come back unchanged, so this is safe to
    call on a user's very first upload.
    """
    enriched = []

    for item in items:
        past = lookup(item["payee"]) or {}

        item = dict(item)
        item["months_seen"] = past.get("months_seen", 0)
        item["lifetime_total"] = past.get("lifetime_total")
        item["first_seen"] = past.get("first_seen")
        item["is_repeat"] = past.get("months_seen", 0) >= 2

        enriched.append(item)

    return enriched


def worst_offender(leaks):
    """The single habit worth naming. None when nothing qualifies."""
    if not leaks:
        return None

    repeats = [leak for leak in leaks if leak.get("is_repeat")]
    pool = repeats or leaks

    return max(pool, key=lambda leak: leak["annual_cost"])
