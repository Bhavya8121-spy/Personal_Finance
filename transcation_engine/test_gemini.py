from src.intelligence import (
    classify_unknown_transaction
)


result = classify_unknown_transaction(
    "CHIPOTLE 1837"
)


print()
print("Merchant:", result.merchant)
print("Alias:", result.merchant_alias)
print("Category:", result.category)
print("Subcategory:", result.subcategory)
print("Confidence:", result.confidence)
print("Merchant transaction:", result.is_merchant_transaction)
print("Reasoning:", result.reasoning)