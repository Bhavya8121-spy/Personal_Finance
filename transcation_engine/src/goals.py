"""
Goal buckets.

This is the mechanic from your brief: a person has a main savings flow and
a main investment flow, they want a car or a house, and the app carves a
slice out of each into a goal bucket.

Worked example from your notes:

    target = 40,000
    main savings   = 500 / month
    main investing = 150 / month

    allocate() decides how much of that 650 goes to the car and what is
    left running into the main pots.

The split between the car's cash bucket and the car's invested bucket is
decided by how far away the purchase is, not by preference, because money
needed soon should not be exposed to a market drop.
"""

from src.planner import DISCLAIMER, future_value


# Share of a goal contribution that goes to cash rather than investments,
# by how many years away the purchase is.
CASH_SHARE_BY_HORIZON = (
    (2, 1.00),    # under 2 years: all cash
    (4, 0.75),
    (7, 0.50),
    (99, 0.30),   # far away: mostly invested
)

# Never drain a pot entirely into one goal.
MAX_DRAW = 0.70

CASH_RATE = 0.02
INVEST_RATE = 0.05


def cash_share(years):
    for limit, share in CASH_SHARE_BY_HORIZON:
        if years <= limit:
            return share
    return CASH_SHARE_BY_HORIZON[-1][1]


def required_monthly(target, years, blended_rate=None):
    """
    What you need to put aside each month to reach the target, ignoring
    growth by default so the number is never optimistic.
    """
    months = max(int(round(years * 12)), 1)

    if not blended_rate:
        return target / months

    rate = blended_rate / 12
    return target * rate / ((1 + rate) ** months - 1)


def allocate(target, years, main_savings, main_investing, already_saved=0.0):
    """
    Work out the goal bucket and what survives in the main pots.

    Returns everything the interface needs to show both sides of the split,
    plus a feasibility verdict when the goal does not fit.
    """
    remaining_target = max(target - already_saved, 0)

    needed = required_monthly(remaining_target, years)

    pool = main_savings + main_investing
    ceiling = (main_savings * MAX_DRAW) + (main_investing * MAX_DRAW)

    feasible = needed <= ceiling
    taken = min(needed, ceiling)

    # Split the draw across the two pots by horizon, then clamp each to
    # what that pot can actually give.
    share = cash_share(years)

    from_savings = min(taken * share, main_savings * MAX_DRAW)
    from_investing = min(taken - from_savings, main_investing * MAX_DRAW)

    # If the investing pot could not cover its part, try savings again.
    shortfall_in_split = taken - (from_savings + from_investing)
    if shortfall_in_split > 0:
        extra = min(shortfall_in_split, main_savings * MAX_DRAW - from_savings)
        from_savings += max(extra, 0)

    goal_monthly = from_savings + from_investing

    projected = (
        already_saved
        + future_value(from_savings, years, CASH_RATE)
        + future_value(from_investing, years, INVEST_RATE)
    )

    months = max(int(round(years * 12)), 1)

    return {
        "target": target,
        "already_saved": already_saved,
        "years": years,
        "months": months,

        "required_monthly": needed,
        "goal_monthly": goal_monthly,
        "goal_savings": from_savings,
        "goal_investing": from_investing,

        "remaining_savings": main_savings - from_savings,
        "remaining_investing": main_investing - from_investing,

        "feasible": feasible,
        "monthly_shortfall": max(needed - goal_monthly, 0),

        "projected_value": projected,
        "projected_gap": max(target - projected, 0),
        "contributed_only": already_saved + goal_monthly * months,

        "cash_share": share,
        "note": (
            f"With {years:g} years to go, {share * 100:.0f}% of the goal"
            " contribution is held as cash. Money you need on a fixed date"
            " is usually not left exposed to the market."
        ),
        "disclaimer": DISCLAIMER,
    }


def time_to_target(target, monthly, already_saved=0.0, rate=0.0):
    """How long the goal takes at a given contribution. Months, or None."""
    if monthly <= 0:
        return None

    remaining = max(target - already_saved, 0)

    if rate == 0:
        return int(round(remaining / monthly))

    months = 0
    balance = already_saved
    step = rate / 12

    while balance < target and months < 1200:
        balance = balance * (1 + step) + monthly
        months += 1

    return months if balance >= target else None


def affordability_note(goal, capacity_data):
    """
    A plain sentence about whether this goal fits the person's actual
    cashflow, or None when we lack the income data to say.
    """
    spare = capacity_data.get("monthly_spare")

    if spare is None:
        return None

    if goal["goal_monthly"] <= spare:
        return (
            "This fits inside what your statement shows as spare each month."
        )

    return (
        "This goal needs more each month than your statement shows as spare."
        " Either the timeline stretches, the target comes down, or something"
        " in the spending has to give."
    )
