# DQ Studio — Data Quality & SQL Repair

A web application that ingests a raw dataset, compares it against a reference schema, identifies data quality issues, and generates SQL transformations to fix them.

Built for the BrightLife Care / HealthKart Data Engineering Internship Assignment.

---

## Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/dq-studio.git
cd dq-studio

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

---

## Project Structure

```
dq-studio/
├── app.py                        # Streamlit UI — entry point
├── profiler/
│   ├── base.py                   # BaseChecker abstract class (the plugin contract)
│   ├── registry.py               # Auto-discovers and runs all checkers
│   └── checkers/
│       ├── schema_mismatch.py    # Detects extra/missing columns
│       ├── null_violations.py    # Detects nulls in required fields
│       ├── duplicate_keys.py     # Detects duplicate customer_ids
│       ├── out_of_domain.py      # Detects invalid country/segment/is_active values
│       ├── format_inconsistency.py # Detects wrong phone/email/date formats
│       └── type_drift.py         # Detects is_active and date type problems
├── sql_generator/
│   └── generator.py              # Generates DuckDB SQL fixes per issue category
├── data/
│   ├── raw/customers_raw.csv
│   └── reference/customers_reference.csv
└── requirements.txt
```

---

## Issues Detected

The app detects 6 categories of data quality issues:

| Category | Level | Description |
|---|---|---|
| Schema Mismatch | Schema | Extra or missing columns vs. reference |
| Null Violation | Content | Nulls in columns that should be non-null |
| Duplicate Key | Content | customer_id appears more than once |
| Out-of-Domain Value | Content | Values outside the reference domain (country, segment, is_active) |
| Format Inconsistency | Content | Phone/email/date not matching expected pattern |
| Type Drift | Content | is_active and signup_date stored as wrong type |

---

## How to Add a New Issue Type

This is the key design decision: **adding a new checker requires zero changes to the engine.**

1. Create a new file in `profiler/checkers/`, e.g. `whitespace_trim.py`
2. Define a class that inherits from `BaseChecker`
3. Implement two methods: `name` (property) and `check(raw, ref) → List[Issue]`
4. That's it. The registry auto-discovers it on next run.

Example:

```python
from profiler.base import BaseChecker, Issue
import pandas as pd
from typing import List

class WhitespaceTrimChecker(BaseChecker):

    @property
    def name(self) -> str:
        return "Whitespace Trim"

    def check(self, raw: pd.DataFrame, ref: pd.DataFrame) -> List[Issue]:
        issues = []
        for col in raw.select_dtypes(include="object").columns:
            has_whitespace = raw[col].dropna().str.match(r"^\s|\s$").sum()
            if has_whitespace:
                issues.append(Issue(
                    level="content",
                    category="Whitespace Trim",
                    column=col,
                    affected=int(has_whitespace),
                    detail=f"'{col}' has {has_whitespace} value(s) with leading/trailing spaces.",
                    examples=[]
                ))
        return issues
```

The registry picks it up automatically — no registration, no imports needed elsewhere.

---

## SQL Execution

The generated SQL is valid DuckDB. To run it directly:

```bash
# Install DuckDB CLI
pip install duckdb

# Run the repair script
duckdb < repair.sql
```

Or download the script from the app UI and paste it into any DuckDB client.

---

## Tech Stack

- **Streamlit** — Python-native web UI
- **Pandas** — data loading and profiling
- **DuckDB** — SQL dialect for all generated fixes
- **Python 3.10+**

---

## License

MIT License
