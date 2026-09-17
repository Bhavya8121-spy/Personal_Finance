from src.merchant_bootstrap import (
    bootstrap_merchants,
    SOURCE_NAME,
    SOURCE_URL
)


def main():

    print()
    print("=" * 60)

    print(
        "Building merchant knowledge database"
    )

    print("=" * 60)
    print()

    result = bootstrap_merchants()

    print()
    print("=" * 60)

    print(
        f"Imported: "
        f"{result['imported']:,}"
    )

    print(
        f"Skipped:  "
        f"{result['skipped']:,}"
    )

    print()

    print(
        f"Source: {SOURCE_NAME}"
    )

    print(
        f"Source URL: {SOURCE_URL}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()