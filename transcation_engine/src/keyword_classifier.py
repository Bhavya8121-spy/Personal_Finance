from src.database import get_learned_keywords


# ==========================================================
# BUILT-IN HIGH-PRECISION KEYWORDS
# ==========================================================

KEYWORD_RULES = {

    "Food & Dining": {

        "Restaurant": [
            "PIZZA",
            "PIZZERIA",
            "RESTAURANT",
            "BISTRO",
            "DINER",
            "GRILL",
            "KITCHEN",
            "NOODLE",
            "SUSHI",
            "BBQ",
            "BARBECUE",
        ],

        "Fast Food": [
            "BURGER",
            "BURGERS",
            "TACO",
            "TACOS",
            "WINGS",
        ],

        "Coffee Shop": [
            "COFFEE",
            "CAFE",
            "ESPRESSO",
        ],

        "Bakery": [
            "BAKERY",
            "DONUT",
            "DONUTS",
        ],
    },

    "Groceries": {

        "Supermarket": [
            "SUPERMARKET",
        ],

        "Grocery Store": [
            "GROCERY",
        ],
    },

    "Travel": {

        "Airline": [
            "AIRLINES",
            "AIR LINES",
            "AIRWAYS",
        ],

        "Hotel": [
            "HOTEL",
            "MOTEL",
            "RESORT",
        ],
    },

    "Auto & Fuel": {

        "Gas Station": [
            "GAS STATION",
            "FUEL",
        ],

        "Auto Repair": [
            "AUTO REPAIR",
            "TIRE",
            "TIRES",
        ],
    },

    "Personal Care": {

        "Salon": [
            "SALON",
            "BARBER",
        ],

        "Spa": [
            "SPA",
        ],
    },
}


# ==========================================================
# BUILT-IN KEYWORD MATCHING
# ==========================================================

def classify_builtin_keyword(description):

    description = str(
        description
    ).upper()

    matches = []

    for category, subcategories in KEYWORD_RULES.items():

        for subcategory, keywords in subcategories.items():

            for keyword in keywords:

                if keyword in description:

                    matches.append({
                        "keyword": keyword,
                        "category": category,
                        "subcategory": subcategory,
                        "confidence": 0.90,
                        "source": "keyword_rule",
                    })

    if not matches:
        return None

    # Prefer longest / most specific match.
    return max(
        matches,
        key=lambda item: len(
            item["keyword"]
        )
    )


# ==========================================================
# LEARNED KEYWORD MATCHING
# ==========================================================

def classify_learned_keyword(description):

    description = str(
        description
    ).upper()

    learned_keywords = (
        get_learned_keywords()
    )

    matches = []

    for rule in learned_keywords:

        keyword = rule["keyword"]

        if keyword in description:

            matches.append(
                rule
            )

    if not matches:
        return None

    # Prefer higher confidence first, then longer keyword.
    return max(
        matches,
        key=lambda item: (
            item["confidence"],
            len(item["keyword"])
        )
    )


# ==========================================================
# COMBINED KEYWORD CLASSIFIER
# ==========================================================

def classify_by_keyword(description):

    # User/community-learned knowledge gets priority.
    learned = classify_learned_keyword(
        description
    )

    if learned:

        return {
            "keyword": learned["keyword"],
            "category": learned["category"],
            "subcategory": learned["subcategory"],
            "confidence": learned["confidence"],
            "source": "learned_keyword",
        }

    return classify_builtin_keyword(
        description
    )