from src.parser import normalize_description

from src.merchant_resolver import (
    resolve_merchant
)

from src.sanitizer import (
    sanitize_for_ai
)

from src.type_detector import (
    detect_transaction_type,
    is_non_merchant_transaction
)

from src.keyword_classifier import (
    classify_by_keyword
)

from src.database import (
    add_merchant
)

from src.intelligence import (
    classify_unknown_transaction,
    validate_classification,
    IntelligenceUnavailableError
)


# ==========================================================
# CONFIGURATION
# ==========================================================

MERCHANT_LEARNING_THRESHOLD = 0.90

CATEGORY_TRUST_THRESHOLD = 0.85

CATEGORY_REVIEW_THRESHOLD = 0.65


# ==========================================================
# BANKING OPERATION CLASSIFIER
# ==========================================================

def classify_banking_operation(
    transaction_type
):

    mappings = {

        "ATM": (
            "Cash",
            "ATM Withdrawal"
        ),

        "Interest": (
            "Income",
            "Interest Income"
        ),

        "Commission": (
            "Financial",
            "Bank Fee"
        ),

        "Reversal": (
            "Other",
            "Miscellaneous"
        ),

        "Cheque": (
            "Transfer",
            "Bank Transfer"
        ),

        "NEFT": (
            "Transfer",
            "Bank Transfer"
        ),

        "RTGS": (
            "Transfer",
            "Bank Transfer"
        ),

        "IMPS": (
            "Transfer",
            "Bank Transfer"
        ),

        "Transfer": (
            "Transfer",
            "Bank Transfer"
        ),
    }

    result = mappings.get(
        transaction_type
    )

    if not result:
        return None

    return {
        "category": result[0],
        "subcategory": result[1]
    }


# ==========================================================
# ANALYZE TRANSACTION
# ==========================================================

def analyze_transaction(
    raw_description
):

    # ======================================================
    # 1. NORMALIZE
    # ======================================================

    normalized = normalize_description(
        raw_description
    )


    # ======================================================
    # 2. TRANSACTION TYPE
    # ======================================================

    transaction_type = (
        detect_transaction_type(
            normalized
        )
    )


    # ======================================================
    # 3. BANKING OPERATIONS
    #
    # No merchant or Gemini needed.
    # ======================================================

    if is_non_merchant_transaction(
        transaction_type
    ):

        banking = (
            classify_banking_operation(
                transaction_type
            )
        )

        return {
            "raw_description":
                raw_description,

            "normalized_description":
                normalized,

            "transaction_type":
                transaction_type,

            "merchant":
                None,

            "merchant_confidence":
                1.0,

            "category":
                banking["category"],

            "subcategory":
                banking["subcategory"],

            "category_confidence":
                1.0,

            "source":
                "local_rule",

            "matched_keyword":
                None,

            "review_required":
                False,

            "review_reason":
                None,
        }


    # ======================================================
    # 4. MERCHANT DATABASE / FUZZY RESOLVER
    # ======================================================

    merchant_result = (
        resolve_merchant(
            normalized
        )
    )


    if (
        merchant_result["status"]
        == "high_confidence"
    ):

        category_confidence = (
            merchant_result.get(
                "category_confidence"
            )
            or 0.0
        )

        if (
            category_confidence
            >= CATEGORY_TRUST_THRESHOLD
        ):

            return {
                "raw_description":
                    raw_description,

                "normalized_description":
                    normalized,

                "transaction_type":
                    transaction_type,

                "merchant":
                    merchant_result[
                        "merchant"
                    ],

                "merchant_confidence":
                    merchant_result[
                        "merchant_confidence"
                    ],

                "category":
                    merchant_result[
                        "default_category"
                    ],

                "subcategory":
                    merchant_result[
                        "default_subcategory"
                    ],

                "category_confidence":
                    category_confidence,

                "source":
                    "merchant_database",

                "matched_keyword":
                    None,

                "review_required":
                    False,

                "review_reason":
                    None,
            }


    # ======================================================
    # 5. KEYWORD INTELLIGENCE
    #
    # Local and free.
    # ======================================================

    keyword_result = (
        classify_by_keyword(
            normalized
        )
    )


    if keyword_result:

        # If we already know the merchant identity,
        # preserve it.

        merchant = None
        merchant_confidence = 0.0

        if (
            merchant_result["status"]
            in {
                "high_confidence",
                "needs_review"
            }
        ):

            merchant = (
                merchant_result[
                    "merchant"
                ]
            )

            merchant_confidence = (
                merchant_result[
                    "merchant_confidence"
                ]
            )

        return {
            "raw_description":
                raw_description,

            "normalized_description":
                normalized,

            "transaction_type":
                transaction_type,

            "merchant":
                merchant,

            "merchant_confidence":
                merchant_confidence,

            "category":
                keyword_result[
                    "category"
                ],

            "subcategory":
                keyword_result[
                    "subcategory"
                ],

            "category_confidence":
                keyword_result[
                    "confidence"
                ],

            "source":
                keyword_result[
                    "source"
                ],

            "matched_keyword":
                keyword_result[
                    "keyword"
                ],

            "review_required":
                False,

            "review_reason":
                None,
        }


    # ======================================================
    # 6. SANITIZE BEFORE EXTERNAL AI
    # ======================================================

    safe_description = (
        sanitize_for_ai(
            normalized
        )
    )


    if not safe_description:

        return {
            "raw_description":
                raw_description,

            "normalized_description":
                normalized,

            "transaction_type":
                transaction_type,

            "merchant":
                None,

            "merchant_confidence":
                0.0,

            "category":
                "Other",

            "subcategory":
                "Unknown",

            "category_confidence":
                0.0,

            "source":
                "insufficient_safe_data",

            "matched_keyword":
                None,

            "review_required":
                True,

            "review_reason":
                "insufficient_safe_data",
        }


    # ======================================================
    # 7. GEMINI — LAST RESORT
    # ======================================================

    try:

        intelligence_result = (
            classify_unknown_transaction(
                safe_description
            )
        )

    except IntelligenceUnavailableError:

        # Preserve merchant identity if fuzzy/database
        # resolution already found one.

        if (
            merchant_result["status"]
            in {
                "high_confidence",
                "needs_review"
            }
        ):

            return {
                "raw_description":
                    raw_description,

                "normalized_description":
                    normalized,

                "transaction_type":
                    transaction_type,

                "merchant":
                    merchant_result[
                        "merchant"
                    ],

                "merchant_confidence":
                    merchant_result[
                        "merchant_confidence"
                    ],

                "category":
                    merchant_result.get(
                        "default_category"
                    )
                    or "Other",

                "subcategory":
                    merchant_result.get(
                        "default_subcategory"
                    )
                    or "Unknown",

                "category_confidence":
                    merchant_result.get(
                        "category_confidence"
                    )
                    or 0.0,

                "source":
                    "merchant_known_ai_unavailable",

                "matched_keyword":
                    None,

                "review_required":
                    True,

                "review_reason":
                    "category_needs_review",
            }

        return {
            "raw_description":
                raw_description,

            "normalized_description":
                normalized,

            "transaction_type":
                transaction_type,

            "merchant":
                None,

            "merchant_confidence":
                0.0,

            "category":
                "Other",

            "subcategory":
                "Unknown",

            "category_confidence":
                0.0,

            "source":
                "ai_unavailable",

            "matched_keyword":
                None,

            "review_required":
                True,

            "review_reason":
                "user_classification_needed",
        }


    # ======================================================
    # 8. VALIDATE AI
    # ======================================================

    if not validate_classification(
        intelligence_result
    ):

        return {
            "raw_description":
                raw_description,

            "normalized_description":
                normalized,

            "transaction_type":
                transaction_type,

            "merchant":
                None,

            "merchant_confidence":
                0.0,

            "category":
                "Other",

            "subcategory":
                "Unknown",

            "category_confidence":
                0.0,

            "source":
                "failed_validation",

            "matched_keyword":
                None,

            "review_required":
                True,

            "review_reason":
                "user_classification_needed",
        }


    # ======================================================
    # 9. LEARN HIGH-CONFIDENCE MERCHANT
    # ======================================================

    if (
        intelligence_result
        .is_merchant_transaction

        and intelligence_result.merchant

        and
        intelligence_result
        .merchant_confidence
        >= MERCHANT_LEARNING_THRESHOLD
    ):

        aliases = []

        if (
            intelligence_result
            .merchant_alias
        ):

            alias = sanitize_for_ai(
                intelligence_result
                .merchant_alias
            )

            if alias:

                aliases.append(
                    alias
                )

        canonical_alias = (
            sanitize_for_ai(
                intelligence_result
                .merchant
            )
        )

        if (
            canonical_alias
            and
            canonical_alias not in aliases
        ):

            aliases.append(
                canonical_alias
            )

        add_merchant(
            name=
                intelligence_result
                .merchant,

            default_category=
                intelligence_result
                .category,

            default_subcategory=
                intelligence_result
                .subcategory,

            category_confidence=
                intelligence_result
                .category_confidence,

            aliases=
                aliases
        )


    # ======================================================
    # 10. REVIEW DECISION
    # ======================================================

    review_required = False
    review_reason = None


    if (
        intelligence_result
        .is_merchant_transaction

        and
        intelligence_result
        .merchant_confidence
        < 0.75
    ):

        review_required = True

        review_reason = (
            "low_merchant_confidence"
        )


    elif (
        intelligence_result
        .category_confidence
        < CATEGORY_REVIEW_THRESHOLD
    ):

        review_required = True

        review_reason = (
            "low_category_confidence"
        )


    # ======================================================
    # 11. FINAL RESULT
    # ======================================================

    return {
        "raw_description":
            raw_description,

        "normalized_description":
            normalized,

        "transaction_type":
            transaction_type,

        "merchant":
            intelligence_result
            .merchant,

        "merchant_confidence":
            intelligence_result
            .merchant_confidence,

        "category":
            intelligence_result
            .category,

        "subcategory":
            intelligence_result
            .subcategory,

        "category_confidence":
            intelligence_result
            .category_confidence,

        "source":
            "intelligence",

        "matched_keyword":
            None,

        "review_required":
            review_required,

        "review_reason":
            review_reason,
    }