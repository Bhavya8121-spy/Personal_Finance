import csv
import io
import re
import urllib.request

from src.database import (
    create_tables,
    add_merchant
)


# ==========================================================
# PUBLIC MERCHANT DATASET
# ==========================================================

DATASET_URL = (
    "https://raw.githubusercontent.com/"
    "pointspick/mcc-database/main/"
    "data/merchant_mappings.csv"
)

SOURCE_NAME = "PointsPick MCC Database"

SOURCE_URL = (
    "https://github.com/"
    "pointspick/mcc-database"
)


# ==========================================================
# CATEGORY MAPPING
#
# Converts MCC data into OUR application taxonomy.
# ==========================================================

def map_mcc_to_taxonomy(
    mcc_code,
    mcc_description,
    source_category
):

    code = str(mcc_code).strip()

    description = (
        str(mcc_description)
        .upper()
        .strip()
    )

    source = (
        str(source_category)
        .upper()
        .strip()
    )

    # ======================================================
    # RESTAURANTS / FOOD
    # ======================================================

    if code == "5814":

        return (
            "Food & Dining",
            "Fast Food",
            0.95
        )

    if code == "5812":

        return (
            "Food & Dining",
            "Restaurant",
            0.95
        )

    if code == "5813":

        return (
            "Food & Dining",
            "Bar",
            0.90
        )

    if code == "5462":

        return (
            "Food & Dining",
            "Bakery",
            0.95
        )

    # ======================================================
    # GROCERIES
    # ======================================================

    if code == "5411":

        return (
            "Groceries",
            "Supermarket",
            0.90
        )

    if code in {
        "5422",
        "5441",
        "5451",
        "5499"
    }:

        return (
            "Groceries",
            "Grocery Store",
            0.85
        )

    # ======================================================
    # GAS / AUTO
    # ======================================================

    if code in {
        "5541",
        "5542"
    }:

        return (
            "Auto & Fuel",
            "Gas Station",
            0.95
        )

    if code in {
        "7531",
        "7534",
        "7535",
        "7538"
    }:

        return (
            "Auto & Fuel",
            "Auto Repair",
            0.90
        )

    if code in {
        "5531",
        "5532",
        "5533"
    }:

        return (
            "Auto & Fuel",
            "Auto Parts",
            0.90
        )

    # ======================================================
    # AIRLINES
    # ======================================================

    if (
        code == "4511"
        or
        "AIRLINE" in description
        or
        "AIR CARRIER" in description
    ):

        return (
            "Travel",
            "Airline",
            0.95
        )

    # ======================================================
    # HOTELS
    # ======================================================

    if (
        code == "7011"
        or
        "HOTEL" in description
        or
        "MOTEL" in description
        or
        "LODGING" in description
    ):

        return (
            "Travel",
            "Hotel",
            0.95
        )

    # ======================================================
    # CAR RENTAL
    # ======================================================

    if code in {
        "3351",
        "3352",
        "3353",
        "3354",
        "3355",
        "3357",
        "3359",
        "3360",
        "3361",
        "3362",
        "3364",
        "3366",
        "3368",
        "3370",
        "3374",
        "3376",
        "3380",
        "3381",
        "3385",
        "3387",
        "3388",
        "3389",
        "3390",
        "3391",
        "3393",
        "3394",
        "3395",
        "3396",
        "3398",
        "3400",
        "3405"
    }:

        return (
            "Travel",
            "Car Rental",
            0.95
        )

    # ======================================================
    # TRANSPORTATION
    # ======================================================

    if code == "4121":

        return (
            "Transportation",
            "Taxi",
            0.90
        )

    if code in {
        "4111",
        "4112"
    }:

        return (
            "Transportation",
            "Public Transit",
            0.90
        )

    if code == "7523":

        return (
            "Transportation",
            "Parking",
            0.95
        )

    if code == "4784":

        return (
            "Transportation",
            "Tolls",
            0.95
        )

    # ======================================================
    # PHARMACY / HEALTH
    # ======================================================

    if code == "5912":

        return (
            "Health",
            "Pharmacy",
            0.90
        )

    if code in {
        "8011",
        "8031",
        "8049"
    }:

        return (
            "Health",
            "Doctor",
            0.90
        )

    if code == "8062":

        return (
            "Health",
            "Hospital",
            0.95
        )

    if code == "8021":

        return (
            "Health",
            "Dental",
            0.95
        )

    if code in {
        "8042",
        "8043"
    }:

        return (
            "Health",
            "Vision",
            0.90
        )

    # ======================================================
    # CLOTHING
    # ======================================================

    if code in {
        "5611",
        "5621",
        "5631",
        "5641",
        "5651",
        "5655",
        "5661",
        "5681",
        "5691",
        "5699"
    }:

        return (
            "Shopping",
            "Clothing",
            0.90
        )

    # ======================================================
    # ELECTRONICS
    # ======================================================

    if code in {
        "5722",
        "5732",
        "5734"
    }:

        return (
            "Shopping",
            "Electronics",
            0.90
        )

    # ======================================================
    # HOME GOODS / HOME IMPROVEMENT
    # ======================================================

    if code in {
        "5200",
        "5211",
        "5231",
        "5251",
        "5261",
        "5712",
        "5713",
        "5714",
        "5718",
        "5719"
    }:

        return (
            "Shopping",
            "Home Goods",
            0.90
        )

    # ======================================================
    # DEPARTMENT STORES
    # ======================================================

    if code == "5311":

        return (
            "Shopping",
            "Department Store",
            0.85
        )

    # ======================================================
    # WAREHOUSE / WHOLESALE
    #
    # Costco-like merchants are multipurpose, so confidence
    # is intentionally lower.
    # ======================================================

    if code == "5300":

        return (
            "Shopping",
            "General Retail",
            0.70
        )

    # ======================================================
    # GENERAL / ONLINE RETAIL
    # ======================================================

    if code in {
        "5399",
        "5999"
    }:

        return (
            "Shopping",
            "General Retail",
            0.70
        )

    # ======================================================
    # ENTERTAINMENT
    # ======================================================

    if code == "7832":

        return (
            "Entertainment",
            "Movies",
            0.95
        )

    if code in {
        "7922",
        "7929"
    }:

        return (
            "Entertainment",
            "Events",
            0.90
        )

    if code in {
        "7994",
        "7996",
        "7998",
        "7999"
    }:

        return (
            "Entertainment",
            "Events",
            0.80
        )

    # ======================================================
    # BEAUTY
    # ======================================================

    if code == "7230":

        return (
            "Personal Care",
            "Salon",
            0.90
        )

    if code == "7298":

        return (
            "Personal Care",
            "Spa",
            0.90
        )

    if code == "5977":

        return (
            "Personal Care",
            "Beauty",
            0.90
        )

    # ======================================================
    # EDUCATION
    # ======================================================

    if code in {
        "8211",
        "8220",
        "8241",
        "8244",
        "8249"
    }:

        return (
            "Education",
            "Tuition",
            0.90
        )

    if code == "5942":

        return (
            "Education",
            "Books",
            0.85
        )

    # ======================================================
    # UTILITIES
    # ======================================================

    if code == "4814":

        return (
            "Bills & Utilities",
            "Phone",
            0.90
        )

    if code == "4816":

        return (
            "Bills & Utilities",
            "Internet",
            0.85
        )

    if code == "4900":

        return (
            "Bills & Utilities",
            "Electricity",
            0.75
        )

    # ======================================================
    # SOURCE CATEGORY FALLBACKS
    # ======================================================

    if "DINING" in source:

        return (
            "Food & Dining",
            "Restaurant",
            0.80
        )

    if (
        "GROCERY" in source
        or
        "GROCERIES" in source
    ):

        return (
            "Groceries",
            "Grocery Store",
            0.80
        )

    if (
        "TRAVEL" in source
        or
        "HOTEL" in source
    ):

        return (
            "Travel",
            "Travel Booking",
            0.70
        )

    if (
        "GAS" in source
        or
        "FUEL" in source
    ):

        return (
            "Auto & Fuel",
            "Gas Station",
            0.85
        )

    if (
        "RETAIL" in source
        or
        "SHOPPING" in source
    ):

        return (
            "Shopping",
            "General Retail",
            0.65
        )

    # ======================================================
    # UNKNOWN MCC
    # ======================================================

    return (
        "Other",
        "Miscellaneous",
        0.50
    )


# ==========================================================
# NORMALIZE ALIAS
# ==========================================================

def normalize_alias(value):

    value = str(value).upper()

    value = re.sub(
        r"[^A-Z0-9&' ]",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ==========================================================
# GENERATE USEFUL ALIASES
# ==========================================================

def build_aliases(
    merchant_name,
    slug=None
):

    aliases = set()

    canonical = normalize_alias(
        merchant_name
    )

    if canonical:

        aliases.add(
            canonical
        )

    if slug:

        slug_alias = (
            str(slug)
            .replace("-", " ")
            .replace("_", " ")
        )

        slug_alias = normalize_alias(
            slug_alias
        )

        if slug_alias:

            aliases.add(
                slug_alias
            )

    return sorted(
        aliases
    )


# ==========================================================
# DOWNLOAD DATASET
# ==========================================================

def download_dataset():

    request = urllib.request.Request(
        DATASET_URL,
        headers={
            "User-Agent":
                "TransactionIntelligence/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = response.read()

    return data.decode(
        "utf-8-sig"
    )


# ==========================================================
# IMPORT MERCHANT DATA
# ==========================================================

def bootstrap_merchants():

    create_tables()

    print(
        "Downloading merchant knowledge dataset..."
    )

    csv_text = download_dataset()

    reader = csv.DictReader(
        io.StringIO(
            csv_text
        )
    )

    imported = 0
    skipped = 0

    for row in reader:

        merchant_name = (
            row.get(
                "merchant_name",
                ""
            )
            .strip()
        )

        if not merchant_name:

            skipped += 1
            continue

        mcc_code = (
            row.get(
                "mcc_code",
                ""
            )
        )

        mcc_description = (
            row.get(
                "mcc_description",
                ""
            )
        )

        source_category = (
            row.get(
                "category",
                ""
            )
        )

        slug = row.get(
            "slug"
        )

        (
            category,
            subcategory,
            category_confidence
        ) = map_mcc_to_taxonomy(
            mcc_code,
            mcc_description,
            source_category
        )

        aliases = build_aliases(
            merchant_name,
            slug
        )

        try:

            add_merchant(
                name=merchant_name,

                default_category=
                    category,

                default_subcategory=
                    subcategory,

                category_confidence=
                    category_confidence,

                aliases=
                    aliases
            )

            imported += 1

        except Exception as error:

            skipped += 1

            print(
                f"Skipped {merchant_name}: "
                f"{type(error).__name__}"
            )

    return {
        "imported": imported,
        "skipped": skipped
    }