from fastmcp import FastMCP
import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), "test.db")
cat_path = os.path.join(os.path.dirname(__file__),'categories.json')
mcp = FastMCP(name="ExpenseTracker")
def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                sub_category TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )"""
        )
init_db()

@mcp.tool()
def add_expense(amount: float, date: str, category: str, sub_category: str = "", note: str = "") -> dict:
    """Add an expense to the database."""
    with sqlite3.connect(DB) as conn:
        c = conn.execute(
            "INSERT INTO test (amount, date, category, sub_category, note) VALUES (?, ?, ?, ?, ?)",
            (amount, date, category, sub_category, note),
        )
    return {"status": "success", "id": c.lastrowid}

@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list[dict]:
    """List all expenses in the database."""
    with sqlite3.connect(DB) as conn:
        c = conn.execute("SELECT * FROM test WHERE date BETWEEN ? AND ? ORDER BY date ASC", (start_date, end_date))
        cols = c.fetchall()
    return [
        {
            "id": col[0],
            "amount": col[1],
            "date": col[2],
            "category": col[3],
            "sub_category": col[4],
            "note": col[5],
        }
        for col in cols
    ]

@mcp.tool()
def summarize_expenses(start_date: str, end_date: str, category: str = None) -> dict:
    """Summarize expenses by category."""
    with sqlite3.connect(DB) as conn:
        if category:
            c = conn.execute(
                "SELECT category, SUM(amount) FROM test WHERE date BETWEEN ? AND ? AND category = ? GROUP BY category ORDER BY category ASC",
                (start_date, end_date, category),
            )
        else:
            c = conn.execute(
                "SELECT category, SUM(amount) AS total_amount FROM test WHERE date BETWEEN ? AND ? GROUP BY category ORDER BY category ASC",
                (start_date, end_date),
            )
        
        cols = c.fetchall()
    return {col[0]: col[1] for col in cols}

@mcp.resource("test://categories", mime_type="application/json")
def get_categories():
    """Get the categories from the JSON file."""
    with open(cat_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0",port=8000)