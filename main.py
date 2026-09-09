# from fastmcp import FastMCP
# import os
# import sqlite3

# DB = os.path.join(os.path.dirname(__file__), "test.db")
# cat_path = os.path.join(os.path.dirname(__file__),'categories.json')
# mcp = FastMCP(name="ExpenseTracker")
# def init_db():
#     with sqlite3.connect(DB) as conn:
#         conn.execute(
#             """CREATE TABLE IF NOT EXISTS test (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 amount REAL NOT NULL,
#                 date TEXT NOT NULL,
#                 category TEXT NOT NULL,
#                 sub_category TEXT DEFAULT '',
#                 note TEXT DEFAULT ''
#             )"""
#         )
# init_db()

# @mcp.tool()
# def add_expense(amount: float, date: str, category: str, sub_category: str = "", note: str = "") -> dict:
#     """Add an expense to the database."""
#     with sqlite3.connect(DB) as conn:
#         c = conn.execute(
#             "INSERT INTO test (amount, date, category, sub_category, note) VALUES (?, ?, ?, ?, ?)",
#             (amount, date, category, sub_category, note),
#         )
#     return {"status": "success", "id": c.lastrowid}

# @mcp.tool()
# def list_expenses(start_date: str, end_date: str) -> list[dict]:
#     """List all expenses in the database."""
#     with sqlite3.connect(DB) as conn:
#         c = conn.execute("SELECT * FROM test WHERE date BETWEEN ? AND ? ORDER BY date ASC", (start_date, end_date))
#         cols = c.fetchall()
#     return [
#         {
#             "id": col[0],
#             "amount": col[1],
#             "date": col[2],
#             "category": col[3],
#             "sub_category": col[4],
#             "note": col[5],
#         }
#         for col in cols
#     ]

# @mcp.tool()
# def summarize_expenses(start_date: str, end_date: str, category: str = None) -> dict:
#     """Summarize expenses by category."""
#     with sqlite3.connect(DB) as conn:
#         if category:
#             c = conn.execute(
#                 "SELECT category, SUM(amount) FROM test WHERE date BETWEEN ? AND ? AND category = ? GROUP BY category ORDER BY category ASC",
#                 (start_date, end_date, category),
#             )
#         else:
#             c = conn.execute(
#                 "SELECT category, SUM(amount) AS total_amount FROM test WHERE date BETWEEN ? AND ? GROUP BY category ORDER BY category ASC",
#                 (start_date, end_date),
#             )
        
#         cols = c.fetchall()
#     return {col[0]: col[1] for col in cols}

# @mcp.resource("test://categories", mime_type="application/json")
# def get_categories():
#     """Get the categories from the JSON file."""
#     with open(cat_path, "r", encoding="utf-8") as f:
#         return f.read()

# if __name__ == "__main__":
#     mcp.run(transport="streamable-http", host="0.0.0.0",port=8000)


from fastmcp import FastMCP
import os
import sqlite3  # Changed: sqlite3 → aiosqlite
import tempfile
# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "test.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

def init_db():  # Keep as sync for initialization
    try:
        # Use synchronous sqlite3 just for initialization
        import sqlite3
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            # Test write access
            c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# Initialize database synchronously at module load
init_db()

@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):  # Changed: added async
    '''Add a new expense entry to the database.'''
    try:
        with sqlite3.connect(DB_PATH) as c:  # Changed: added async
            cur = c.execute(  # Changed: added await
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
            c.commit()  # Changed: added await
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    except Exception as e:  # Changed: simplified exception handling
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. Check file permissions."}
        return {"status": "error", "message": f"Database error: {str(e)}"}
    
@mcp.tool()
def list_expenses(start_date, end_date):  # Changed: added async
    '''List expense entries within an inclusive date range.'''
    try:
        with sqlite3.connect(DB_PATH) as c:  # Changed: added async
            cur = c.execute(  # Changed: added await
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]  # Changed: added await
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}

@mcp.tool()
def summarize(start_date, end_date, category=None):  # Changed: added async
    '''Summarize expenses by category within an inclusive date range.'''
    try:
        with sqlite3.connect(DB_PATH) as c:  # Changed: added async
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = c.execute(query, params)  # Changed: added await
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]  # Changed: added await
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}

@mcp.resource("expense:///categories", mime_type="application/json")  # Changed: expense:// → expense:///
def categories():
    try:
        # Provide default categories if file doesn't exist
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }
        
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run()