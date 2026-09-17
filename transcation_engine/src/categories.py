CATEGORY_TAXONOMY = {

    "Food & Dining": [
        "Restaurant",
        "Fast Food",
        "Coffee Shop",
        "Food Delivery",
        "Bar",
        "Bakery"
    ],

    "Groceries": [
        "Supermarket",
        "Grocery Store",
        "Convenience Store"
    ],

    "Shopping": [
        "Online Marketplace",
        "Clothing",
        "Electronics",
        "Department Store",
        "Home Goods",
        "General Retail"
    ],

    "Transportation": [
        "Rideshare",
        "Taxi",
        "Public Transit",
        "Parking",
        "Tolls"
    ],

    "Auto & Fuel": [
        "Gas Station",
        "Auto Repair",
        "Car Wash",
        "Auto Parts"
    ],

    "Bills & Utilities": [
        "Electricity",
        "Water",
        "Gas Utility",
        "Internet",
        "Phone",
        "Cable"
    ],

    "Entertainment": [
        "Streaming",
        "Movies",
        "Gaming",
        "Events",
        "Music"
    ],

    "Travel": [
        "Airline",
        "Hotel",
        "Car Rental",
        "Travel Booking"
    ],

    "Health": [
        "Pharmacy",
        "Doctor",
        "Hospital",
        "Dental",
        "Vision"
    ],

    "Personal Care": [
        "Salon",
        "Barber",
        "Spa",
        "Beauty"
    ],

    "Education": [
        "Tuition",
        "Books",
        "Courses",
        "School Supplies"
    ],

    "Financial": [
        "Bank Fee",
        "Interest",
        "Investment",
        "Insurance"
    ],

    "Income": [
        "Salary",
        "Refund",
        "Interest Income",
        "Other Income"
    ],

    "Transfer": [
        "Bank Transfer",
        "Peer-to-Peer Transfer",
        "Internal Transfer"
    ],

    "Cash": [
        "ATM Withdrawal",
        "Cash Deposit"
    ],

    "Other": [
        "Miscellaneous",
        "Unknown"
    ]
}
def is_valid_category(category):
    return category in CATEGORY_TAXONOMY
def is_valid_subcategory(category, subcategory):

    if category not in CATEGORY_TAXONOMY:
        return False

    return subcategory in CATEGORY_TAXONOMY[category]