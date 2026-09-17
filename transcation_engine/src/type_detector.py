TRANSACTION_PATTERNS = {
    "ATM": [
        "ATM",
        "CASH WITHDRAWAL",
        "CASH WDL",
    ],

    "Interest": [
        "INTEREST CREDIT",
        "INTEREST PAYMENT",
        "INTEREST PAID",
    ],

    "Commission": [
        "BANK COMMISSION",
        "COMMISSION",
        "BANK FEE",
        "SERVICE FEE",
    ],

    "Reversal": [
        "REVERSAL",
        "REVERSED",
    ],

    "Cheque": [
        "CHEQUE",
        "CHECK DEPOSIT",
        "CHECK",
        "CHQ",
    ],

    "NEFT": [
        "NEFT",
    ],

    "RTGS": [
        "RTGS",
    ],

    "IMPS": [
        "IMPS",
    ],

    "Transfer": [
        "TRANSFER TO",
        "TRANSFER FROM",
        "BANK TRANSFER",
        "INTERNAL TRANSFER",
    ],
}


def detect_transaction_type(description):

    if not description:
        return "Unknown"

    description = str(description).upper()

    for transaction_type, patterns in TRANSACTION_PATTERNS.items():

        for pattern in patterns:

            if pattern in description:
                return transaction_type

    return "Purchase"


def is_non_merchant_transaction(transaction_type):

    return transaction_type in {
        "ATM",
        "Interest",
        "Commission",
        "Reversal",
        "Cheque",
        "NEFT",
        "RTGS",
        "IMPS",
        "Transfer",
    }