import sqlite3
import os

# ── Turso / libsql support ─────────────────────────────────────────────────────
# When TURSO_DATABASE_URL + TURSO_AUTH_TOKEN are set, all DB calls go to Turso.
# Otherwise falls back to local SQLite (for local development / Render).
try:
    import libsql
    _LIBSQL_AVAILABLE = True
except ImportError:
    _LIBSQL_AVAILABLE = False

from config import DB_PATH

TURSO_URL   = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def _turso_enabled() -> bool:
    return bool(TURSO_URL and TURSO_TOKEN and _LIBSQL_AVAILABLE)


class CustomRow:
    def __init__(self, cursor, tuple_row):
        self._row = tuple_row
        self._keys = [col[0] for col in cursor.description] if cursor.description else []

    def keys(self):
        return self._keys

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        try:
            return self._row[self._keys.index(key)]
        except ValueError:
            raise KeyError(key)

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)


class LibsqlCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        return CustomRow(self._cursor, row) if row else None

    def fetchall(self):
        return [CustomRow(self._cursor, row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor.fetchall():
            yield CustomRow(self._cursor, row)
            
    def execute(self, *args, **kwargs):
        self._cursor.execute(*args, **kwargs)
        return self
        
    def __getattr__(self, name):
        return getattr(self._cursor, name)


class LibsqlConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return LibsqlCursorWrapper(self._conn.cursor())

    def execute(self, *args, **kwargs):
        cursor = self.cursor()
        cursor.execute(*args, **kwargs)
        return cursor

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()
        
    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db_connection():
    """Returns a DB connection — Turso (remote) or SQLite (local)."""
    if _turso_enabled():
        conn = libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)
        return LibsqlConnectionWrapper(conn)
    elif os.getenv("VERCEL") == "1":
        raise RuntimeError(f"Vercel Deployment Error: Turso database is not configured or failed to load. _LIBSQL_AVAILABLE={_LIBSQL_AVAILABLE}, URL={bool(TURSO_URL)}, TOKEN={bool(TURSO_TOKEN)}")
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """Initializes the database tables. Safe to call multiple times (idempotent)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # ── Users & Payments Table ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            selected_plan TEXT,
            payment_status TEXT DEFAULT 'none',
            payment_method TEXT DEFAULT NULL,
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
    _migrate_existing_purchases(conn)

    # Clean up payment_method for users who got welcome stars and never paid (meaning is_approved = 0 and no purchases)
    cursor.execute("""
        UPDATE users 
        SET payment_method = NULL 
        WHERE is_approved = 0 
          AND payment_method = 'crypto'
          AND user_id NOT IN (SELECT DISTINCT user_id FROM purchases)
    """)
    conn.commit()
    conn.close()


def _migrate(cursor):
    """Adds new columns to existing tables if they don't exist yet (safe upgrade path)."""
    existing_users = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
    user_migrations = [
        ("referred_by",     "INTEGER DEFAULT NULL"),
        ("referral_count",  "INTEGER DEFAULT 0"),
        ("payment_method",  "TEXT DEFAULT NULL"),
        ("last_seen",       "TIMESTAMP"),
        ("language",        "TEXT DEFAULT NULL"),
        ("stars_balance",   "INTEGER DEFAULT 0"),
        ("stars_gift_from", "TEXT DEFAULT NULL"),
    ]
    for col, definition in user_migrations:
        if col not in existing_users:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")

    existing_demos = {row[1] for row in cursor.execute("PRAGMA table_info(demo_videos)")}
    demo_migrations = [
        ("video_type", "TEXT DEFAULT 'regular'"),
        ("duration",   "INTEGER DEFAULT NULL"),
    ]
    for col, definition in demo_migrations:
        if col not in existing_demos:
            cursor.execute(f"ALTER TABLE demo_videos ADD COLUMN {col} {definition}")


def _migrate_existing_purchases(conn):
    """Retroactively populates the purchases table with star top-ups and manual approved users."""
    cursor = conn.cursor()

    # 1. Migrate star package top-ups from interactions
    rows = cursor.execute(
        "SELECT user_id, detail, created_at FROM interactions WHERE action = 'stars_topup'"
    ).fetchall()

    for row in rows:
        user_id = row[0]
        detail = row[1]
        created_at = row[2]
        plan_id = detail.split(':')[0] if (detail and ':' in detail) else (detail or 'starter')
        # Per-user unique synthetic charge ID prevents UNIQUE constraint violation
        synthetic_id = f"migrated-topup-{user_id}-{plan_id}"
        cursor.execute(
            "INSERT OR IGNORE INTO purchases (user_id, plan_id, payment_method, telegram_charge_id, created_at) "
            "VALUES (?, ?, 'stars', ?, ?)",
            (user_id, plan_id, synthetic_id, created_at)
        )

    # 2. Migrate manual approvals (users where is_approved = 1) to purchases
    approved_users = cursor.execute(
        "SELECT user_id, selected_plan, payment_method, join_date FROM users WHERE is_approved = 1"
    ).fetchall()

    for u in approved_users:
        user_id = u[0]
        plan_id = u[1]
        pm = u[2] or 'crypto'
        join_date = u[3]
        if plan_id:
            synthetic_id = f"manual-{user_id}-{plan_id}"
            cursor.execute(
                "INSERT OR IGNORE INTO purchases (user_id, plan_id, payment_method, telegram_charge_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, plan_id, pm, synthetic_id, join_date)
            )
