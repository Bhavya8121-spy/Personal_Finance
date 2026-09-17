"""
The funny bit.

Rules this module enforces, because a joke about money lands very badly
on the wrong person:

  1. Only discretionary spending gets a joke. Rent, medical, groceries,
     childcare, debt and transfers are never the punchline.
  2. Nothing fires below a floor. Twelve dollars of coffee is not a bit.
  3. If the statement shows someone underwater with almost no
     discretionary spend, the tone switches to plain and supportive.
     There is no version of this app that roasts a person who is broke.
  4. The spending is the target, never the person.

generate() returns a list of dicts so the interface controls presentation:
    {"kind": "joke"|"note", "category": str, "amount": float, "text": str}
"""

import hashlib


# ----------------------------------------------------------------------
# Tone gate
# ----------------------------------------------------------------------

def should_joke(summary):
    """Decide whether humour is appropriate for this statement at all."""

    # No income visible means we cannot judge whether spending was a choice.
    if summary["money_in"] <= 0:
        return summary["discretionary"] >= 150

    # Spending more than you earned, with little discretionary spend, means
    # the money went to bills. Nothing funny there.
    if summary["net"] < 0 and summary["discretionary"] < summary["essentials"] * 0.35:
        return False

    return summary["discretionary"] >= 100


def _pick(options, seed):
    """Stable choice: the same statement always gets the same line."""
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return options[int(digest, 16) % len(options)]


# ----------------------------------------------------------------------
# Lines, keyed by what the category sounds like
# ----------------------------------------------------------------------

LINES = {
    "food": [
        "{amount} on eating out across {count} orders. Your kitchen is doing"
        " storage-unit work at this point.",
        "{amount} on takeout. The delivery app knows your building better"
        " than your landlord does.",
        "{count} food orders this period. Somewhere a stove is filing a"
        " missing person report.",
    ],
    "coffee": [
        "{count} coffee runs, {amount} total. That is not a habit, that is a"
        " subscription with extra steps.",
        "{amount} on coffee. The barista has earned the right to ask how"
        " you're doing and mean it.",
    ],
    "shopping": [
        "{amount} on shopping across {count} purchases. The cart did not"
        " abandon itself.",
        "{amount} of retail. Past you was optimistic about closet space.",
    ],
    "subscriptions": [
        "{amount} on subscriptions. Some of these are charging you rent for"
        " an app you last opened in spring.",
        "{count} recurring charges. That is a full roster and you are not"
        " starting most of them.",
    ],
    "entertainment": [
        "{amount} on going out. Memories: priceless. Statement: {amount}.",
        "{amount} on entertainment. Worth it, probably, mostly.",
    ],
    "transport": [
        "{amount} on rides across {count} trips. The car you do not own is"
        " getting expensive.",
        "{count} rides. Walking is right there, being free.",
    ],
    "generic": [
        "{amount} on {label} across {count} transactions. Small numbers,"
        " committed effort.",
        "{label} took {amount} this period. Consistency is a skill.",
    ],
}

CATEGORY_HINTS = (
    ("coffee", ("coffee", "cafe", "starbucks")),
    ("food", ("food", "dining", "restaurant", "takeout", "delivery", "eat")),
    ("subscriptions", ("subscription", "streaming", "membership")),
    ("shopping", ("shopping", "retail", "clothes", "apparel", "amazon", "merch")),
    ("entertainment", ("entertainment", "bar", "night", "game", "event")),
    ("transport", ("ride", "uber", "lyft", "taxi", "transport", "travel")),
)


def _style_for(label):
    text = (label or "").lower()

    for style, hints in CATEGORY_HINTS:
        if any(hint in text for hint in hints):
            return style

    return "generic"


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def generate(summary, leaks=None, currency="$", limit=3, floor=75.0):
    """Build the commentary block for one statement."""

    if not should_joke(summary):
        return [{
            "kind": "note",
            "category": None,
            "amount": summary["money_out"],
            "text": (
                "Most of this statement went to essentials. There is no"
                " spending habit to cut here, so the numbers above are the"
                " whole story."
            ),
        }]

    frame = summary["frame"]

    discretionary = (
        frame[(frame["Spent"] > 0) & (frame["Bucket"] == "discretionary")]
        .groupby("Category")
        .agg(spent=("Spent", "sum"), count=("Description", "count"))
        .sort_values("spent", ascending=False)
    )

    output = []
    seed_base = f"{summary['start']}-{summary['money_out']:.0f}"

    for label, row in discretionary.head(limit).iterrows():

        if row.spent < floor:
            continue

        style = _style_for(label)
        template = _pick(LINES[style], f"{seed_base}-{label}")

        output.append({
            "kind": "joke",
            "category": label,
            "amount": float(row.spent),
            "text": template.format(
                amount=_fmt(row.spent, currency),
                count=int(row["count"]),
                label=str(label).lower(),
            ),
        })

    # One line about the worst repeat habit, if habits.py found one
    if leaks:
        worst = leaks[0]

        if worst["annual_cost"] >= 240:
            repeat = (
                f" You have done this for {worst['months_seen']} months running."
                if worst.get("is_repeat") else ""
            )

            output.append({
                "kind": "note",
                "category": worst.get("category"),
                "amount": worst["annual_cost"],
                "text": (
                    f"{worst['payee']} took {_fmt(worst['total'], currency)} over"
                    f" {worst['visits']} visits. Keep that pace and it is"
                    f" {_fmt(worst['annual_cost'], currency)} a year.{repeat}"
                ),
            })

    return output


def _fmt(value, currency="$"):
    """Rounded amount with the statement's symbol."""
    symbol = "" if currency in (None, "No symbol") else currency
    return f"{symbol}{float(value):,.0f}"
