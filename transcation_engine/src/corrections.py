import re
from src.sanitizer import sanitize_for_ai
from src.database import (
    save_merchant_correction,
    record_keyword_evidence,
    promote_keyword_if_ready
)


# ==========================================================
# WORDS WE NEVER WANT TO LEARN AS CATEGORY KEYWORDS
# ==========================================================

STOP_WORDS = {
    "THE",
    "AND",
    "FOR",
    "WITH",
    "STORE",
    "SHOP",
    "PAYMENT",
    "PURCHASE",
    "ONLINE",
    "CARD",
    "DEBIT",
    "CREDIT",
    "USA",
    "US",
}


# ==========================================================
# EXTRACT POSSIBLE KEYWORDS
# ==========================================================

def extract_candidate_keywords(
    description
):

    text = str(
        description
    ).upper()

    words = re.findall(
        r"[A-Z]{4,}",
        text
    )

    candidates = []

    for word in words:

        if word in STOP_WORDS:
            continue

        if word not in candidates:

            candidates.append(
                word
            )

    return candidates


# ==========================================================
# SAVE USER CORRECTION
# ==========================================================

def save_user_correction(
    description,
    merchant,
    category,
    subcategory
):

    # ------------------------------------------------------
    # Save merchant-specific knowledge immediately
    # ------------------------------------------------------

    if merchant:

        safe_alias = sanitize_for_ai(
            description
        )

        save_merchant_correction(
            merchant_name=merchant,
            alias=safe_alias,
            category=category,
            subcategory=subcategory
        )

    # ------------------------------------------------------
    # Gather possible reusable keyword evidence
    # ------------------------------------------------------

    candidates = (
        extract_candidate_keywords(
            description
        )
    )

    promoted = []

    for keyword in candidates:

        record_keyword_evidence(
            keyword=keyword,
            category=category,
            subcategory=subcategory
        )

        if promote_keyword_if_ready(
            keyword
        ):

            promoted.append(
                keyword
            )

    return {
        "keywords_considered":
            candidates,

        "keywords_promoted":
            promoted,
    }