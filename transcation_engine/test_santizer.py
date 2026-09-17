from src.sanitizer import sanitize_for_ai


tests = [
    "DOORDASH*DASHPASS CARD 92837465 REF AB882739",
    "TRANSFER TO JOHN SMITH ACCOUNT 9283746251",
    "AMZN MKTP US 839201 CARD 48392017",
    "STARBUCKS 615-555-1234 REF 928374",
    "PAYMENT test@example.com",
]


for transaction in tests:

    print()
    print("ORIGINAL:")
    print(transaction)

    print("SAFE:")
    print(
        sanitize_for_ai(
            transaction
        )
    )