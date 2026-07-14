"""
CHECKER 4: Out-of-Domain Values
--------------------------------
WHAT IT CHECKS:
  Some columns have a fixed set of valid values (a "domain").
  Any value outside that set is an out-of-domain violation.

  We derive the valid domain from the reference dataset.

LEVEL: content  (row-level problem)

IN OUR DATA:
  country  → raw has 14 variants; reference only uses: IN, UK, US, AE, SG
  segment  → raw has 12 variants; reference only uses: retail, premium, enterprise
  is_active → raw has 11 variants; reference only uses: true, false

NOTE: We normalise both sides to lowercase+stripped before comparing,
  so the "domain" comparison is case-insensitive. But we still flag the
  original bad values so the SQL fix can target them precisely.
"""

from profiler.base import BaseChecker, Issue
from typing import List
import pandas as pd


# Columns where we enforce domain from reference
DOMAIN_COLUMNS = ["country", "segment", "is_active"]


class OutOfDomainChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Out-of-Domain Values"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []

        for col in DOMAIN_COLUMNS:
            if col not in raw.columns or col not in ref.columns:
                continue

            # Valid values from reference (lowercase, stripped)
            # Cast to str first to handle boolean columns
            valid_values = set(
                ref[col].dropna().astype(str).str.strip().str.lower().unique()
            )

            # Find raw values that don't match (after normalising)
            raw_normalised = raw[col].dropna().astype(str).str.strip().str.lower()
            bad_mask = ~raw_normalised.isin(valid_values)
            bad_original = raw.loc[raw[col].notna() & bad_mask, col].astype(str)
            bad_unique = bad_original.unique().tolist()
            bad_count = bad_mask.sum()

            if bad_count > 0:
                issues.append(Issue(
                    level="content",
                    category="Out-of-Domain Value",
                    column=col,
                    affected=int(bad_count),
                    detail=f"'{col}' has {bad_count} value(s) outside the reference domain "
                           f"{sorted(valid_values)}. Found invalid values: {bad_unique[:8]}",
                    examples=bad_unique[:5]
                ))

        return issues
