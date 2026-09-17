from src.database import (
    create_tables,
    add_merchant
)


create_tables()


add_merchant(
    name="Amazon",

    default_category="Shopping",
    default_subcategory="Online Marketplace",

    category_confidence=0.70,

    aliases=[
        "AMAZON",
        "AMZN",
        "AMZN MKTP"
    ]
)


add_merchant(
    name="DoorDash",

    default_category="Food & Dining",
    default_subcategory="Food Delivery",

    category_confidence=0.98,

    aliases=[
        "DOORDASH",
        "DOOR DASH",
        "DASHPASS"
    ]
)


add_merchant(
    name="Ross",

    default_category="Shopping",
    default_subcategory="Clothing",

    category_confidence=0.90,

    aliases=[
        "ROSS",
        "ROSS STORES",
        "ROSS DRESS FOR LESS"
    ]
)


add_merchant(
    name="Uber",

    default_category="Transportation",
    default_subcategory="Rideshare",

    category_confidence=0.95,

    aliases=[
        "UBER",
        "UBER TRIP"
    ]
)


print("Database seeded successfully!")