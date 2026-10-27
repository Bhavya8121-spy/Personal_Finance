import pandas as pd

from src.header_detect import detect_roles


# ==========================================================
# COMMON BANK COLUMN NAMES
# ==========================================================

DATE_COLUMNS = [
    "date",
    "transaction date",
    "transaction_date",
    "posting date",
    "post date",
    "posted date"
]


DESCRIPTION_COLUMNS = [
    "description",
    "transaction description",
    "transaction_description",
    "details",
    "transaction details",
    "memo",
    "narration",
    "merchant",
    "name"
]


AMOUNT_COLUMNS = [
    "amount",
    "transaction amount",
    "transaction_amount",
    "value"
]


DEBIT_COLUMNS = [
    "debit",
    "withdrawal",
    "withdrawals",
    "debit amount",
    "money out"
]


CREDIT_COLUMNS = [
    "credit",
    "deposit",
    "deposits",
    "credit amount",
    "money in"
]


# ==========================================================
# NORMALIZE COLUMN NAME
# ==========================================================

def normalize_column_name(column):

    return (
        str(column)
        .strip()
        .lower()
    )


# ==========================================================
# FIND COLUMN
# ==========================================================

def find_column(columns, candidates):

    normalized_columns = {
        normalize_column_name(column): column
        for column in columns
    }

    for candidate in candidates:

        if candidate in normalized_columns:

            return normalized_columns[
                candidate
            ]

    return None


# ==========================================================
# DETECT COLUMNS
# ==========================================================

def detect_columns(df):

    columns = df.columns

    # 1. Exact matches against the known lists (fast, never wrong)
    detected = {

        "date":
            find_column(
                columns,
                DATE_COLUMNS
            ),

        "description":
            find_column(
                columns,
                DESCRIPTION_COLUMNS
            ),

        "amount":
            find_column(
                columns,
                AMOUNT_COLUMNS
            ),

        "debit":
            find_column(
                columns,
                DEBIT_COLUMNS
            ),

        "credit":
            find_column(
                columns,
                CREDIT_COLUMNS
            )
    }

    # 2. Anything still missing: phrase + fuzzy matching
    #    ("Withdrawals ($)", "Posted\nDate", "Descripton", ...)
    fuzzy = detect_roles(list(columns))
    taken = {column for column in detected.values() if column is not None}

    # "Trans Date" beats "Post Date" when a statement has both
    preferred_date = fuzzy.get("date")

    if (
        preferred_date is not None
        and detected["date"] != preferred_date
        and any(word in normalize_column_name(preferred_date) for word in ("trans", "txn"))
    ):

        detected["date"] = preferred_date

    taken = {column for column in detected.values() if column is not None}

    for role in ("date", "description", "amount", "debit", "credit"):

        if detected[role] is None:

            candidate = fuzzy.get(role)

            if candidate is not None and candidate not in taken:

                detected[role] = candidate
                taken.add(candidate)

    return detected


# ==========================================================
# CLEAN MONEY VALUE
# ==========================================================

def clean_amount(value):

    if pd.isna(value):
        return 0.0

    if isinstance(
        value,
        (int, float)
    ):
        return float(value)

    value = str(value)

    value = (
        value
        .replace("$", "")
        .replace("₹", "")
        .replace("€", "")
        .replace("£", "")
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )

    # "45.99-" (trailing minus) and "45.99 CR" / "45.99 DR" from PDFs
    upper = value.upper()

    if upper.endswith("CR"):
        value = value[:-2].strip()

    elif upper.endswith("DR"):
        value = "-" + value[:-2].strip().lstrip("-")

    elif value.endswith("-") and not value.startswith("-"):
        value = "-" + value[:-1]

    try:

        return float(value)

    except ValueError:

        return 0.0


# ==========================================================
# GET TRANSACTION AMOUNT
# ==========================================================

def get_amount(
    row,
    column_map
):

    # ------------------------------------------------------
    # Bank provides one Amount column
    # ------------------------------------------------------

    amount_column = (
        column_map["amount"]
    )

    if amount_column:

        return clean_amount(
            row[amount_column]
        )

    # ------------------------------------------------------
    # Bank provides Debit + Credit separately
    # ------------------------------------------------------

    debit_column = (
        column_map["debit"]
    )

    credit_column = (
        column_map["credit"]
    )

    debit = 0.0
    credit = 0.0

    if debit_column:

        debit = clean_amount(
            row[debit_column]
        )

    if credit_column:

        credit = clean_amount(
            row[credit_column]
        )

    # Debit = money leaving account
    if debit != 0:

        return -abs(debit)

    # Credit = money entering account
    if credit != 0:

        return abs(credit)

    return 0.0


# ==========================================================
# PREPARE STATEMENT
# ==========================================================

def prepare_statement(
    df,
    column_map,
    flip_sign=False
):

    description_column = (
        column_map["description"]
    )

    if not description_column:

        raise ValueError(
            "A transaction description "
            "column must be selected."
        )

    transactions = []

    for index, row in df.iterrows():

        description = row[
            description_column
        ]

        if pd.isna(description):
            continue

        description = str(
            description
        ).strip()

        if not description:
            continue

        amount = get_amount(
            row,
            column_map
        )

        # Credit card statements list purchases as positive numbers
        if flip_sign:

            amount = -amount

        transaction = {

            "row_index":
                index,

            "description":
                description,

            "amount":
                amount,

            "date":
                None
        }

        date_column = (
            column_map["date"]
        )

        if date_column:

            transaction["date"] = (
                row[date_column]
            )

        transactions.append(
            transaction
        )

    return transactions
