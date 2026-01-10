import sqlite3
import os

# Database file path - adjusting for running from root
DB_PATH = "./careerdev.db"

def add_columns():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("subscription_status", "TEXT DEFAULT 'free'"),
        ("subscription_end_date", "DATETIME"),
        ("is_recurring", "BOOLEAN DEFAULT 0"),
        ("stripe_customer_id", "TEXT")
    ]

    for col_name, col_type in columns_to_add:
        try:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Column {col_name} added successfully.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    add_columns()
