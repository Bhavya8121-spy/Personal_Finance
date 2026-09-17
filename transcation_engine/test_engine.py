from src.engine import analyze_transaction


transactions = [
    "COSTCO WHSE #0630",
    "PANERA BREAD #2048",
    "LOWES #1842",
    "DELTA AIR LINES",
    "MARRIOTT HOTEL",
    "CHEVRON 0094821",
    "TRADER JOE'S #721",
    "WHOLEFDS MKT 10234",
    "PETSMART #1482",
]


for transaction in transactions:

    print()
    print("=" * 70)
    print("INPUT:", transaction)

    try:

        result = analyze_transaction(
            transaction
        )

        for key, value in result.items():

            print(
                f"{key:25}: {value}"
            )

    except Exception as error:

        print()
        print("ERROR")
        print(type(error).__name__)
        print(str(error))