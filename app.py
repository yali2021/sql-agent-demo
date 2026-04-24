import streamlit as st
from openai import OpenAI
import sqlite3
import os

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
        return rows
    finally:
        conn.close()


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


st.set_page_config(page_title="AI SQL Agent Demo", page_icon="📊")

st.title("📊 AI SQL Agent Demo")
st.write("Ask a question about sales data.")
st.markdown("""
**Dataset Overview**

Table: sales

Columns:
- product_name
- category
- quantity
- revenue
""")
st.markdown("### Example questions")
st.write("- Show total revenue by product")
st.write("- Which product generated the highest revenue?")
st.write("- Show total quantity sold by category")

question = st.text_input("Ask a question about sales data:")

result_area = st.empty()

if question:
    result_area.empty()

    with result_area.container():
        try:
            with st.spinner("Generating SQL..."):
                sql1 = generate_sql(question)

            st.subheader("Initial SQL")
            st.code(sql1, language="sql")

            with st.spinner("Reviewing SQL..."):
                sql2 = review_sql(question, sql1)

            st.subheader("Reviewed SQL")
            st.code(sql2, language="sql")

            with st.spinner("Executing SQL..."):
                rows = run_sql(sql2)

            st.subheader("Query Results")
            if rows:
                for row in rows:
                    st.text(" | ".join(str(item) for item in row))
            else:
                st.text("No rows returned.")

            with st.spinner("Generating explanation..."):
                explanation = explain(question, sql2, rows)

            st.subheader("Explanation")
            st.write(explanation)

        except Exception as e:
            st.error(f"Error: {str(e)}")