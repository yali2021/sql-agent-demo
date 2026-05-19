import os
import sqlite3

import pandas as pd
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "sales.db"

SCHEMA = """
Table name: sales

Columns:
- id (INTEGER)
- order_date (TEXT)
- product_name (TEXT)
- category (TEXT)
- quantity (INTEGER)
- revenue (REAL)
"""


def clean_sql(sql_text: str) -> str:
    return sql_text.replace("```sql", "").replace("```", "").strip()


def generate_sql(question: str) -> str:
    prompt = f"""
You are a helpful data analyst.

Convert the user's business question into a valid SQLite SQL query.

Rules:
- Only return raw SQL
- Do not include explanations
- Do not use markdown
- Do not include ``` or code blocks
- Use only the table and columns provided
- The database is SQLite

Schema:
{SCHEMA}

User question:
{question}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    sql_query = response.choices[0].message.content

    if not sql_query:
        raise ValueError("Model returned empty SQL.")

    return clean_sql(sql_query)


def review_sql(question: str, sql_query: str) -> str:
    prompt = f"""
You are a senior analytics engineer reviewing a SQL query.

Your task:
Review the SQL query and correct it if needed.

Rules:
- Return only raw SQL
- Do not use markdown
- Do not include explanations
- Keep the query valid for SQLite
- Use only the provided schema
- Make sure the SQL answers the business question correctly
- If the query is already correct, return it unchanged
- Pay special attention to semantic correctness, not just syntax

Important review rules:
- If the question asks for the highest, top, lowest, or bottom item by a metric,
  return both the item and the metric value
- If the question is about which product generated the highest revenue,
  aggregate revenue by product using SUM(revenue)
- When ranking aggregated revenue, include SUM(revenue) AS total_revenue in the SELECT clause

Schema:
{SCHEMA}

User question:
{question}

SQL query to review:
{sql_query}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    reviewed_sql = response.choices[0].message.content

    if not reviewed_sql:
        raise ValueError("Model returned empty reviewed SQL.")

    return clean_sql(reviewed_sql)


def run_sql(sql_query: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        # Column names come from the SELECT clause (e.g. product_name, total_revenue)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        return rows, columns
    finally:
        conn.close()


def display_query_results(rows, columns):
    """Turn SQL rows into a table and optionally a simple bar chart."""
    if not rows:
        st.text("No rows returned.")
        return

    # pandas DataFrame = spreadsheet-style table for st.dataframe()
    if not columns:
        columns = [f"column_{i}" for i in range(len(rows[0]))]
    df = pd.DataFrame(rows, columns=columns)

    st.dataframe(df, use_container_width=True)

    # Bar chart: need at least one label column (text) and one number column
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    num_cols = df.select_dtypes(include="number").columns.tolist()

    if text_cols and num_cols:
        category_col = text_cols[0]   # e.g. product_name or category
        value_col = num_cols[0]       # e.g. total_revenue or quantity
        st.subheader("Chart")
        # Streamlit bar chart: category names on the x-axis, numeric values as bar height
        chart_data = df.set_index(category_col)[value_col]
        st.bar_chart(chart_data)


def explain(question: str, sql_query: str, rows) -> str:
    prompt = f"""
You are a business analyst.

A user asked:
{question}

The SQL query used was:
{sql_query}

The SQL query returned these results:
{rows}

Write a short, clear business explanation in English.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    explanation = response.choices[0].message.content

    if not explanation:
        raise ValueError("Model returned empty explanation.")

    return explanation.strip()


def master_agent(question: str) -> str:
    q = question.lower()
    schema_terms = (
        "column", "columns", "field", "fields", "schema",
        "dataset", "table structure",
    )
    if any(term in q for term in schema_terms):
        return "schema"
    return "sql"


SALES_COLUMNS = [
    "id (INTEGER)",
    "order_date (TEXT)",
    "product_name (TEXT)",
    "category (TEXT)",
    "quantity (INTEGER)",
    "revenue (REAL)",
]


st.set_page_config(page_title="AI SQL Agent Demo", page_icon="📊")

st.title("📊 AI SQL Agent Demo")

st.markdown("""
**Dataset Overview**

Table: sales

Columns:
- product_name
- category
- quantity
- revenue
""")
st.markdown("**Click an example to get started:**")
q1 = "Show total revenue by product"
q2 = "Which product generated the highest revenue?"
q3 = "Show total quantity sold by category"

if st.button(q1):
    st.session_state["question"] = q1

if st.button(q2):
    st.session_state["question"] = q2

if st.button(q3):
    st.session_state["question"] = q3

st.markdown("### Ask a question")

question = st.text_input(
    "",
    value=st.session_state.get("question", ""),
    placeholder="e.g. Which product generated the highest revenue?"
)

result_area = st.empty()

if question:
    result_area.empty()

    with result_area.container():
        try:
            st.write("Step 1: Master agent routing the question...")
            intent = master_agent(question)
            if intent == "schema":
                st.subheader("Dataset schema")
                st.markdown("**Table:** `sales`")
                st.markdown("**Available columns:**")
                for col in SALES_COLUMNS:
                    st.write(f"- {col}")
            elif intent == "sql":
                st.write("Step 2: Generating SQL")
                with st.spinner("Generating SQL..."):
                    sql1 = generate_sql(question)

                st.subheader("Initial SQL")
                st.code(sql1, language="sql")

                st.write("Step 3: Reviewing SQL")
                with st.spinner("Reviewing SQL..."):
                    sql2 = review_sql(question, sql1)

                st.subheader("Reviewed SQL")
                st.code(sql2, language="sql")

                st.write("Step 4: Executing SQL")
                with st.spinner("Executing SQL..."):
                    rows, columns = run_sql(sql2)

                st.subheader("Query Results")
                display_query_results(rows, columns)

                st.write("Step 5: Generating explanation")
                with st.spinner("Generating explanation..."):
                    explanation = explain(question, sql2, rows)

                st.subheader("Explanation")
                st.write(explanation)

        except Exception as e:
            st.error(f"Error: {str(e)}")