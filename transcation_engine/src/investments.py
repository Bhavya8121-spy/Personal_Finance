"""
Spotting investment activity in an ordinary bank statement.

Your brief: if we see something like Robinhood or a Chase deposit, offer
guidance instead of assuming. This module only detects and measures. It
never gives advice; planner.py handles that, and only when asked.
"""

from src.analytics import normalize


PLATFORMS = {
    "Robinhood": ("robinhood",),
    "Coinbase": ("coinbase",),
    "Fidelity": ("fidelity",),
    "Vanguard": ("vanguard",),
    "Charles Schwab": ("schwab",),
    "E*TRADE": ("etrade", "e*trade"),
    "Webull": ("webull",),
    "Wealthfront": ("wealthfront",),
    "Betterment": ("betterment",),
    "Acorns": ("acorns",),
    "Zerodha": ("zerodha",),
    "Groww": ("groww",),
    "Upstox": ("upstox",),
    "SIP / Mutual fund": ("sip ", "mutual fund", "amc ", "nav "),
    "Retirement account": ("401k", "401(k)", "ira ", "roth", "pension", "nps "),
    "Brokerage (generic)": ("brokerage", "securities", "invest"),
}


def detect(results_df):
    """
    Return what investment activity, if any, is visible.

    {
      "found": bool,
      "platforms": {"Robinhood": {...}},
      "contributed": float,   money that left the account toward investing
      "withdrawn": float,     money that came back from it
      "monthly_average": float | None,
    }
    """
    df = normalize(results_df)

    text = (
        df["Description"].astype(str) + " " + df["Payee"].astype(str)
    ).str.lower()

    platforms = {}
    matched_index = set()

    for name, keywords in PLATFORMS.items():

        mask = text.apply(lambda value: any(k in value for k in keywords))
        hits = df[mask]

        if hits.empty:
            continue

        matched_index.update(hits.index)

        platforms[name] = {
            "transactions": int(len(hits)),
            "contributed": float(hits["Spent"].sum()),
            "withdrawn": float(hits["Received"].sum()),
            "last_seen": hits["Date"].max(),
        }

    matched = df.loc[sorted(matched_index)] if matched_index else df.iloc[0:0]

    months = len({m for m in matched["Month"] if m != "Unknown"}) or 1

    contributed = float(matched["Spent"].sum())

    return {
        "found": bool(platforms),
        "platforms": platforms,
        "contributed": contributed,
        "withdrawn": float(matched["Received"].sum()),
        "monthly_average": contributed / months if contributed else None,
        "transactions": matched,
    }


def prompt_text(detection, currency="$"):
    """
    The line to show the user. Returns None when there is nothing to ask
    about, so the interface can skip the whole section.
    """
    if not detection["found"]:
        return None

    symbol = "" if currency in (None, "No symbol") else currency
    names = ", ".join(detection["platforms"].keys())

    return (
        f"We spotted {symbol}{detection['contributed']:,.0f} moving toward"
        f" {names}. Want to see how that compares with general savings"
        f" guidance?"
    )
