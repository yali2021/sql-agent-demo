# sql-agent-demo
A simple SQL agent that converts natural language questions into SQL, executes them on SQLite, and explains the results using an LLM.
---

## Overview

This project demonstrates how natural language can be used to query structured data.

Given a business question, the system:

- generates a SQL query  
- optionally refines the query for correctness  
- executes it on a SQLite database  
- returns the result and a brief explanation  

---

## Example Questions

- Show total revenue by product  
- Which product generated the highest revenue?  
- Show total quantity sold by category  

---

## How It Works

The application follows a simple pipeline:

1. A user enters a question in plain English  
2. The model generates a SQL query  
3. The query is reviewed for correctness  
4. The query is executed using SQLite  
5. The result is explained in plain English  

---

## Tech Stack

- Python  
- Streamlit  
- OpenAI API  
- SQLite  

---

## Limitations 

- Generated SQL may not always be accurate
- No validation layer

---

## License

MIT License

## Author

Ya
