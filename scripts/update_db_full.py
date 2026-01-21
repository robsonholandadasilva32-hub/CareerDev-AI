import sqlite3
import os

DB_FILE = "careerdev.db"

def update_schema():
    if not os.path.exists(DB_FILE):
        print("Database not found. Skipping migration.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Checking users table schema...")
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    # Define columns to add: name -> type definition
    new_columns = {
        "failed_login_attempts": "INTEGER DEFAULT 0",
        "locked_until": "DATETIME"
    }

    for col_name, col_def in new_columns.items():
        if col_name not in columns:
            print(f"Adding {col_name} to users...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
        else:
            print(f"Column {col_name} already exists.")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    update_schema()
