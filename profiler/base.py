"""
base.py — The contract every checker must follow.

WHY THIS EXISTS:
  The assignment says "adding a new issue type must NOT require modifying
  the profiling engine." The way to guarantee that is: every checker
  follows the same interface (BaseChecker). The engine only knows about
  BaseChecker — never about the individual checkers. So you can add 100
  new checkers and the engine never changes.

  This pattern is called the "Strategy" or "Plugin" pattern.
"""

from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass, field
from typing import List


@dataclass
class Issue:
    """
    One detected data quality problem.

    Fields:
      level      — "schema" (column-level) or "content" (row-level)
      category   — e.g. "Null Violation", "Duplicate Key"
      column     — which column is affected (None if whole-table issue)
      affected   — how many rows / columns are affected
      detail     — human-readable description of the problem
      examples   — up to 5 sample bad values so the user can see the issue
    """
    level: str          # "schema" or "content"
    category: str
    column: str
    affected: int
    detail: str
    examples: List = field(default_factory=list)


class BaseChecker(ABC):
    """
    Every checker must inherit from this class and implement two methods:

      name()   — returns a short label like "Null Violations"
      check()  — receives raw df + reference df, returns a list of Issue objects

    That's the entire contract. The profiling engine calls these two methods
    and nothing else.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short human-readable name for this checker."""
        pass

    @abstractmethod
    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        """
        Run the check. Return a (possibly empty) list of Issue objects.
        Never raise — return [] if nothing is wrong.
        """
        pass
