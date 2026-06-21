"""
Run this ONCE from your Flask project root folder to add
the 'bio' and 'phone' columns to the existing database.

Usage:
    python migrate_add_profile_fields.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')

def run():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at: {DB_PATH}")
        print("Make sure you run this from your Flask project root.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    try:
        cur.execute("ALTER TABLE user ADD COLUMN bio TEXT")
        print("✅ Added column: bio")
    except sqlite3.OperationalError:
        print("ℹ️  Column 'bio' already exists — skipped.")

    try:
        cur.execute("ALTER TABLE user ADD COLUMN phone VARCHAR(20)")
        print("✅ Added column: phone")
    except sqlite3.OperationalError:
        print("ℹ️  Column 'phone' already exists — skipped.")

    conn.commit()
    conn.close()
    print("\nMigration complete. You can now run your Flask app normally.")

if __name__ == '__main__':
    run()