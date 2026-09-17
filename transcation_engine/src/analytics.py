"""
Summaries built from the classified transaction frame.

Everything here is plain pandas: no Streamlit, no Flask. Any interface
can import it. The input is always the DataFrame your engine produces,
with at minimum these columns:

    Date, Description, Amount, Merchant, Category, Subcategory

Amount is negative for money leaving the account.
"""

import pandas as pd


# ----------------------------------------------------------------------
# Category buckets
#
# Your taxonomy may change, so we classify by the *name* of the category
# rather than hardcoding a list. This keeps analytics working even after
# you add new categories to CATEGORY_TAXONOMY.
# ----------------------------------------------------------------------

BUCKET_KEYWORDS = {
    "housing": ("rent", "mortgage", "housing", "lease", "hoa", "property"),
    "essential": (
        "grocer", "utility", "utilities", "electric", "water", "gas bill",
        "insurance", "medical", "health", "pharmacy", "doctor", "dental",
        "childcare", "daycare", "tuition", "education", "phone", "internet",
        "transit", "commute", "fuel", "petrol",
    ),
    "debt": ("loan", "debt", "credit card payment", "emi", "repayment", "student"),
    "investment": ("invest", "brokerage", "mutual fund", "stock", "crypto", "retirement"),
    "transfer": ("transfer", "atm", "cash", "withdrawal", "neft", "imps", "upi to", "zelle", "venmo"),
    "income": ("salary", "payroll", "income", "refund", "deposit", "interest earned"),
}

# Anything not matched above is treated as discretionary: the spending a
# person can actually change. Only discretionary spend gets commented on.


def bucket_of(category, subcategory=None):
    """Map a category name onto a spending bucket."""
    text = f"{category or ''} {subcategory or ''}".lower()

    for bucket, keywords in BUCKET_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return bucket

    return "discretionary"


# ----------------------------------------------------------------------
# Normalisation
# ----------------------------------------------------------------------

def normalize(results_df):
    """Return a copy with usable dtypes and derived columns."""
    df = results_df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)

    df["Spent"] = df["Amount"].where(df["Amount"] < 0, 0).abs()
    df["Received"] = df["Amount"].where(df["Amount"] > 0, 0)

    df["Bucket"] = [
        bucket_of(category, subcategory)
        for category, subcategory in zip(
            df.get("Category", ""), df.get("Subcategory", "")
        )
    ]

    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df.loc[df["Date"].isna(), "Month"] = "Unknown"

    # A clean label for grouping: merchant when we have one, else the raw text
    df["Payee"] = df.get("Merchant")
    df["Payee"] = df["Payee"].fillna(df["Description"]).astype(str).str.strip()

    return df


# ----------------------------------------------------------------------
# Headline summary
# ----------------------------------------------------------------------

def summarize(results_df):
    """One dict holding every number the interface needs up front."""
    df = normalize(results_df)

    dates = df["Date"].dropna()

    money_out = float(df["Spent"].sum())
    money_in = float(df["Received"].sum())

    spending = df[df["Spent"] > 0]

    by_bucket = (
        spending.groupby("Bucket")["Spent"].sum().sort_values(ascending=False)
    )

    by_category = (
        spending
        .groupby("Category")
        .agg(spent=("Spent", "sum"), count=("Description", "count"))
        .sort_values("spent", ascending=False)
    )

    months = sorted(m for m in df["Month"].unique() if m != "Unknown")

    day_count = None
    if not dates.empty:
        day_count = (dates.max() - dates.min()).days + 1

    # Savings rate only means something when we can see income
    savings_rate = None
    if money_in > 0:
        savings_rate = (money_in - money_out) / money_in

    discretionary = float(by_bucket.get("discretionary", 0.0))
    essentials = float(
        by_bucket.get("essential", 0.0) + by_bucket.get("housing", 0.0)
    )

    largest = None
    if not spending.empty:
        row = spending.loc[spending["Spent"].idxmax()]
        largest = {
            "payee": row["Payee"],
            "amount": float(row["Spent"]),
            "category": row.get("Category"),
            "date": row["Date"],
        }

    return {
        "transactions": int(len(df)),
        "debits": int((df["Spent"] > 0).sum()),
        "money_out": money_out,
        "money_in": money_in,
        "net": money_in - money_out,
        "savings_rate": savings_rate,
        "start": dates.min() if not dates.empty else None,
        "end": dates.max() if not dates.empty else None,
        "days": day_count,
        "months": months,
        "month_count": len(months),
        "by_category": by_category,
        "by_bucket": by_bucket,
        "discretionary": discretionary,
        "essentials": essentials,
        "largest": largest,
        "frame": df,
    }


# ----------------------------------------------------------------------
# Trends
# ----------------------------------------------------------------------

def monthly_trend(results_df):
    """Money in, money out and net per month. Empty frame if no dates."""
    df = normalize(results_df)
    dated = df[df["Month"] != "Unknown"]

    if dated.empty:
        return pd.DataFrame()

    trend = (
        dated
        .groupby("Month")
        .agg(**{
            "Money in": ("Received", "sum"),
            "Money out": ("Spent", "sum"),
        })
        .sort_index()
    )

    trend["Net"] = trend["Money in"] - trend["Money out"]
    return trend


def category_trend(results_df, top=5):
    """Spend per category per month, limited to the biggest categories."""
    df = normalize(results_df)
    dated = df[(df["Month"] != "Unknown") & (df["Spent"] > 0)]

    if dated.empty:
        return pd.DataFrame()

    biggest = (
        dated.groupby("Category")["Spent"].sum()
        .sort_values(ascending=False)
        .head(top)
        .index
    )

    pivot = (
        dated[dated["Category"].isin(biggest)]
        .pivot_table(
            index="Month", columns="Category", values="Spent",
            aggfunc="sum", fill_value=0,
        )
        .sort_index()
    )

    return pivot


# ----------------------------------------------------------------------
# Data sufficiency
#
# Your brief says: only draw a graph if there is enough data behind it.
# These are the gates the interface should check before charting.
# ----------------------------------------------------------------------

def has_dates(summary):
    return summary["start"] is not None


def enough_for_trend(summary):
    """A line over time needs at least two months."""
    return summary["month_count"] >= 2


def enough_for_breakdown(summary):
    """A category split needs at least three categories and some spend."""
    return len(summary["by_category"]) >= 3 and summary["money_out"] > 0


def enough_for_income_view(summary):
    """Income comparison needs credits to actually exist."""
    return summary["money_in"] > 0
