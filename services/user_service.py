from services.database import get_db_connection
from config import WELCOME_STARS, REFERRAL_REWARD_STARS


# ── User Registration & Updates ────────────────────────────────────────────────

def register_user(user_id, username, full_name, referred_by=None, language_code=None):
    """Registers a new user or updates their username/full_name on re-start."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by, language, stars_balance, stars_gift_from)
        VALUES (?, ?, ?, ?, ?, ?, 'the house')
    ''', (user_id, username, full_name, referred_by, language_code, WELCOME_STARS))

    is_new_user = cursor.rowcount > 0  # True only if a row was actually inserted

    # Update username/full_name in case they changed. Only set language if not already set.
    cursor.execute('''
        UPDATE users SET username = ?, full_name = ?, last_seen = CURRENT_TIMESTAMP,
                         language = COALESCE(language, ?)
        WHERE user_id = ?
    ''', (username, full_name, language_code, user_id))

    conn.commit()
    conn.close()

    # Credit referrer ONLY if this is a brand-new user registration
    rewarded_referrer = None
    if is_new_user and referred_by and referred_by != user_id:
        _increment_referral_count(referred_by)
        rewarded_referrer = referred_by

    return is_new_user, rewarded_referrer

def update_last_seen(user_id):
    """Updates the last_seen timestamp for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()

def _increment_referral_count(referrer_id):
    """Increments the referral count and awards 5 stars for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET referral_count = referral_count + 1, stars_balance = stars_balance + ? WHERE user_id = ?",
        (REFERRAL_REWARD_STARS, referrer_id,)
    )
    conn.commit()
    conn.close()

def update_selected_plan(user_id, plan_id, payment_method=None):
    """Updates the user's selected plan in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if payment_method:
        cursor.execute('''
            UPDATE users
            SET selected_plan = ?, payment_status = 'pending', payment_method = ?
            WHERE user_id = ?
        ''', (plan_id, payment_method, user_id))
    else:
        cursor.execute('''
            UPDATE users
            SET selected_plan = ?, payment_status = 'pending'
            WHERE user_id = ?
        ''', (plan_id, user_id))
    conn.commit()
    conn.close()

def update_user_language(user_id: int, language: str):
    """Updates the user's preferred language."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET language = ? WHERE user_id = ?",
        (language, user_id)
    )
    conn.commit()
    conn.close()

def get_user_language(user_id: int) -> str:
    """Gets the user's preferred language, defaulting to 'en'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row and row['language']:
        return row['language']
    return 'en'


# ── Interaction Logging ────────────────────────────────────────────────────────

def log_interaction(user_id, action, detail=None):
    """
    Logs a single user interaction to the interactions table.
    action: short string key e.g. 'start', 'view_pricing', 'view_demo'
    detail: optional extra context e.g. 'demo_1', 'pro'
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO interactions (user_id, action, detail) VALUES (?, ?, ?)",
        (user_id, action, detail)
    )
    conn.commit()
    conn.close()


# ── Read Queries ───────────────────────────────────────────────────────────────

def get_user_status(user_id):
    """Fetches the full status record for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT user_id, username, full_name, selected_plan, payment_status,
                  payment_method, is_approved, join_date, last_seen, referral_count
           FROM users WHERE user_id = ?''',
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users(limit=50, offset=0):
    """Returns all registered users ordered by join date descending."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT user_id, username, full_name, payment_status, is_approved,
                  join_date, last_seen, selected_plan
           FROM users
           ORDER BY join_date DESC
           LIMIT ? OFFSET ?''',
        (limit, offset)
    )
    rows = cursor.fetchall()
    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total

def lookup_user_by_username(username: str):
    """Finds a user by their Telegram username (without @)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT user_id, username, full_name, selected_plan, payment_status,
                  is_approved, join_date, last_seen, referral_count
           FROM users WHERE LOWER(username) = LOWER(?)
           LIMIT 1''',
        (username.lstrip('@'),)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_pending_payments():
    """Returns a list of all users with pending payments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT user_id, username, selected_plan FROM users WHERE payment_status = "pending"'
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_users_by_status(status):
    """Returns users matching the given payment_status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, full_name, selected_plan, join_date FROM users WHERE payment_status = ?",
        (status,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_status_counts():
    """Returns a dict with counts for pending, approved, and cancelled users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    counts = {
        'pending':   cursor.execute("SELECT COUNT(*) FROM users WHERE payment_status = 'pending'").fetchone()[0],
        'approved':  cursor.execute("SELECT COUNT(*) FROM users WHERE payment_status = 'approved'").fetchone()[0],
        'cancelled': cursor.execute("SELECT COUNT(*) FROM users WHERE payment_status = 'cancelled'").fetchone()[0],
    }
    conn.close()
    return counts


# ── Stats & Analytics ──────────────────────────────────────────────────────────

def get_stats():
    """Returns overall bot statistics for the admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}
    stats['total_users']    = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    stats['approved_users'] = cursor.execute("SELECT COUNT(*) FROM users WHERE is_approved = 1").fetchone()[0]
    stats['pending_users']  = cursor.execute("SELECT COUNT(*) FROM users WHERE payment_status = 'pending'").fetchone()[0]

    # New user counts
    stats['new_today'] = cursor.execute(
        "SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')"
    ).fetchone()[0]
    stats['new_week'] = cursor.execute(
        "SELECT COUNT(*) FROM users WHERE join_date >= DATETIME('now', '-7 days')"
    ).fetchone()[0]

    # Plan breakdown (approved only)
    rows = cursor.execute(
        "SELECT selected_plan, COUNT(*) as cnt FROM users WHERE is_approved = 1 GROUP BY selected_plan"
    ).fetchall()
    stats['plan_breakdown'] = {row[0]: row[1] for row in rows if row[0]}

    # Top referrers (overview/Telegram stats show only top 5, dedicated tab shows all paginated)
    rows = cursor.execute(
        "SELECT user_id, username, full_name, referral_count FROM users WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT 5"
    ).fetchall()
    stats['top_referrers'] = [dict(row) for row in rows]

    # Funnel from interactions
    stats['viewed_pricing']  = cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM interactions WHERE action = 'view_pricing'"
    ).fetchone()[0]
    stats['clicked_plan']    = cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM interactions WHERE action = 'view_plan'"
    ).fetchone()[0]
    stats['submitted_payment'] = cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM interactions WHERE action = 'payment_submitted'"
    ).fetchone()[0]

    # Demo views per demo
    demo_rows = cursor.execute(
        "SELECT detail, COUNT(*) FROM interactions WHERE action = 'view_demo' GROUP BY detail"
    ).fetchall()
    stats['demo_views'] = {row[0]: row[1] for row in demo_rows}

    conn.close()
    return stats

def get_interaction_stats():
    """Returns aggregated interaction counts by action type."""
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT action, detail, COUNT(*) as cnt FROM interactions GROUP BY action, detail ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── Payment Actions ────────────────────────────────────────────────────────────

def approve_user_payment(user_id):
    """
    Marks a user's payment as approved and inserts the purchase into the purchases table.
    Returns (newly_approved, referred_by)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_approved, referred_by, selected_plan, payment_method FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, None
    was_approved = bool(row['is_approved'])
    referred_by = row['referred_by']
    plan_id = row['selected_plan']
    pm = row['payment_method'] or 'crypto'

    cursor.execute(
        "UPDATE users SET payment_status = 'approved', is_approved = 1, payment_method = ? WHERE user_id = ?",
        (pm, user_id)
    )
    if plan_id:
        cursor.execute(
            "INSERT OR IGNORE INTO purchases (user_id, plan_id, payment_method, telegram_charge_id) VALUES (?, ?, ?, 'Manual Approval')",
            (user_id, plan_id, pm)
        )
    conn.commit()
    conn.close()
    return not was_approved, referred_by

def cancel_user_payment(user_id):
    """Marks a user's payment as cancelled."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET payment_status = 'cancelled', is_approved = 0 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


# ── Stars Payment Functions ────────────────────────────────────────────────────

def has_active_purchase(user_id: int, plan_id: str) -> bool:
    """Returns True if the user has already successfully purchased this plan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM purchases WHERE user_id = ? AND plan_id = ? LIMIT 1",
        (user_id, plan_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def record_package_purchase(user_id: int, pkg_id: str, payment_method: str, charge_id: str = None) -> None:
    """
    Records a completed Star Package purchase in the purchases table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT OR IGNORE INTO purchases (user_id, plan_id, payment_method, telegram_charge_id)
        VALUES (?, ?, ?, ?)
        ''',
        (user_id, pkg_id, payment_method, charge_id)
    )
    conn.commit()
    conn.close()


def record_stars_purchase(user_id: int, plan_id: str, telegram_charge_id: str) -> tuple[bool, int]:
    """
    Records a completed Telegram Stars purchase in the purchases table
    and marks the user as approved with payment_method = 'stars'.
    The UNIQUE constraint on telegram_charge_id prevents double-delivery.
    Returns (newly_approved, referred_by)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT is_approved, referred_by FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, None
    was_approved = bool(row['is_approved'])
    referred_by = row['referred_by']

    cursor.execute(
        '''
        INSERT OR IGNORE INTO purchases (user_id, plan_id, payment_method, telegram_charge_id)
        VALUES (?, ?, 'stars', ?)
        ''',
        (user_id, plan_id, telegram_charge_id)
    )
    cursor.execute(
        '''
        UPDATE users
        SET selected_plan = ?,
            payment_status = 'approved',
            payment_method = 'stars',
            is_approved = 1
        WHERE user_id = ?
        ''',
        (plan_id, user_id)
    )
    conn.commit()
    conn.close()
    return not was_approved, referred_by


# ── Ban / Unban Functions ───────────────────────────────────────────────────────

def ban_user(user_id: int, reason: str = None) -> None:
    """Adds a user to the banned_users table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO banned_users (user_id, reason) VALUES (?, ?)",
        (user_id, reason)
    )
    conn.commit()
    conn.close()

def unban_user(user_id: int) -> None:
    """Removes a user from the banned_users table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id: int) -> bool:
    """Returns True if the user is banned."""
    conn = get_db_connection()
    cursor = conn.cursor()
    result = cursor.execute(
        "SELECT 1 FROM banned_users WHERE user_id = ? LIMIT 1", (user_id,)
    ).fetchone()
    conn.close()
    return result is not None

def get_banned_users() -> list:
    """Returns all banned users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT user_id, reason, banned_at FROM banned_users ORDER BY banned_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Rate Limiting ──────────────────────────────────────────────────────────────


# ── Dashboard Data ─────────────────────────────────────────────────────────────

def get_user_dashboard_data(user_id: int) -> dict:
    """Returns stars balance, gift source, and referral stats for the dashboard welcome."""
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute(
        '''SELECT stars_balance, stars_gift_from, referral_count, username
           FROM users WHERE user_id = ?''',
        (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {"stars_balance": 0, "stars_gift_from": None, "referral_count": 0, "username": None}
    return {
        "stars_balance": row["stars_balance"] or 0,
        "stars_gift_from": row["stars_gift_from"],
        "referral_count": row["referral_count"] or 0,
        "username": row["username"],
    }


def admin_gift_stars(user_id: int, amount: int, source: str = "the house") -> bool:
    """
    Credits stars_balance to a user and marks the gift source label.
    Returns True if the user exists and was updated.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE users
           SET stars_balance = stars_balance + ?,
               stars_gift_from = ?
           WHERE user_id = ?''',
        (amount, source, user_id)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def deduct_stars(user_id: int, amount: int) -> bool:
    """
    Deducts `amount` stars from a user's balance atomically.
    Returns True if successful, False if the user has insufficient stars.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT stars_balance FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not row or (row["stars_balance"] or 0) < amount:
        conn.close()
        return False
    cursor.execute(
        "UPDATE users SET stars_balance = stars_balance - ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    conn.close()
    return True


def check_rate_limit(user_id: int, min_interval: float = 1.5) -> bool:
    """
    Returns True if the user is allowed to proceed, False if they are rate limited.
    Updates the last_action timestamp if allowed.
    """
    import time
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()
    
    cursor.execute("SELECT last_action FROM rate_limits WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and (now - row[0]) < min_interval:
        conn.close()
        return False
        
    cursor.execute('''
        INSERT INTO rate_limits (user_id, last_action)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_action = excluded.last_action
    ''', (user_id, now))
    conn.commit()
    conn.close()
    return True


def get_all_user_ids() -> list[int]:
    """Returns a list of all registered (non-banned) user IDs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT u.user_id FROM users u "
        "WHERE NOT EXISTS (SELECT 1 FROM banned_users b WHERE b.user_id = u.user_id)"
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


def credit_daily_stars(user_id: int, amount: int) -> None:
    """Credits the daily star bonus to a user's balance."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET stars_balance = stars_balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    conn.close()
