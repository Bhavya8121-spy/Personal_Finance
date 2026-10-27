"""
Shared column-header recognition for CSV and PDF statements.

Banks name the same column a dozen different ways ("Withdrawals ($)",
"Transaction Details", "Paid out"...). Instead of exact-matching a short
list, every header cell is scored against phrase lists per role, the
longest phrase that appears wins, and a fuzzy fallback catches typos and
abbreviations.
"""

import re

try:
    from rapidfuzz import fuzz

    def _similar(a, b):
        return fuzz.ratio(a, b) / 100
except ImportError:  # keeps the module usable without RapidFuzz
    from difflib import SequenceMatcher

    def _similar(a, b):
        return SequenceMatcher(None, a, b).ratio()


ROLE_PHRASES = {
    "balance": [
        "balance", "running balance", "ending balance", "closing balance",
        "available balance", "bal",
    ],
    "debit": [
        "debit", "debits", "debit amount", "withdrawal", "withdrawals",
        "withdrawn", "money out", "paid out", "payments out", "charges",
        "withdrawals and other debits", "amount debited", "dr",
    ],
    "credit": [
        "credit", "credits", "credit amount", "deposit", "deposits",
        "money in", "paid in", "payments in", "amount credited", "cr",
        "deposits and other credits",
    ],
    "date": [
        "date", "transaction date", "trans date", "txn date", "posting date",
        "post date", "posted date", "posted", "value date", "date of transaction",
        "dt", "value dt", "txn dt", "trans dt", "posting dt",
    ],
    "description": [
        "description", "transaction description", "details",
        "transaction details", "memo", "narration", "particulars", "payee",
        "merchant", "name", "transaction", "descr", "desc", "reference",
        "narrative",
    ],
    "amount": [
        "amount", "transaction amount", "value", "amt", "sum",
    ],
}

# Tie-break when two roles match with the same phrase length
ROLE_ORDER = ["balance", "debit", "credit", "date", "description", "amount"]


def normalize_header(text):
    """'Withdrawals ($)\\n' -> 'withdrawals'. Strips symbols and extra space."""
    text = str(text or "").lower()
    text = re.sub(r"\([^)]*\)", " ", text)       # drop "($)", "(USD)"
    text = re.sub(r"[^a-z0-9 ]+", " ", text)     # drop punctuation / symbols
    return re.sub(r"\s+", " ", text).strip()


def classify_header(cell):
    """Return (role, confidence 0-1) for one header cell, or (None, 0)."""
    text = normalize_header(cell)
    if not text or len(text) > 60 or re.fullmatch(r"[\d ]+", text):
        return None, 0.0

    if text == "type" or text.endswith(" type"):  # "Transaction Type" is not the description
        return None, 0.0

    padded = f" {text} "
    best = None  # (phrase_length, -role_rank, role)
    for rank, role in enumerate(ROLE_ORDER):
        for phrase in ROLE_PHRASES[role]:
            if f" {phrase} " in padded:
                candidate = (len(phrase), -rank, role)
                if best is None or candidate > best:
                    best = candidate
    if best:
        exact = text in ROLE_PHRASES[best[2]]
        return best[2], 1.0 if exact else 0.9

    # Fuzzy fallback: typos ("Descripton") and truncations ("Trans. Descr")
    best_role, best_score = None, 0.0
    for role in ROLE_ORDER:
        for phrase in ROLE_PHRASES[role]:
            if len(phrase) < 4:
                continue
            score = _similar(text, phrase)
            for token in text.split():
                if len(token) >= 4 and phrase.startswith(token):
                    score = max(score, 0.86)
                score = max(score, _similar(token, phrase) if len(token) >= 5 else 0)
            if score > best_score:
                best_role, best_score = role, score
    if best_score >= 0.84:
        return best_role, round(best_score, 2)
    return None, 0.0


def header_row_score(cells):
    """
    How header-like is this row? Number of distinct roles recognised,
    or 0 if it is not plausible (needs a description or date column).
    """
    roles = {classify_header(c)[0] for c in cells if c and str(c).strip()}
    roles.discard(None)
    if not roles & {"description", "date"}:
        return 0
    return len(roles)


def detect_roles(columns):
    """
    Map role -> original column name for a list of column names.
    Each column is used at most once; highest confidence wins.
    """
    scored = []
    for column in columns:
        role, confidence = classify_header(column)
        if role:
            scored.append((confidence, role, column))

    def preference(item):
        # Between "Trans Date" and "Post Date", the transaction date is the one we want
        confidence, role, column = item
        prefers_transaction = bool(re.search(r"\b(trans|txn|transaction)\b", normalize_header(column)))
        return (-confidence, 0 if prefers_transaction else 1)

    found, used = {}, set()
    for confidence, role, column in sorted(scored, key=preference):
        if role not in found and column not in used:
            found[role] = column
            used.add(column)
    return found
