"""
CHECKER 1: Schema Mismatch
--------------------------
WHAT IT CHECKS:
  Compares the column names in raw vs reference.
  - Extra columns in raw (columns that shouldn't exist)
  - Missing columns in raw (columns the reference expects but raw doesn't have)

LEVEL: schema  (this is a structural problem, not a row-level problem)

IN OUR DATA:
  raw has 'notes' which reference does not → that's an extra column.
"""

from profiler.base import BaseChecker, Issue
from typing import List
import pandas as pd


class SchemaMismatchChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Schema Mismatch"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []
        raw_cols = set(raw.columns)
        ref_cols = set(ref.columns)

        # Columns in raw that reference doesn't have
        extra = raw_cols - ref_cols
        if extra:
            issues.append(Issue(
                level="schema",
                category="Schema Mismatch",
                column=", ".join(sorted(extra)),
                affected=len(extra),
                detail=f"Column(s) present in raw but not in reference schema: {sorted(extra)}. "
                       f"These should be dropped or the schema updated.",
                examples=sorted(extra)
            ))

        # Columns reference expects but raw doesn't have
        missing = ref_cols - raw_cols
        if missing:
            issues.append(Issue(
                level="schema",
                category="Schema Mismatch",
                column=", ".join(sorted(missing)),
                affected=len(missing),
                detail=f"Column(s) expected by reference but missing in raw: {sorted(missing)}.",
                examples=sorted(missing)
            ))

        return issues
