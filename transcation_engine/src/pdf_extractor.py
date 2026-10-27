"""
Turn a bank / credit-card PDF statement into a pandas DataFrame the rest of
the app already understands (Date, Description, Amount[, Balance]).

Strategy, in order:
  1. Ruled tables   - pdfplumber table extraction, header row located by
                      scoring every early row (src/header_detect.py).
                      Pages without a header reuse the previous page's.
  2. Plain text     - many statements have no ruling lines. Each line that
                      starts with a date and ends with amounts is a
                      transaction; the sign comes from the running balance,
                      section headings (Deposits / Withdrawals), CR/DR marks.
  3. Headerless     - if a table has no recognisable header, columns are
                      inferred from what is in them (dates, numbers, text).

Nothing is sent anywhere: this runs entirely locally.
"""

import io
import re
from collections import Counter

import pandas as pd
import pdfplumber

from src.header_detect import classify_header, header_row_score


class PdfStatementError(Exception):
    """Raised with a message that is safe to show the user."""


# ----------------------------------------------------------------------
# Patterns
# ----------------------------------------------------------------------

MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"

DATE = (
    r"(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?"
    rf"|(?:{MONTHS})[a-z]*\.?\s+\d{{1,2}}(?:,?\s+\d{{4}})?"
    rf"|\d{{1,2}}[\s-](?:{MONTHS})[a-z]*\.?(?:[\s,-]+\d{{2,4}})?)"
)

# 1,234.56  (1,234.56)  -1,234.56  1,234.56-  $1,234.56  1,234.56 CR
AMOUNT = r"\(?-?[$₹€£¥]?\s?\d[\d,]*\.\d{2}\)?-?(?:\s?(?:CR|DR|Cr|Dr))?"

LINE_RE = re.compile(
    rf"^\s*(?P<date>{DATE})\s+(?:(?P<date2>{DATE})\s+)?"
    rf"(?P<desc>.*?)\s+(?P<amts>(?:{AMOUNT}\s*){{1,3}})$"
)
AMOUNT_RE = re.compile(AMOUNT)

SKIP_DESCRIPTIONS = (
    "opening balance", "beginning balance", "balance forward", "previous balance",
    "closing balance", "ending balance", "new balance", "total ", "balance brought",
    "balance carried",
)

CREDIT_WORDS = (
    "deposit", "payroll", "salary", "direct dep", "interest paid", "refund",
    "reversal", "cashback", "transfer from", "from savings", "payment received",
    "payment thank", "credit",
)

CARD_HINTS = (
    "minimum payment", "payment due", "credit limit", "available credit",
    "new balance", "previous balance", "annual percentage rate",
)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def _clean_cell(cell):
    return re.sub(r"\s+", " ", str(cell or "")).strip()


def _parse_amount(token):
    """'(1,234.56)' -> (1234.56, marker) where marker is 'neg', 'pos' or None."""
    raw = token.strip()
    marker = None
    upper = raw.upper()
    if upper.endswith("CR"):
        marker = "pos"
    elif upper.endswith("DR"):
        marker = "neg"
    if raw.startswith("(") or raw.startswith("-") or raw.rstrip("CRDRcrdr ").endswith("-") \
            or raw.endswith(")"):
        marker = "neg"
    number = re.sub(r"[^\d.]", "", raw.replace(",", ""))
    try:
        return float(number), marker
    except ValueError:
        return None, None


def _is_date(text):
    return bool(re.fullmatch(DATE, str(text).strip()))


def _number_or_none(text):
    """Signed number from a cell ('(5.00)' -> -5.0), or None if it isn't money."""
    if isinstance(text, (int, float)) and not pd.isna(text):
        return float(text)
    cell = str(text).strip()
    if not AMOUNT_RE.fullmatch(cell):
        return None
    value, marker = _parse_amount(cell)
    if value is None:
        return None
    return -value if marker == "neg" else value


def _statement_years(text):
    years = [int(y) for y in re.findall(r"\b(20\d{2}|19\d{2})\b", text)]
    if not years:
        return []
    common = [y for y, _ in Counter(years).most_common(3)]
    return sorted(set(common))


def _add_year(value, years):
    """
    '03/15' or 'Mar 15' -> a full date string using the statement's year(s).
    A Dec-Jan statement gives Dec the earlier year and Jan the later one.
    """
    text = str(value).strip()
    if not text:
        return None
    if re.search(r"\b\d{4}\b", text) or re.search(r"\d[/.-]\d{1,2}[/.-]\d{2}\b", text):
        return text  # already has a year
    if not years:
        return text
    month_match = re.match(r"(\d{1,2})[/.-]\d{1,2}", text)
    if month_match:
        month = int(month_match.group(1))
    else:
        found = re.search(MONTHS, text, re.I)
        names = MONTHS.split("|")
        month = (names.index(found.group(0).capitalize()) + 1) if found and found.group(0).capitalize() in names else 6
    if len(years) >= 2 and years[-1] - years[0] == 1:
        year = years[0] if month >= 7 else years[-1]
    else:
        year = years[-1]
    return f"{text}/{year}" if month_match else f"{text} {year}"


def _looks_like_card(text):
    lowered = text.lower()
    return sum(hint in lowered for hint in CARD_HINTS) >= 2


# ----------------------------------------------------------------------
# Sign handling
# ----------------------------------------------------------------------

def _section_from_heading(line, is_card):
    lowered = line.lower()
    debit_words = ("withdrawal", "debits", "checks", "purchases", "charges", "fees",
                   "subtractions", "cash advance", "debit card")
    credit_words = ("deposits", "credits", "additions", "refunds")
    if is_card:
        credit_words = credit_words + ("payments",)
    else:
        debit_words = debit_words + ("payments",)
    is_debit = any(word in lowered for word in debit_words)
    is_credit = any(word in lowered for word in credit_words)
    if is_debit and not is_credit:
        return "debit"
    if is_credit and not is_debit:
        return "credit"
    return None


def _decide_sign(amount, marker, balance, previous_balance, section, description, is_card):
    """Return +amount for money in, -amount for money out."""
    # 1. Running balance is the most reliable evidence
    if balance is not None and previous_balance is not None:
        delta = balance - previous_balance
        if abs(abs(delta) - amount) < 0.011 and delta != 0:
            return amount if delta > 0 else -amount

    # 2. Section headings ("Deposits and additions")
    if section == "credit":
        return amount
    if section == "debit":
        return -amount

    # 3. Explicit marks: (x), -x, x-, CR, DR
    if marker:
        money_in = (marker == "pos")
        if is_card and marker == "neg":
            money_in = True  # on a card statement a minus is a payment/credit
        return amount if money_in else -amount

    # 4. Wording, then default to money out
    lowered = description.lower()
    if any(word in lowered for word in CREDIT_WORDS):
        return amount
    return -amount


# ----------------------------------------------------------------------
# Strategy 2: plain text lines
# ----------------------------------------------------------------------

def _rows_from_text(pages_text, years, is_card):
    rows, section, previous_balance = [], None, None

    for page_text in pages_text:
        for line in page_text.splitlines():
            line = line.strip()
            if not line:
                continue

            match = LINE_RE.match(line)
            if not match:
                if len(line) < 70 and not AMOUNT_RE.search(line):
                    section = _section_from_heading(line, is_card) or section
                continue

            description = match.group("desc").strip()
            if not description or any(description.lower().startswith(s) for s in SKIP_DESCRIPTIONS):
                continue

            parsed = [_parse_amount(t) for t in AMOUNT_RE.findall(match.group("amts"))]
            parsed = [p for p in parsed if p[0] is not None]
            if not parsed:
                continue

            amount, marker = parsed[0]
            balance = parsed[-1][0] if len(parsed) >= 2 else None
            if balance is not None and parsed[-1][1] == "neg":
                balance = -balance

            signed = _decide_sign(amount, marker, balance, previous_balance,
                                  section, description, is_card)
            if balance is not None:
                previous_balance = balance

            rows.append({
                "Date": _add_year(match.group("date"), years),
                "Description": description,
                "Amount": round(signed, 2),
                "Balance": balance,
            })

    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Strategy 1: ruled tables
# ----------------------------------------------------------------------

def _unique_names(cells):
    names, seen = [], Counter()
    for index, cell in enumerate(cells):
        name = _clean_cell(cell) or f"column_{index + 1}"
        seen[name] += 1
        names.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return names


def _tables_to_frame(pdf):
    """Stitch every page's tables together, carrying the header forward."""
    header = None
    frames = []
    headerless = []

    for page in pdf.pages:
        for table in page.extract_tables() or []:
            grid = [[_clean_cell(c) for c in row] for row in table if row and any(row)]
            if len(grid) < 1 or len(grid[0]) < 3:
                continue

            scores = [header_row_score(row) for row in grid[:6]]
            best = max(range(len(scores)), key=lambda i: scores[i]) if scores else 0

            if scores and scores[best] >= 2:
                header = _unique_names(grid[best])
                body = grid[best + 1:]
            elif header and len(grid[0]) == len(header):
                body = grid                       # continuation page, header reused
            else:
                headerless.append(grid)
                continue

            if body:
                frames.append(pd.DataFrame(body, columns=header))

    if frames:
        frame = pd.concat(frames, ignore_index=True)
        return frame, "table"
    if headerless:
        width = Counter(len(g[0]) for g in headerless).most_common(1)[0][0]
        grid = [row for g in headerless if len(g[0]) == width for row in g]
        return _infer_headers(pd.DataFrame(grid)), "inferred"
    return pd.DataFrame(), None


def _clean_table_frame(frame):
    """Drop repeated header rows and blanks; merge wrapped description lines."""
    roles = {}
    for column in frame.columns:
        role, _ = classify_header(column)
        if role and role not in roles:
            roles[role] = column

    date_col, desc_col = roles.get("date"), roles.get("description")
    money_cols = [roles[r] for r in ("amount", "debit", "credit") if r in roles]

    # Repeated header rows (every page prints them again)
    keep = [header_row_score(list(row)) < 2 for row in frame.astype(str).values]
    frame = frame[keep].reset_index(drop=True)

    merged = []
    for _, row in frame.iterrows():
        row = row.copy()
        has_money = any(_number_or_none(row[c]) is not None for c in money_cols)
        has_date = bool(date_col and _is_date(row[date_col]))
        # A row with text but no date and no amount is the previous line wrapping
        if desc_col and merged and not has_money and not has_date and str(row[desc_col]).strip():
            merged[-1][desc_col] = f"{merged[-1][desc_col]} {row[desc_col]}".strip()
            continue
        if desc_col and not str(row[desc_col]).strip() and not has_money:
            continue
        merged.append(row)

    return pd.DataFrame(merged).reset_index(drop=True)


# ----------------------------------------------------------------------
# Strategy 3: infer a header from content
# ----------------------------------------------------------------------

def _infer_headers(frame):
    frame = frame.copy()
    frame.columns = range(frame.shape[1])
    stats = {}
    for column in frame.columns:
        cells = [str(v).strip() for v in frame[column] if str(v).strip()]
        if not cells:
            continue
        stats[column] = {
            "dates": sum(_is_date(c) for c in cells) / len(cells),
            "numbers": sum(_number_or_none(c) is not None for c in cells) / len(cells),
            "length": sum(len(c) for c in cells) / len(cells),
        }

    names = {}
    date_candidates = [c for c, s in stats.items() if s["dates"] >= 0.6]
    if date_candidates:
        names[date_candidates[0]] = "Date"

    numeric = [c for c, s in stats.items() if s["numbers"] >= 0.6 and c not in names]
    text = [c for c, s in stats.items() if c not in names and c not in numeric]
    if text:
        names[max(text, key=lambda c: stats[c]["length"])] = "Description"

    # Last numeric column is a running balance if it explains the others
    if len(numeric) >= 2:
        last, others = numeric[-1], numeric[:-1]
        balances = [_number_or_none(v) for v in frame[last]]
        hits = checks = 0
        for i in range(1, len(balances)):
            if balances[i] is None or balances[i - 1] is None:
                continue
            delta = abs(balances[i] - balances[i - 1])
            for other in others:
                amount = _number_or_none(frame.at[i, other])
                if amount is not None:
                    checks += 1
                    hits += abs(delta - abs(amount)) < 0.011
                    break
        if checks and hits / checks >= 0.7:
            names[last] = "Balance"
            numeric = others

    if len(numeric) == 1:
        names[numeric[0]] = "Amount"
    elif len(numeric) == 2:
        names[numeric[0]], names[numeric[1]] = "Debit", "Credit"
    elif len(numeric) > 2:
        names[numeric[0]] = "Amount"

    frame = frame[[c for c in frame.columns if c in names]]
    return frame.rename(columns=names)


def _signs_from_balance(frame, amount_col, balance_col):
    """If amounts are all positive but a balance column exists, derive the signs."""
    amounts = frame[amount_col].map(_number_or_none)
    balances = frame[balance_col].map(_number_or_none)
    if amounts.isna().all() or (amounts.dropna() < 0).any():
        return frame
    signed, previous, resolved = [], None, 0
    for amount, balance in zip(amounts, balances):
        if amount is None or pd.isna(amount):
            signed.append(amount)
            continue
        value = -amount  # default: money out
        if previous is not None and balance is not None and not pd.isna(balance):
            delta = balance - previous
            if abs(abs(delta) - amount) < 0.011 and delta != 0:
                value = amount if delta > 0 else -amount
                resolved += 1
        signed.append(value)
        if balance is not None and not pd.isna(balance):
            previous = balance
    if resolved >= 2:
        frame = frame.copy()
        frame[amount_col] = signed
    return frame


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def read_pdf_statement(file_bytes, password=None):
    """
    Returns (DataFrame, info). info has: method, is_card, warnings.
    Raises PdfStatementError with a user-friendly message.
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes), password=password)
    except Exception as error:
        if "password" in repr(error).lower():
            raise PdfStatementError(
                "This PDF is password protected. Enter the password and try again."
                if password is None else
                "That password didn't open the PDF. Check it and try again."
            ) from error
        raise PdfStatementError(
            "This file couldn't be opened as a PDF. Download it again from your bank."
        ) from error

    with pdf:
        pages_text = [(page.extract_text() or "") for page in pdf.pages]
        full_text = "\n".join(pages_text)

        if len(full_text.strip()) < 40:
            raise PdfStatementError(
                "This PDF has no selectable text (it looks like a scan or photo). "
                "Download the statement directly from your bank's website instead."
            )

        years = _statement_years(full_text)
        is_card = _looks_like_card(full_text)
        warnings = []

        frame, method = _tables_to_frame(pdf)
        if not frame.empty and method == "table":
            frame = _clean_table_frame(frame)

        usable = (
            not frame.empty
            and len(frame) >= 3
            and any(classify_header(c)[0] in ("amount", "debit", "credit") for c in frame.columns)
        )

        if not usable:
            frame, method = _rows_from_text(pages_text, years, is_card), "text"

    if frame.empty:
        raise PdfStatementError(
            "No transactions could be found in this PDF. If it's a summary or "
            "cover page, upload the statement that lists the individual transactions."
        )

    # Normalise dates, and recover signs from the balance column when possible
    roles = {}
    for column in frame.columns:
        role, _ = classify_header(column)
        roles.setdefault(role, column)

    if roles.get("date"):
        frame[roles["date"]] = frame[roles["date"]].map(lambda v: _add_year(v, years))
    if method != "text" and roles.get("amount") and roles.get("balance"):
        frame = _signs_from_balance(frame, roles["amount"], roles["balance"])

    if method == "inferred":
        warnings.append("Column headings weren't printed in this PDF, so they were guessed "
                        "from the data. Check the column settings below.")
    if is_card:
        warnings.append("This looks like a credit card statement. Purchases are counted "
                        "as money out and payments/refunds as money in.")

    return frame.reset_index(drop=True), {
        "method": method, "is_card": is_card, "warnings": warnings,
        # Tables on card statements list purchases as positive numbers
        "flip_default": bool(is_card and method != "text"),
    }
