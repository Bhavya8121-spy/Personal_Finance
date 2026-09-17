import os
import sqlite3

from src.categories import (
    is_valid_category,
    is_valid_subcategory
)


# ==========================================================
# DATABASE CONFIGURATION
# ==========================================================

DB_PATH = "data/transactions.db"


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_connection():

    folder = os.path.dirname(DB_PATH)

    if folder:
        os.makedirs(folder, exist_ok=True)

    conn = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    # SQLite does not enforce foreign keys by default.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ==========================================================
# CREATE DATABASE TABLES
# ==========================================================

def create_tables():

    with get_connection() as conn:

        cursor = conn.cursor()

        # ==================================================
        # MERCHANTS
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchants (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                canonical_name TEXT NOT NULL UNIQUE,

                default_category TEXT,

                default_subcategory TEXT,

                category_confidence REAL
                    CHECK (
                        category_confidence IS NULL
                        OR (
                            category_confidence >= 0
                            AND category_confidence <= 1
                        )
                    )
            )
        """)

        # ==================================================
        # MERCHANT ALIASES
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchant_aliases (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                merchant_id INTEGER NOT NULL,

                alias TEXT NOT NULL UNIQUE,

                FOREIGN KEY (merchant_id)
                    REFERENCES merchants(id)
                    ON DELETE CASCADE
            )
        """)

        # ==================================================
        # KEYWORD EVIDENCE
        #
        # Stores evidence collected from user corrections.
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_evidence (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                keyword TEXT NOT NULL,

                category TEXT NOT NULL,

                subcategory TEXT NOT NULL,

                positive_votes INTEGER NOT NULL DEFAULT 0,

                negative_votes INTEGER NOT NULL DEFAULT 0,

                UNIQUE (
                    keyword,
                    category,
                    subcategory
                )
            )
        """)

        # ==================================================
        # LEARNED KEYWORDS
        #
        # Keywords promoted after enough evidence.
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_keywords (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                keyword TEXT NOT NULL UNIQUE,

                category TEXT NOT NULL,

                subcategory TEXT NOT NULL,

                confidence REAL NOT NULL,

                evidence_count INTEGER NOT NULL DEFAULT 0
            )
        """)
# ==========================================================
# ADD MERCHANT
# ==========================================================

def add_merchant(
    name,
    default_category=None,
    default_subcategory=None,
    category_confidence=None,
    aliases=None
):

    # ======================================================
    # CLEAN INPUTS
    # ======================================================

    name = str(name).strip()

    if not name:
        raise ValueError(
            "Merchant name cannot be empty."
        )

    if aliases is None:
        aliases = []

    # ======================================================
    # VALIDATE CATEGORY
    # ======================================================

    if default_category is not None:

        if not is_valid_category(
            default_category
        ):
            raise ValueError(
                f"Invalid category: "
                f"{default_category}"
            )

    # ======================================================
    # VALIDATE SUBCATEGORY
    # ======================================================

    if (
        default_category is not None
        and default_subcategory is not None
    ):

        if not is_valid_subcategory(
            default_category,
            default_subcategory
        ):
            raise ValueError(
                f"Invalid subcategory "
                f"'{default_subcategory}' "
                f"for category "
                f"'{default_category}'"
            )

    # ======================================================
    # VALIDATE CONFIDENCE
    # ======================================================

    if category_confidence is not None:

        if not 0 <= category_confidence <= 1:

            raise ValueError(
                "category_confidence must "
                "be between 0 and 1."
            )

    # ======================================================
    # DATABASE
    # ======================================================

    with get_connection() as conn:

        cursor = conn.cursor()

        # ==================================================
        # 1. CREATE MERCHANT IF IT DOES NOT EXIST
        # ==================================================

        cursor.execute(
            """
            INSERT OR IGNORE INTO merchants (
                canonical_name,
                default_category,
                default_subcategory,
                category_confidence
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                default_category,
                default_subcategory,
                category_confidence
            )
        )

        # ==================================================
        # 2. GET MERCHANT ID
        # ==================================================

        cursor.execute(
            """
            SELECT id
            FROM merchants
            WHERE canonical_name = ?
            """,
            (name,)
        )

        row = cursor.fetchone()

        if row is None:

            raise RuntimeError(
                f"Could not create or find "
                f"merchant: {name}"
            )

        merchant_id = row[0]

        # ==================================================
        # 3. CHECK EXISTING MERCHANT KNOWLEDGE
        # ==================================================

        cursor.execute(
            """
            SELECT
                default_category,
                default_subcategory,
                category_confidence

            FROM merchants

            WHERE id = ?
            """,
            (merchant_id,)
        )

        existing = cursor.fetchone()

        # ==================================================
        # 4. UPDATE IF NEW KNOWLEDGE IS BETTER
        # ==================================================

        if existing:

            existing_confidence = (
                existing[2]
                if existing[2] is not None
                else 0.0
            )

            new_confidence = (
                category_confidence
                if category_confidence is not None
                else 0.0
            )

            if (
                new_confidence
                > existing_confidence
            ):

                cursor.execute(
                    """
                    UPDATE merchants

                    SET
                        default_category = ?,
                        default_subcategory = ?,
                        category_confidence = ?

                    WHERE id = ?
                    """,
                    (
                        default_category,
                        default_subcategory,
                        category_confidence,
                        merchant_id
                    )
                )

        # ==================================================
        # 5. ADD MERCHANT ALIASES
        # ==================================================

        for alias in aliases:

            if alias is None:
                continue

            normalized_alias = (
                str(alias)
                .upper()
                .strip()
            )

            if not normalized_alias:
                continue

            cursor.execute(
                """
                INSERT OR IGNORE INTO merchant_aliases (
                    merchant_id,
                    alias
                )
                VALUES (?, ?)
                """,
                (
                    merchant_id,
                    normalized_alias
                )
            )

        # ==================================================
        # 6. RETURN MERCHANT ID
        # ==================================================

        return merchant_id

# ==========================================================
# GET ALL MERCHANT ALIASES
# ==========================================================

def get_all_merchant_aliases():

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                merchants.id,
                merchants.canonical_name,
                merchants.default_category,
                merchants.default_subcategory,
                merchants.category_confidence,
                merchant_aliases.alias

            FROM merchant_aliases

            JOIN merchants
                ON merchant_aliases.merchant_id
                = merchants.id
        """)

        return cursor.fetchall()


# ==========================================================
# GET MERCHANT BY ID
# ==========================================================

def get_merchant_by_id(merchant_id):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                canonical_name,
                default_category,
                default_subcategory,
                category_confidence

            FROM merchants

            WHERE id = ?
            """,
            (merchant_id,)
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "merchant_id": row[0],
            "merchant": row[1],
            "default_category": row[2],
            "default_subcategory": row[3],
            "category_confidence": row[4]
        }
    # ==========================================================
# LEARNED KEYWORDS
# ==========================================================

def get_learned_keywords():

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                keyword,
                category,
                subcategory,
                confidence,
                evidence_count

            FROM learned_keywords
        """)

        rows = cursor.fetchall()

    return [
        {
            "keyword": row[0],
            "category": row[1],
            "subcategory": row[2],
            "confidence": row[3],
            "evidence_count": row[4],
        }
        for row in rows
    ]


# ==========================================================
# RECORD KEYWORD EVIDENCE
# ==========================================================

def record_keyword_evidence(
    keyword,
    category,
    subcategory
):

    keyword = str(
        keyword
    ).upper().strip()

    if not keyword:
        return

    if not is_valid_category(
        category
    ):
        raise ValueError(
            f"Invalid category: {category}"
        )

    if not is_valid_subcategory(
        category,
        subcategory
    ):
        raise ValueError(
            f"Invalid subcategory: "
            f"{subcategory}"
        )

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO keyword_evidence (
                keyword,
                category,
                subcategory,
                positive_votes
            )

            VALUES (?, ?, ?, 1)

            ON CONFLICT(
                keyword,
                category,
                subcategory
            )

            DO UPDATE SET
                positive_votes =
                positive_votes + 1
            """,
            (
                keyword,
                category,
                subcategory
            )
        )


# ==========================================================
# PROMOTE STRONG KEYWORDS
# ==========================================================

def promote_keyword_if_ready(
    keyword,
    minimum_evidence=5,
    minimum_agreement=0.80
):

    keyword = str(
        keyword
    ).upper().strip()

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                category,
                subcategory,
                positive_votes,
                negative_votes

            FROM keyword_evidence

            WHERE keyword = ?
            """,
            (keyword,)
        )

        rows = cursor.fetchall()

        if not rows:
            return False

        total_positive = sum(
            row[2]
            for row in rows
        )

        total_negative = sum(
            row[3]
            for row in rows
        )

        total_evidence = (
            total_positive
            + total_negative
        )

        if total_evidence < minimum_evidence:
            return False

        best = max(
            rows,
            key=lambda row: row[2]
        )

        category = best[0]
        subcategory = best[1]
        best_votes = best[2]

        agreement = (
            best_votes / total_evidence
        )

        if agreement < minimum_agreement:
            return False

        cursor.execute(
            """
            INSERT INTO learned_keywords (
                keyword,
                category,
                subcategory,
                confidence,
                evidence_count
            )

            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(keyword)

            DO UPDATE SET
                category = excluded.category,
                subcategory = excluded.subcategory,
                confidence = excluded.confidence,
                evidence_count = excluded.evidence_count
            """,
            (
                keyword,
                category,
                subcategory,
                agreement,
                total_evidence
            )
        )

        return True
    def save_merchant_correction(
        merchant_name,
        alias,
        category,
        subcategory
    ):

        if not merchant_name:

            merchant_name = alias

    merchant_name = str(
        merchant_name
    ).strip()

    alias = str(
        alias
    ).upper().strip()

    return add_merchant(
        name=merchant_name,
        default_category=category,
        default_subcategory=subcategory,
        category_confidence=1.0,
        aliases=[
            alias,
            merchant_name.upper()
        ]
    )
# ==========================================================
# SAVE MERCHANT CORRECTION
# ==========================================================

def save_merchant_correction(
    merchant_name,
    alias,
    category,
    subcategory
):

    # ------------------------------------------------------
    # Validate merchant name
    # ------------------------------------------------------

    if not merchant_name:

        merchant_name = alias

    merchant_name = str(
        merchant_name
    ).strip()

    if not merchant_name:

        raise ValueError(
            "Merchant name cannot be empty."
        )

    # ------------------------------------------------------
    # Clean alias
    # ------------------------------------------------------

    alias = str(
        alias
    ).upper().strip()

    # ------------------------------------------------------
    # Store correction
    #
    # Human-provided corrections receive confidence 1.0.
    # ------------------------------------------------------

    return add_merchant(
        name=merchant_name,

        default_category=category,

        default_subcategory=subcategory,

        category_confidence=1.0,

        aliases=[
            alias,
            merchant_name.upper()
        ]
    )