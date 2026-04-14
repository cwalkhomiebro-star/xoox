from services.database import get_db_connection

def register_user(user_id, username, full_name, referred_by=None):
    """Registers a new user in the database or updates existing user info."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, full_name, referred_by))
    
    conn.commit()
    conn.close()

    # If this is a new user (INSERT happened) and there's a referrer, credit them
    if referred_by and referred_by != user_id:
        _increment_referral_count(referred_by)

def _increment_referral_count(referrer_id):
    """Increments the referral count for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
        (referrer_id,)
    )
    conn.commit()
    conn.close()

def update_selected_plan(user_id, plan_id):
    """Updates the user's selected plan in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users
        SET selected_plan = ?, payment_status = 'pending'
        WHERE user_id = ?
    ''', (plan_id, user_id))
    
    conn.commit()
    conn.close()

def get_user_status(user_id):
    """Fetches the current status and selected plan for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT selected_plan, payment_status, is_approved, join_date, referral_count FROM users WHERE user_id = ?',
        (user_id,)
    )
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None

def approve_user_payment(user_id):
    """Marks a user's payment as approved and updates status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users
        SET payment_status = 'approved', is_approved = 1
        WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()

def get_pending_payments():
    """Returns a list of all users with pending payments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, username, selected_plan FROM users WHERE payment_status = "pending"')
    rows = cursor.fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    """Returns overall bot statistics for the admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}
    stats['total_users'] = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    stats['approved_users'] = cursor.execute("SELECT COUNT(*) FROM users WHERE is_approved = 1").fetchone()[0]
    stats['pending_users'] = cursor.execute("SELECT COUNT(*) FROM users WHERE payment_status = 'pending'").fetchone()[0]

    # Plan breakdown
    rows = cursor.execute(
        "SELECT selected_plan, COUNT(*) as cnt FROM users WHERE is_approved = 1 GROUP BY selected_plan"
    ).fetchall()
    stats['plan_breakdown'] = {row[0]: row[1] for row in rows if row[0]}

    # Top referrers
    rows = cursor.execute(
        "SELECT user_id, username, referral_count FROM users WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT 5"
    ).fetchall()
    stats['top_referrers'] = [dict(row) for row in rows]

    conn.close()
    return stats

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

def get_users_by_status(status):
    """Returns a list of users matching the given payment_status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, full_name, selected_plan, join_date FROM users WHERE payment_status = ?",
        (status,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

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
