import sqlite3
import os
from config import DB_PATH

def init_db():
    """Initializes the SQLite database with user and payment tracking."""
    # Ensure the database file's directory exists
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User and Payments Table
    # status: 'pending', 'approved', 'declined'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            selected_plan TEXT,
            payment_status TEXT DEFAULT 'none',
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_approved INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT NULL,
            referral_count INTEGER DEFAULT 0
        )
    ''')

    # Run migrations to add columns if upgrading from older schema
    _migrate(cursor)
    
    conn.commit()
    conn.close()

def _migrate(cursor):
    """Adds new columns to existing tables if they don't exist yet."""
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
    migrations = [
        ("referred_by", "INTEGER DEFAULT NULL"),
        ("referral_count", "INTEGER DEFAULT 0"),
    ]
    for col, definition in migrations:
        if col not in existing:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")

def get_db_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
