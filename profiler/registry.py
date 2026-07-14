"""
registry.py — Finds and runs all checkers automatically.

HOW IT WORKS:
  1. It imports every .py file inside the checkers/ folder.
  2. Python's __subclasses__() returns every class that inherited BaseChecker.
  3. It runs each one's .check() method and collects all issues.

WHY THIS MATTERS:
  You never have to register a new checker. Just create a new file in
  checkers/ that subclasses BaseChecker, and the registry picks it up
  automatically next time the app runs. This is exactly what the assignment
  means by "adding a new issue type does not require modifying the profiling
  engine."
"""

import importlib
import pkgutil
import pandas as pd
from typing import List
from profiler.base import BaseChecker, Issue


def _load_all_checkers():
    """Import every module inside profiler/checkers/ so their classes register."""
    import profiler.checkers as checkers_pkg
    for _, module_name, _ in pkgutil.iter_modules(checkers_pkg.__path__):
        importlib.import_module(f"profiler.checkers.{module_name}")


def run_all_checks(raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
    """
    Load all checkers, run each one, return combined list of all issues.
    """
    _load_all_checkers()

    all_issues: List[Issue] = []
    for checker_class in BaseChecker.__subclasses__():
        checker = checker_class()
        try:
            issues = checker.check(raw, ref)
            all_issues.extend(issues)
        except Exception as e:
            # A broken checker should not crash the whole app
            all_issues.append(Issue(
                level="schema",
                category="Checker Error",
                column=None,
                affected=0,
                detail=f"{checker.name} failed: {e}",
                examples=[]
            ))
    return all_issues
