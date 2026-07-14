"""
CHECKER 5: Format Inconsistencies
----------------------------------
WHAT IT CHECKS:
  Even when a value isn't null or out-of-domain, it can be in the wrong
  format. We check specific columns against expected regex patterns.

LEVEL: content  (row-level problem)

IN OUR DATA:
  phone      → should match +91-XXXXXXXXXX  (some rows just have 10 digits)
  email      → should be a valid email format
  signup_date → should be YYYY-MM-DD
  customer_id → should match C followed by 6 digits

HOW TO ADD A NEW FORMAT RULE:
  Just add an entry to FORMAT_RULES below. No other file changes needed.
"""

from profiler.base import BaseChecker, Issue
from typing import List
import pandas as pd
import re

# Each rule: (column, regex_pattern, human description)
FORMAT_RULES = [
    (
        "phone",
        r"^\+91-\d{10}$",
        "Expected format: +91-XXXXXXXXXX (10 digits after country code)"
    ),
    (
        "email",
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        "Expected format: valid email (name@domain.tld)"
    ),
    (
        "signup_date",
        r"^\d{4}-\d{2}-\d{2}$",
        "Expected format: YYYY-MM-DD"
    ),
    (
        "customer_id",
        r"^C\d{6}$",
        "Expected format: C followed by exactly 6 digits (e.g. C200488)"
    ),
]


class FormatInconsistencyChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Format Inconsistency"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []

        for col, pattern, description in FORMAT_RULES:
            if col not in raw.columns:
                continue

            non_null = raw[col].dropna()
            bad_mask = ~non_null.astype(str).str.match(pattern)
            bad_values = non_null[bad_mask].unique().tolist()
            bad_count = bad_mask.sum()

            if bad_count > 0:
                issues.append(Issue(
                    level="content",
                    category="Format Inconsistency",
                    column=col,
                    affected=int(bad_count),
                    detail=f"'{col}' has {bad_count} value(s) not matching the expected format. "
                           f"{description}.",
                    examples=[str(v) for v in bad_values[:5]]
                ))

        return issues
