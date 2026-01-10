import sqlite3
import os

DB_FILE = "careerdev.db"

def add_phone_column():
    if not os.path.exists(DB_FILE):
        print("Database not found. Skipping migration.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Checking users table schema...")
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "phone_number" not in columns:
        print("Adding phone_number to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column phone_number already exists.")

    conn.close()

if __name__ == "__main__":
    add_phone_column()
