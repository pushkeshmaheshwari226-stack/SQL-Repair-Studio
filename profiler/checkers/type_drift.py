"""
CHECKER 6: Type Drift
----------------------
WHAT IT CHECKS:
  Columns that should be a specific type (date, boolean, integer)
  but the raw data stores them as plain strings.

  We don't compare dtypes directly (both CSVs load as strings),
  instead we try to PARSE each value and count failures.

LEVEL: content  (row-level problem)

IN OUR DATA:
  signup_date → should parse as a date; any unparseable string is flagged
  is_active   → should be boolean; raw has Y/no/1/0/FALSE etc.
"""

from profiler.base import BaseChecker, Issue
from typing import List
import pandas as pd


# Valid boolean representations (lowercase)
VALID_BOOL = {"true", "false"}


class TypeDriftChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Type Drift"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []

        # --- Check signup_date can be parsed as a date ---
        if "signup_date" in raw.columns:
            parsed = pd.to_datetime(raw["signup_date"], errors="coerce")
            bad_count = parsed.isnull().sum() - raw["signup_date"].isnull().sum()
            bad_values = raw.loc[
                parsed.isnull() & raw["signup_date"].notna(), "signup_date"
            ].unique().tolist()

            if bad_count > 0:
                issues.append(Issue(
                    level="content",
                    category="Type Drift",
                    column="signup_date",
                    affected=int(bad_count),
                    detail=f"'signup_date' has {bad_count} value(s) that cannot be parsed "
                           f"as a valid date. Expected YYYY-MM-DD.",
                    examples=[str(v) for v in bad_values[:5]]
                ))

        # --- Check is_active is a proper boolean ---
        if "is_active" in raw.columns:
            non_null = raw["is_active"].dropna().astype(str).str.strip().str.lower()
            bad_mask = ~non_null.isin(VALID_BOOL)
            bad_values = non_null[bad_mask].unique().tolist()
            bad_count = int(bad_mask.sum())

            if bad_count > 0:
                issues.append(Issue(
                    level="content",
                    category="Type Drift",
                    column="is_active",
                    affected=bad_count,
                    detail=f"'is_active' should be boolean (true/false) but has "
                           f"{bad_count} non-boolean value(s): {bad_values[:8]}",
                    examples=bad_values[:5]
                ))

        return issues
