from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:

    raw_description: str

    amount: float

    transaction_type: Optional[str] = None

    merchant: Optional[str] = None

    category: Optional[str] = None

    subcategory: Optional[str] = None

    confidence: float = 0.0