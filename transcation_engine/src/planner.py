"""
Savings capacity and general investing education.

Read this before you extend it.

This module does not give financial advice and must not be turned into
something that does. It does three things:

  1. Arithmetic on the user's own numbers (what is left over, how long an
     emergency fund would take).
  2. Widely published benchmarks, labelled as benchmarks.
  3. Historical return ranges for broad asset classes, labelled as
     history rather than prediction, always shown with the downside.

It never names a security, fund, ticker or platform, and it never tells a
person what to do. Every returned payload carries DISCLAIMER; show it.
"""

DISCLAIMER = (
    "This is general education, not financial advice, and it is based only"
    " on the statement you uploaded. Figures are historical ranges, not"
    " predictions. Markets fall as well as rise. Talk to a licensed adviser"
    " before acting on any of it."
)


# ----------------------------------------------------------------------
# Capacity: what is actually spare each month
# ----------------------------------------------------------------------

def capacity(summary):
    """
    What the statement says about monthly room to save.

    Returns None for fields we cannot honestly compute rather than
    guessing, so the interface can hide them.
    """
    months = max(summary["month_count"], 1)

    income = summary["money_in"] / months if summary["money_in"] else None
    outgoings = summary["money_out"] / months
    essentials = summary["essentials"] / months
    discretionary = summary["discretionary"] / months

    spare = (income - outgoings) if income else None

    return {
        "months_observed": summary["month_count"],
        "monthly_income": income,
        "monthly_outgoings": outgoings,
        "monthly_essentials": essentials,
        "monthly_discretionary": discretionary,
        "monthly_spare": spare,
        "savings_rate": summary["savings_rate"],
        "confidence": "low" if summary["month_count"] < 2 else "fair",
        "disclaimer": DISCLAIMER,
    }


# ----------------------------------------------------------------------
# Emergency fund: the step that comes before investing
# ----------------------------------------------------------------------

def emergency_fund(summary, months_of_cover=3):
    """
    A cash buffer sized against essential spending, not total spending.
    Commonly cited range is three to six months.
    """
    months = max(summary["month_count"], 1)
    essentials_per_month = summary["essentials"] / months

    if essentials_per_month <= 0:
        return None

    return {
        "monthly_essentials": essentials_per_month,
        "target_low": essentials_per_month * 3,
        "target_high": essentials_per_month * 6,
        "target": essentials_per_month * months_of_cover,
        "note": (
            "A cash buffer usually comes before investing, because selling"
            " investments during an emergency means selling at whatever"
            " price the market happens to offer that week."
        ),
        "disclaimer": DISCLAIMER,
    }


# ----------------------------------------------------------------------
# Benchmarks, clearly labelled as such
# ----------------------------------------------------------------------

BENCHMARKS = [
    {
        "name": "50 / 30 / 20",
        "detail": "Half to needs, 30% to wants, 20% to saving and debt.",
        "split": {"needs": 0.50, "wants": 0.30, "saving": 0.20},
    },
    {
        "name": "Pay yourself first",
        "detail": "Move a fixed amount to savings on payday, spend the rest.",
        "split": None,
    },
]


def benchmark_view(capacity_data):
    """Compare the user's actual split against a published rule of thumb."""
    income = capacity_data["monthly_income"]

    if not income:
        return None

    actual = {
        "needs": capacity_data["monthly_essentials"] / income,
        "wants": capacity_data["monthly_discretionary"] / income,
        "saving": max((capacity_data["monthly_spare"] or 0) / income, 0),
    }

    target = BENCHMARKS[0]["split"]

    return {
        "benchmark": BENCHMARKS[0]["name"],
        "detail": BENCHMARKS[0]["detail"],
        "actual": actual,
        "target": target,
        "gaps": {key: actual[key] - target[key] for key in target},
        "disclaimer": DISCLAIMER,
    }


# ----------------------------------------------------------------------
# Risk and horizon education
#
# Horizon, not personality, is the part that can be computed. How much
# volatility someone can stomach is theirs to decide.
# ----------------------------------------------------------------------

HORIZON_BANDS = [
    {
        "max_years": 3,
        "label": "Short horizon",
        "typical_mix": "Cash and cash-like accounts",
        "why": (
            "Money needed within about three years is usually kept in cash,"
            " because a market drop right before you spend it cannot be"
            " waited out."
        ),
        "historical_return": "roughly 0–5% a year, depending on rates",
        "worst_case": "Value is stable, but inflation erodes purchasing power",
    },
    {
        "max_years": 7,
        "label": "Medium horizon",
        "typical_mix": "A blend of bonds and diversified equity",
        "why": (
            "There is some time to recover from a fall, but not enough to"
            " ride out a long one."
        ),
        "historical_return": "historically around 4–7% a year before inflation",
        "worst_case": "Blended portfolios have fallen 10–20% in bad years",
    },
    {
        "max_years": 99,
        "label": "Long horizon",
        "typical_mix": "Mostly diversified equity, broadly held",
        "why": (
            "Over decades, time has historically been the thing that"
            " smoothed out bad years."
        ),
        "historical_return": (
            "broad equity markets have averaged roughly 6–10% a year before"
            " inflation over multi-decade periods"
        ),
        "worst_case": (
            "Equity markets have fallen 30–50% and taken years to recover."
            " That has happened repeatedly and will happen again."
        ),
    },
]


def horizon_guidance(years):
    """Education keyed to how far away the money is needed."""
    for band in HORIZON_BANDS:
        if years <= band["max_years"]:
            return {**band, "years": years, "disclaimer": DISCLAIMER}

    return {**HORIZON_BANDS[-1], "years": years, "disclaimer": DISCLAIMER}


# ----------------------------------------------------------------------
# Projection maths
# ----------------------------------------------------------------------

def future_value(monthly, years, annual_rate):
    """Future value of a monthly contribution. Plain compound arithmetic."""
    months = int(round(years * 12))

    if months <= 0:
        return 0.0

    if annual_rate == 0:
        return monthly * months

    rate = annual_rate / 12
    return monthly * (((1 + rate) ** months - 1) / rate)


def scenarios(monthly, years):
    """
    Three outcomes, always shown together. Showing only the middle one is
    how people end up surprised.
    """
    return {
        "contributed": monthly * years * 12,
        "poor": future_value(monthly, years, 0.02),
        "middling": future_value(monthly, years, 0.05),
        "strong": future_value(monthly, years, 0.08),
        "note": (
            "These are three fixed rates applied evenly. Real returns arrive"
            " unevenly, and a bad stretch early costs more than a bad stretch"
            " late."
        ),
        "disclaimer": DISCLAIMER,
    }
