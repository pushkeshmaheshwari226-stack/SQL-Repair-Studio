"""
CHECKER 3: Duplicate Keys
-------------------------
WHAT IT CHECKS:
  customer_id should be a primary key — unique per row.
  If the same ID appears more than once, that's a data integrity violation.

LEVEL: content  (row-level problem)

IN OUR DATA:
  15 duplicate customer_ids found.
"""

from profiler.base import BaseChecker, Issue
from typing import List
import pandas as pd


class DuplicateKeyChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Duplicate Keys"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []

        # customer_id is the primary key in both datasets
        pk_col = "customer_id"
        if pk_col not in raw.columns:
            return issues

        dupes = raw[raw.duplicated(subset=[pk_col], keep=False)]
        dupe_ids = dupes[pk_col].unique().tolist()

        if len(dupe_ids) > 0:
            issues.append(Issue(
                level="content",
                category="Duplicate Key",
                column=pk_col,
                affected=len(dupes),   # total rows involved (not just unique IDs)
                detail=f"'{pk_col}' has {len(dupe_ids)} value(s) that appear more than once, "
                       f"affecting {len(dupes)} total rows. Primary keys must be unique.",
                examples=dupe_ids[:5]
            ))

        return issues
