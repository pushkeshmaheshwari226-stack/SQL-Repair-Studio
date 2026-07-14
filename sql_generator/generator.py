"""
sql_generator/generator.py
--------------------------
Takes the list of Issue objects from the profiler and generates
runnable DuckDB SQL to fix each one.

HOW IT WORKS:
  Each issue category maps to a SQL template function.
  The function receives the issue details and returns a SQL string.

WHY DUCKDB:
  DuckDB can read CSV files directly without a database server.
  You just run:  duckdb < fix.sql
  and it executes. Perfect for local data work.

"""

from typing import List
from profiler.base import Issue


# Valid mappings for out-of-domain fixes
COUNTRY_MAP = {
    "uk ":      "UK",
    "u.k.":     "UK",
    "united states": "US",
    "usa":      "US",
    "india":    "IN",
    "in ":      "IN",
    "in":       "IN",   # already correct but lowercase
    "india":    "IN",
    "ae":       "AE",
    "sg":       "SG",
}

SEGMENT_MAP = {
    "premium ":   "premium",
    "enterprise": "enterprise",
    "Premium":    "premium",
    "Enterprise": "enterprise",
    "Retail":     "retail",
    "retail ":    "retail",
    "primium":    "premium",
    "enterprize": "enterprise",
    "PREMIUM":    "premium",
}

IS_ACTIVE_MAP = {
    "Y":     "true",
    "yes":   "true",
    "1":     "true",
    "TRUE":  "true",
    "True":  "true",
    "no":    "false",
    "FALSE": "false",
    "False": "false",
    "0":     "false",
}


def _sql_for_schema_mismatch(issue: Issue) -> str:
    cols = [c.strip() for c in issue.column.split(",")]
    drop_clauses = [f"    -- DROP COLUMN {c}" for c in cols]
    return f"""-- FIX: Schema Mismatch — remove extra column(s) from raw
-- Run this to create a clean version without the extra column(s)
CREATE OR REPLACE TABLE customers_clean AS
SELECT
    customer_id,
    email,
    full_name,
    phone,
    signup_date,
    country,
    city,
    segment,
    is_active
    -- Dropped: {", ".join(cols)}
FROM read_csv_auto('data/raw/customers_raw.csv');
"""


def _sql_for_null_violations(issues: List[Issue]) -> str:
    lines = []
    for issue in issues:
        col = issue.column
        lines.append(
            f"    -- '{col}': {issue.affected} null(s) → delete or fill\n"
            f"    -- Option A: delete rows where {col} IS NULL\n"
            f"    --   DELETE FROM customers_clean WHERE {col} IS NULL;\n"
            f"    -- Option B: fill with placeholder\n"
            f"    --   UPDATE customers_clean SET {col} = 'UNKNOWN' WHERE {col} IS NULL;"
        )
    body = "\n\n".join(lines)
    return f"""-- FIX: Null Violations
-- For each column, choose DELETE (remove bad rows) or UPDATE (fill placeholder)
{body}
"""


def _sql_for_duplicates(issue: Issue) -> str:
    return f"""-- FIX: Duplicate Keys — keep only the first occurrence of each customer_id
CREATE OR REPLACE TABLE customers_deduped AS
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY customer_id) AS rn
    FROM read_csv_auto('data/raw/customers_raw.csv')
)
SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1;

-- Affected customer_ids (sample): {issue.examples}
"""


def _sql_for_out_of_domain(issues: List[Issue]) -> str:
    blocks = []

    for issue in issues:
        col = issue.column

        if col == "country":
            cases = "\n".join(
                f"        WHEN LOWER(TRIM({col})) = '{k}' THEN '{v}'"
                for k, v in COUNTRY_MAP.items()
            )
            blocks.append(f"""-- FIX: country — normalise to ISO 2-letter codes
UPDATE customers_clean
SET country = CASE
{cases}
        ELSE UPPER(TRIM(country))
    END
WHERE LOWER(TRIM(country)) NOT IN ('in','uk','us','ae','sg');
""")

        elif col == "segment":
            cases = "\n".join(
                f"        WHEN LOWER(TRIM({col})) = '{k.lower()}' THEN '{v}'"
                for k, v in {
                    "premium": "premium", "primium": "premium",
                    "enterprise": "enterprise", "enterprize": "enterprise",
                    "retail": "retail"
                }.items()
            )
            blocks.append(f"""-- FIX: segment — normalise to lowercase standard values
UPDATE customers_clean
SET segment = CASE
{cases}
        ELSE LOWER(TRIM(segment))
    END
WHERE LOWER(TRIM(segment)) NOT IN ('retail','premium','enterprise');
""")

        elif col == "is_active":
            blocks.append(f"""-- FIX: is_active — normalise to true/false
UPDATE customers_clean
SET is_active = CASE
        WHEN LOWER(TRIM(is_active)) IN ('y','yes','1','true')  THEN 'true'
        WHEN LOWER(TRIM(is_active)) IN ('n','no','0','false')  THEN 'false'
        ELSE is_active
    END
WHERE LOWER(TRIM(is_active)) NOT IN ('true','false');
""")

    return "\n".join(blocks)


def _sql_for_format(issues: List[Issue]) -> str:
    blocks = []
    for issue in issues:
        col = issue.column

        if col == "phone":
            blocks.append("""-- FIX: phone — add +91- prefix to bare 10-digit numbers
UPDATE customers_clean
SET phone = '+91-' || phone
WHERE phone NOT LIKE '+91-%'
  AND LENGTH(phone) = 10
  AND phone ~ '^[0-9]{10}$';
""")

        elif col == "email":
            blocks.append("""-- FIX: email — flag invalid emails (cannot auto-fix)
-- Review and correct manually or delete:
SELECT customer_id, email
FROM customers_clean
WHERE email NOT LIKE '%@%.%'
   OR email IS NULL;
""")

    return "\n".join(blocks)


def _sql_for_type_drift(issues: List[Issue]) -> str:
    blocks = []
    for issue in issues:
        col = issue.column

        if col == "signup_date":
            blocks.append("""-- FIX: signup_date — cast to DATE type; NULL out unparseable values
CREATE OR REPLACE TABLE customers_clean AS
SELECT * REPLACE (
    TRY_CAST(signup_date AS DATE) AS signup_date
)
FROM customers_clean;
""")

        elif col == "is_active":
            blocks.append("""-- FIX: is_active — already handled by out-of-domain fix above.
-- After normalising to 'true'/'false' strings, cast to BOOLEAN:
CREATE OR REPLACE TABLE customers_clean AS
SELECT * REPLACE (
    CAST(is_active AS BOOLEAN) AS is_active
)
FROM customers_clean;
""")

    return "\n".join(blocks)


def generate_sql(issues: List[Issue]) -> str:
    """
    Given all detected issues, produce a single SQL script that fixes them all.
    Returns the full SQL as a string.
    """
    from collections import defaultdict
    by_category = defaultdict(list)
    for issue in issues:
        by_category[issue.category].append(issue)

    parts = [
        "-- ============================================================",
        "-- DATA QUALITY REPAIR SCRIPT",
        "-- Generated by DQ Studio",
        "-- Dialect: DuckDB / ANSI SQL",
        "-- Run: duckdb < repair.sql",
        "-- ============================================================\n",
        "-- STEP 0: Load raw data into a working table",
        "CREATE OR REPLACE TABLE customers_clean AS",
        "SELECT * FROM read_csv_auto('data/raw/customers_raw.csv');\n",
    ]

    if "Schema Mismatch" in by_category:
        parts.append(_sql_for_schema_mismatch(by_category["Schema Mismatch"][0]))

    if "Null Violation" in by_category:
        parts.append(_sql_for_null_violations(by_category["Null Violation"]))

    if "Duplicate Key" in by_category:
        parts.append(_sql_for_duplicates(by_category["Duplicate Key"][0]))

    if "Out-of-Domain Value" in by_category:
        parts.append(_sql_for_out_of_domain(by_category["Out-of-Domain Value"]))

    if "Format Inconsistency" in by_category:
        parts.append(_sql_for_format(by_category["Format Inconsistency"]))

    if "Type Drift" in by_category:
        parts.append(_sql_for_type_drift(by_category["Type Drift"]))

    parts += [
        "\n-- STEP FINAL: Verify the cleaned table",
        "SELECT COUNT(*) AS total_rows,",
        "       COUNT(DISTINCT customer_id) AS unique_customers",
        "FROM customers_clean;",
    ]

    return "\n".join(parts)
