from src.engine import analyze_transaction


def main():

    transactions = [
        "AMZN MKTP US*839201",
        "CHIPOTLE #1837",
        "STARBUCKS STORE 10482",
        "WALMART SUPERCENTER 5612",
        "MCDONALDS F38192",
        "SHELL OIL 574442",
        "BEST BUY 82736",
        "ATM CASH WITHDRAWAL",
        "NEFT TRANSFER TO JOHN"
    ]

    for transaction in transactions:

        result = analyze_transaction(transaction)

        print()
        print("=" * 60)

        print(
            f"Transaction         : "
            f"{result['raw_description']}"
        )

        print(
            f"Normalized          : "
            f"{result['normalized_description']}"
        )

        print(
            f"Merchant            : "
            f"{result['merchant']}"
        )

        print(
            f"Merchant Confidence : "
            f"{result['merchant_confidence']:.2f}"
        )

        print(
            f"Category            : "
            f"{result['category']}"
        )

        print(
            f"Subcategory         : "
            f"{result['subcategory']}"
        )

        print(
            f"Category Confidence : "
            f"{result['category_confidence']:.2f}"
        )

        print(
            f"Source              : "
            f"{result['source']}"
        )


if __name__ == "__main__":
    main()