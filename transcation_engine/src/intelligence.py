import os

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, Field

from src.categories import (
    CATEGORY_TAXONOMY,
    is_valid_category,
    is_valid_subcategory
)


# ==========================================================
# ENVIRONMENT
# ==========================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY was not found. "
        "Make sure it exists in your .env file."
    )


# ==========================================================
# GEMINI CLIENT
# ==========================================================

client = genai.Client(
    api_key=api_key
)


# ==========================================================
# CUSTOM EXCEPTIONS
# ==========================================================

class IntelligenceUnavailableError(Exception):
    """
    Raised when Gemini is temporarily unavailable.
    """
    pass


# ==========================================================
# STRUCTURED CLASSIFICATION RESULT
# ==========================================================

class ClassificationResult(BaseModel):

    merchant: str | None = Field(
        description=(
            "Clean canonical merchant/business name. "
            "Use null when no merchant can be identified."
        )
    )

    merchant_alias: str | None = Field(
        description=(
            "Useful merchant text appearing in the "
            "transaction description."
        )
    )

    merchant_confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence that the merchant identity "
            "is correct."
        )
    )

    category: str = Field(
        description=(
            "Transaction category from the allowed taxonomy."
        )
    )

    subcategory: str = Field(
        description=(
            "Transaction subcategory from the allowed taxonomy."
        )
    )

    category_confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence that the category and subcategory "
            "correctly describe this transaction."
        )
    )

    is_merchant_transaction: bool = Field(
        description=(
            "True if an identifiable merchant/business "
            "is involved."
        )
    )

    reasoning: str = Field(
        description=(
            "Short explanation of the classification."
        )
    )


# ==========================================================
# TAXONOMY TEXT
# ==========================================================

def build_taxonomy_text():

    lines = []

    for category, subcategories in CATEGORY_TAXONOMY.items():

        lines.append(
            f"{category}: {', '.join(subcategories)}"
        )

    return "\n".join(lines)


# ==========================================================
# GEMINI CLASSIFIER
# ==========================================================

def classify_unknown_transaction(description):

    taxonomy = build_taxonomy_text()

    prompt = f"""
You are a financial transaction classification engine.

Analyze this normalized bank transaction:

TRANSACTION:
{description}


YOUR TASK

Determine:

1. Whether an identifiable merchant exists.
2. The canonical merchant name.
3. The merchant alias visible in the transaction.
4. Your confidence in the merchant identity.
5. The transaction category.
6. The transaction subcategory.
7. Your confidence in the category classification.


IMPORTANT DISTINCTION

Merchant identity and transaction category are different.

You may be highly confident about the merchant while being
less confident about what was purchased.

Example:

WALMART SUPERCENTER 1234

Merchant:
Walmart

Merchant confidence:
Very high

But Walmart sells groceries, clothing, electronics,
pharmacy products, automotive products, and many other
things.

Therefore category confidence should be lower unless the
transaction description contains evidence about what was
purchased.


MERCHANT RULES

- Do not invent merchants.

- If there is not enough evidence to identify a merchant,
  merchant must be null.

- Transaction mechanisms are NOT merchants.

Examples:

NEFT
RTGS
IMPS
ATM
DEBIT CARD
CHEQUE
TRANSFER

- merchant_alias should contain useful identifying merchant
  text.

- Remove store numbers, transaction IDs, reference numbers,
  dates, and similar noise from merchant_alias.


CATEGORY RULES

- category MUST come from the allowed taxonomy.

- subcategory MUST belong to the selected category.

- If category is uncertain, lower category_confidence.

- Do not use merchant_confidence as category_confidence.

- Multi-purpose merchants should generally have lower
  category confidence when the transaction description
  does not reveal what was purchased.

- Generic transfers, ATM withdrawals, interest payments,
  bank fees, and reversals are generally not merchant
  transactions.


ALLOWED TAXONOMY

{taxonomy}
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,

            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClassificationResult
            )
        )

    except (
        errors.ServerError,
        errors.ClientError
    ) as error:

        raise IntelligenceUnavailableError(
            "Gemini is unavailable or the API quota "
            "has been reached."
        ) from error

    result = ClassificationResult.model_validate_json(
        response.text
    )

    return result


# ==========================================================
# VALIDATION
# ==========================================================

def validate_classification(result):

    if not is_valid_category(
        result.category
    ):
        return False

    if not is_valid_subcategory(
        result.category,
        result.subcategory
    ):
        return False

    if not 0 <= result.merchant_confidence <= 1:
        return False

    if not 0 <= result.category_confidence <= 1:
        return False

    if (
        result.is_merchant_transaction
        and result.merchant is None
    ):
        return False

    return True