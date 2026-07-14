"""
CHECKER 2: Null Violations
--------------------------
WHAT IT CHECKS:
  In the reference dataset, all columns are non-null (complete clean data).
  So any column in raw that has nulls where reference has none is a violation.

LEVEL: content  (this is a row-level problem)

IN OUR DATA:
  email(2), full_name(4), phone(4), signup_date(7), city(2), segment(6)
  all have null values.
"""

from profiler.base import BaseChecker, Issue
from typing import List
import pandas as pd


class NullViolationChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Null Violations"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []

        # Only check columns that exist in both (ignore schema-level extras)
        shared_cols = [c for c in ref.columns if c in raw.columns]

        for col in shared_cols:
            null_count = raw[col].isnull().sum()
            ref_nulls = ref[col].isnull().sum()

            # Flag if raw has nulls but reference column is fully populated
            if null_count > 0 and ref_nulls == 0:
                # Get the row indices (customer_ids) where this column is null
                null_rows = raw[raw[col].isnull()]['customer_id'].tolist()
                issues.append(Issue(
                    level="content",
                    category="Null Violation",
                    column=col,
                    affected=int(null_count),
                    detail=f"'{col}' has {null_count} null value(s). "
                           f"Reference schema requires this column to be non-null.",
                    examples=null_rows[:5]  # show up to 5 affected customer IDs
                ))

        return issues
