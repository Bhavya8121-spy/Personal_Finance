from rapidfuzz import fuzz

from src.database import (
    get_all_merchant_aliases
)


# ==========================================================
# MATCHING CONFIGURATION
# ==========================================================

HIGH_CONFIDENCE_THRESHOLD = 0.90

REVIEW_THRESHOLD = 0.75


# ==========================================================
# UNKNOWN RESULT
# ==========================================================

def unknown_result():

    return {
        "merchant_id": None,
        "merchant": None,

        "default_category": None,
        "default_subcategory": None,

        "merchant_confidence": 0.0,
        "category_confidence": 0.0,

        "matched_alias": None,
        "match_method": None,

        "status": "unknown"
    }


# ==========================================================
# MERCHANT RESOLVER
# ==========================================================

def resolve_merchant(description):

    # ------------------------------------------------------
    # Normalize incoming text
    # ------------------------------------------------------

    if description is None:
        return unknown_result()

    description = (
        str(description)
        .upper()
        .strip()
    )

    if not description:
        return unknown_result()

    # ------------------------------------------------------
    # Load merchant knowledge
    # ------------------------------------------------------

    aliases = get_all_merchant_aliases()

    if not aliases:
        return unknown_result()

    # ======================================================
    # STEP 1 — EXACT ALIAS MATCHING
    # ======================================================

    exact_matches = []

    for row in aliases:

        merchant_id = row[0]

        name = row[1]

        default_category = row[2]

        default_subcategory = row[3]

        category_confidence = row[4]

        alias = row[5]

        # --------------------------------------------------
        # Safety
        # --------------------------------------------------

        if not alias:
            continue

        alias = alias.upper().strip()

        # --------------------------------------------------
        # Exact substring match
        # --------------------------------------------------

        if alias in description:

            exact_matches.append({

                "merchant_id":
                    merchant_id,

                "merchant":
                    name,

                "default_category":
                    default_category,

                "default_subcategory":
                    default_subcategory,

                "merchant_confidence":
                    1.0,

                "category_confidence":
                    category_confidence or 0.0,

                "matched_alias":
                    alias,

                "match_method":
                    "exact",

                "status":
                    "high_confidence"
            })

    # ------------------------------------------------------
    # Multiple aliases may match.
    #
    # Example:
    #
    # AMZN
    # AMZN MKTP
    #
    # Description:
    #
    # AMZN MKTP US 839201
    #
    # We want AMZN MKTP because it is more specific.
    # ------------------------------------------------------

    if exact_matches:

        best_exact_match = max(
            exact_matches,
            key=lambda match:
                len(match["matched_alias"])
        )

        return best_exact_match

    # ======================================================
    # STEP 2 — FUZZY MATCHING
    # ======================================================

    best_match = None

    best_score = 0.0

    for row in aliases:

        merchant_id = row[0]

        name = row[1]

        default_category = row[2]

        default_subcategory = row[3]

        category_confidence = row[4]

        alias = row[5]

        if not alias:
            continue

        alias = alias.upper().strip()

        # --------------------------------------------------
        # Compare alias with transaction description
        # --------------------------------------------------

        score = fuzz.partial_ratio(
            alias,
            description
        )

        confidence = (
            score / 100
        )

        # --------------------------------------------------
        # Keep best candidate
        # --------------------------------------------------

        if confidence > best_score:

            best_score = confidence

            best_match = {

                "merchant_id":
                    merchant_id,

                "merchant":
                    name,

                "default_category":
                    default_category,

                "default_subcategory":
                    default_subcategory,

                "merchant_confidence":
                    confidence,

                "category_confidence":
                    category_confidence or 0.0,

                "matched_alias":
                    alias,

                "match_method":
                    "fuzzy",

                "status":
                    None
            }

    # ======================================================
    # STEP 3 — CONFIDENCE DECISION
    # ======================================================

    if best_match is None:

        return unknown_result()

    merchant_confidence = (
        best_match[
            "merchant_confidence"
        ]
    )

    # ------------------------------------------------------
    # High confidence
    # ------------------------------------------------------

    if (
        merchant_confidence
        >= HIGH_CONFIDENCE_THRESHOLD
    ):

        best_match["status"] = (
            "high_confidence"
        )

        return best_match

    # ------------------------------------------------------
    # Possible merchant but uncertain
    # ------------------------------------------------------

    if (
        merchant_confidence
        >= REVIEW_THRESHOLD
    ):

        best_match["status"] = (
            "needs_review"
        )

        return best_match

    # ------------------------------------------------------
    # Not good enough
    # ------------------------------------------------------

    return unknown_result()