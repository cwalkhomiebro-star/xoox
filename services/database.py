import sqlite3
import os
from config import DB_PATH

def init_db():
    """Initializes the SQLite database with user, payment, and interaction tracking."""
    db_dir = os.path.dirname(DB_PATH)  # empty string when DB_PATH is a bare filename
    if db_dir:  # only makedirs when there's actually a sub-directory component
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    
    # ── Users & Payments Table ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            selected_plan TEXT,
            payment_status TEXT DEFAULT 'none',
            payment_method TEXT DEFAULT 'crypto',
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_approved INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT NULL,
            referral_count INTEGER DEFAULT 0,
            language TEXT DEFAULT NULL,
            stars_balance INTEGER DEFAULT 0,
            stars_gift_from TEXT DEFAULT NULL
        )
    ''')

    # ── Purchases Table ────────────────────────────────────────────────────────
    # One row per successful purchase — enables duplicate prevention & multi-product support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id TEXT NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'stars',
            telegram_charge_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # ── Interactions Table ─────────────────────────────────────────────────────
    # Logs every meaningful action a user takes in the bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Banned Users Table ──────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
    ''')

    # ── Rate Limits Table ───────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits (
            user_id INTEGER PRIMARY KEY,
            last_action REAL DEFAULT 0
        )
    ''')

    # ── Demo Videos Table ───────────────────────────────────────────────────────
    # Stores admin-uploaded preview video file_ids with per-slot star prices
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS demo_videos (
            slot       INTEGER PRIMARY KEY,
            file_id    TEXT    NOT NULL,
            price      INTEGER NOT NULL DEFAULT 15,
            title      TEXT    DEFAULT NULL,
            video_type TEXT    DEFAULT 'regular',
            duration   INTEGER DEFAULT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    _migrate(cursor)
    conn.commit()
    conn.close()

def _migrate(cursor):
    """Adds new columns to existing tables if they don't exist yet (safe upgrade path)."""
    # Users table migrations
    existing_users = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
    user_migrations = [
        ("referred_by",       "INTEGER DEFAULT NULL"),
        ("referral_count",    "INTEGER DEFAULT 0"),
        ("payment_method",    "TEXT DEFAULT 'crypto'"),
        ("last_seen",         "TIMESTAMP"), # SQLite complains about CURRENT_TIMESTAMP in ALTER TABLE
        ("language",          "TEXT DEFAULT NULL"),
        ("stars_balance",     "INTEGER DEFAULT 0"),
        ("stars_gift_from",   "TEXT DEFAULT NULL"),
    ]
    for col, definition in user_migrations:
        if col not in existing_users:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            
    # Demo videos table migrations
    existing_demos = {row[1] for row in cursor.execute("PRAGMA table_info(demo_videos)")}
    demo_migrations = [
        ("video_type", "TEXT DEFAULT 'regular'"),
        ("duration",   "INTEGER DEFAULT NULL"),
    ]
    for col, definition in demo_migrations:
        if col not in existing_demos:
            cursor.execute(f"ALTER TABLE demo_videos ADD COLUMN {col} {definition}")


def get_db_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")  # WAL mode: crash-safe, concurrent-read-friendly
    conn.row_factory = sqlite3.Row
    return conn
