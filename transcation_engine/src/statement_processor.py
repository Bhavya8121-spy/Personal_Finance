import pandas as pd


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

    return {

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
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )

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
    column_map
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

        transaction = {

            "row_index":
                index,

            "description":
                description,

            "amount":
                get_amount(
                    row,
                    column_map
                ),

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