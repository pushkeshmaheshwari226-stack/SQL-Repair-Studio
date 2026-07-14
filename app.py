"""
app.py — Main Streamlit application
------------------------------------
This is the entry point. Run it with:
    streamlit run app.py

WHAT STREAMLIT DOES:
  Every time the page loads or a user interacts, Python runs top to bottom.
  st.title(), st.write(), st.dataframe() etc. all render HTML automatically.
  You write Python; Streamlit turns it into a website.

STRUCTURE OF THIS APP:
  1. Load the two CSV files
  2. Show a side-by-side schema comparison
  3. Run all checkers via the registry
  4. Show issues grouped by category (schema-level and content-level)
  5. Show the generated SQL repair script
"""

import streamlit as st
import pandas as pd
import sys
import os

# Make sure the project root is on the Python path
sys.path.insert(0, os.path.dirname(__file__))

from profiler.registry import run_all_checks
from sql_generator.generator import generate_sql

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DQ Studio — HealthKart Assignment",
    page_icon="🔍",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔍 Data Quality & SQL Repair Studio")
st.caption("BrightLife Care · Data Engineering Internship Assignment")
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
RAW_PATH = "data/raw/customers_raw.csv"
REF_PATH = "data/reference/customers_reference.csv"


@st.cache_data  # cache so we don't re-read files on every interaction
def load_data():
    raw = pd.read_csv(RAW_PATH)
    ref = pd.read_csv(REF_PATH)
    return raw, ref


try:
    raw_df, ref_df = load_data()
except FileNotFoundError as e:
    st.error(f"Could not find data files: {e}. Make sure you're running from the project root.")
    st.stop()

# ── Section 1: Dataset Overview ───────────────────────────────────────────────
st.header("📁 Dataset Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Raw Rows", f"{len(raw_df):,}")
col2.metric("Raw Columns", len(raw_df.columns))
col3.metric("Reference Rows", f"{len(ref_df):,}")
col4.metric("Reference Columns", len(ref_df.columns))

st.subheader("Side-by-Side Schema Comparison")
schema_data = []
all_cols = sorted(set(list(raw_df.columns) + list(ref_df.columns)))
for col in all_cols:
    in_raw = "✅" if col in raw_df.columns else "❌"
    in_ref = "✅" if col in ref_df.columns else "❌"
    raw_dtype = str(raw_df[col].dtype) if col in raw_df.columns else "—"
    ref_dtype = str(ref_df[col].dtype) if col in ref_df.columns else "—"
    null_count = int(raw_df[col].isnull().sum()) if col in raw_df.columns else 0
    flag = "⚠️ Extra" if col in raw_df.columns and col not in ref_df.columns else \
           "⚠️ Missing" if col not in raw_df.columns and col in ref_df.columns else ""
    schema_data.append({
        "Column": col,
        "In Raw": in_raw,
        "In Reference": in_ref,
        "Raw dtype": raw_dtype,
        "Ref dtype": ref_dtype,
        "Nulls in Raw": null_count,
        "Note": flag
    })

st.dataframe(pd.DataFrame(schema_data), use_container_width=True, hide_index=True)

with st.expander("👁️ Preview Raw Data (first 10 rows)"):
    st.dataframe(raw_df.head(10), use_container_width=True)

with st.expander("👁️ Preview Reference Data (first 10 rows)"):
    st.dataframe(ref_df.head(10), use_container_width=True)

st.divider()

# ── Section 2: Run Profiler ───────────────────────────────────────────────────
st.header("🧪 Issues Report")

with st.spinner("Running all data quality checks..."):
    issues = run_all_checks(raw_df, ref_df)

# Summary metrics
schema_issues = [i for i in issues if i.level == "schema"]
content_issues = [i for i in issues if i.level == "content"]

c1, c2, c3 = st.columns(3)
c1.metric("Total Issues Found", len(issues))
c2.metric("Schema-Level Issues", len(schema_issues))
c3.metric("Content-Level Issues", len(content_issues))

# Group by category for display
from collections import defaultdict
by_category = defaultdict(list)
for issue in issues:
    by_category[issue.category].append(issue)

# ── Schema-level issues ───────────────────────────────────────────────────────
st.subheader("🏗️ Schema-Level Issues")
st.caption("These are structural problems — wrong columns, wrong types at the table level.")

if schema_issues:
    for issue in schema_issues:
        with st.container(border=True):
            st.markdown(f"**{issue.category}** · Column(s): `{issue.column}` · Affected: `{issue.affected}`")
            st.write(issue.detail)
            if issue.examples:
                st.code(str(issue.examples), language=None)
else:
    st.success("No schema-level issues found.")

# ── Content-level issues ──────────────────────────────────────────────────────
st.subheader("📋 Content-Level Issues")
st.caption("These are row/value problems — nulls, duplicates, wrong values.")

CATEGORY_ICONS = {
    "Null Violation":        "🟡",
    "Duplicate Key":         "🔴",
    "Out-of-Domain Value":   "🟠",
    "Format Inconsistency":  "🔵",
    "Type Drift":            "🟣",
}

if content_issues:
    for category, cat_issues in by_category.items():
        if cat_issues[0].level != "content":
            continue
        icon = CATEGORY_ICONS.get(category, "⚪")
        st.markdown(f"#### {icon} {category}")
        rows = []
        for issue in cat_issues:
            rows.append({
                "Column": issue.column,
                "Affected Rows": issue.affected,
                "Detail": issue.detail,
                "Sample Bad Values": str(issue.examples[:3])
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.success("No content-level issues found.")

st.divider()

# ── Section 3: SQL Repair Script ──────────────────────────────────────────────
st.header("🛠️ Generated SQL Repair Script")
st.caption("Copy this into DuckDB to fix all detected issues. Each block is commented to explain what it does.")

sql_script = generate_sql(issues)
st.code(sql_script, language="sql")

# Download button
st.download_button(
    label="⬇️ Download SQL Script",
    data=sql_script,
    file_name="repair.sql",
    mime="text/plain"
)

st.divider()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.caption("Built with Streamlit + DuckDB · BrightLife Care Data Engineering Assignment")
