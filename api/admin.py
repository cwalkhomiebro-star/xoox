"""
api/admin.py — Admin web dashboard for the XOOX bot.
Serves a password-protected HTML admin panel + JSON data endpoints.

Routes:
  GET  /admin             → HTML dashboard (redirects to /admin/login if not auth)
  GET  /admin/login       → Login form
  POST /admin/login       → Validate password, set session cookie
  GET  /admin/logout      → Clear session, redirect to login
  GET  /api/admin/stats   → Overview JSON
  GET  /api/admin/users   → Users list JSON (paginated, searchable)
  GET  /api/admin/buyers  → Purchases list JSON (paginated)
  GET  /api/admin/pending → Pending users JSON
  GET  /api/admin/banned  → Banned users JSON
  GET  /api/admin/videos  → Demo videos JSON
  POST /api/admin/approve → Approve a user (DB only)
  POST /api/admin/cancel  → Cancel a user
  POST /api/admin/unban   → Unban a user
"""
import os
import sys
import hmac
import hashlib
import time
import logging
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, make_response, redirect
from services.database import init_db, get_db_connection
from services.user_service import (
    get_stats,
    get_all_users,
    get_status_counts,
    get_pending_payments,
    get_banned_users,
    get_interaction_stats,
    approve_user_payment,
    cancel_user_payment,
    unban_user,
)
from services.demo_service import get_all_demo_videos
from config import PRICING_PLANS
from api.admin_template import DASHBOARD_HTML, LOGIN_HTML

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── One-time init ──────────────────────────────────────────────────────────────
init_db()

app = Flask(__name__)

DASHBOARD_SECRET = os.environ.get("ADMIN_DASHBOARD_SECRET", "xoox-admin-2025")
_COOKIE = "xoox_admin"
_TTL    = 86400  # 24 hours


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _sign(payload: str) -> str:
    return hmac.new(
        DASHBOARD_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def _make_token() -> str:
    ts  = str(int(time.time()))
    sig = _sign("admin:" + ts)
    return f"{ts}:{sig}"


def _verify_token(token: str) -> bool:
    try:
        ts, sig = token.split(":", 1)
        if int(time.time()) - int(ts) > _TTL:
            return False
        return hmac.compare_digest(sig, _sign("admin:" + ts))
    except Exception:
        return False


def _is_auth() -> bool:
    return _verify_token(request.cookies.get(_COOKIE, ""))


def _auth(fn):
    """Decorator: redirect to login if not authenticated."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_auth():
            return redirect("/admin/login")
        return fn(*args, **kwargs)
    return wrapper


def _api_auth(fn):
    """Decorator: return 401 JSON if not authenticated."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_auth():
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ── Login / Logout ─────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if hmac.compare_digest(pwd.encode(), DASHBOARD_SECRET.encode()):
            resp = make_response(redirect("/admin"))
            resp.set_cookie(
                _COOKIE, _make_token(),
                httponly=True, samesite="Lax", max_age=_TTL, secure=True
            )
            return resp
        html = LOGIN_HTML.replace(
            "##ERROR##",
            '<div class="err-box">❌ Wrong password — try again.</div>'
        )
        return html, 401

    return LOGIN_HTML.replace("##ERROR##", ""), 200


@app.route("/admin/logout")
def logout():
    resp = make_response(redirect("/admin/login"))
    resp.delete_cookie(_COOKIE)
    return resp


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/admin")
@_auth
def dashboard():
    return DASHBOARD_HTML, 200


# ── Data: Stats ────────────────────────────────────────────────────────────────

@app.route("/api/admin/stats")
@_api_auth
def api_stats():
    stats  = get_stats()
    counts = get_status_counts()
    total    = stats["total_users"]
    approved = stats["approved_users"]

    # Revenue from Stars purchases (join with PRICING_PLANS prices)
    conn = get_db_connection()
    cursor = conn.cursor()
    stars_rows = cursor.execute(
        "SELECT plan_id, COUNT(*) as cnt FROM purchases "
        "WHERE payment_method='stars' GROUP BY plan_id"
    ).fetchall()
    conn.close()

    stars_rev = sum(
        PRICING_PLANS.get(str(r["plan_id"]), {}).get("price", 0) * int(r["cnt"])
        for r in stars_rows
    )
    crypto_rev = sum(
        PRICING_PLANS.get(p, {}).get("price", 0) * c
        for p, c in stats.get("plan_breakdown", {}).items()
    )

    return jsonify({
        "total_users":    total,
        "approved":       approved,
        "pending":        counts["pending"],
        "cancelled":      counts["cancelled"],
        "new_today":      stats["new_today"],
        "new_week":       stats["new_week"],
        "conversion_rate": f"{(approved / total * 100):.1f}%" if total > 0 else "N/A",
        "total_revenue":  crypto_rev + stars_rev,
        "plan_breakdown": stats.get("plan_breakdown", {}),
        "top_referrers":  stats.get("top_referrers", []),
        "funnel": {
            "viewed_pricing": stats.get("viewed_pricing", 0),
            "clicked_plan":   stats.get("clicked_plan",   0),
            "submitted":      stats.get("submitted_payment", 0),
            "approved":       approved,
        },
    })


# ── Data: Users ────────────────────────────────────────────────────────────────

@app.route("/api/admin/users")
@_api_auth
def api_users():
    page      = max(1, int(request.args.get("page", 1)))
    search    = request.args.get("search", "").strip()
    page_size = 20
    offset    = (page - 1) * page_size

    conn   = get_db_connection()
    cursor = conn.cursor()

    base_cols = (
        "user_id, username, full_name, payment_status, is_approved, "
        "join_date, last_seen, selected_plan, stars_balance, payment_method"
    )
    if search:
        like = f"%{search}%"
        rows = cursor.execute(
            f"SELECT {base_cols} FROM users "
            "WHERE username LIKE ? OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ? "
            "ORDER BY join_date DESC LIMIT ? OFFSET ?",
            (like, like, like, page_size, offset)
        ).fetchall()
        total = cursor.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE username LIKE ? OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?",
            (like, like, like)
        ).fetchone()[0]
    else:
        rows = cursor.execute(
            f"SELECT {base_cols} FROM users ORDER BY join_date DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        ).fetchall()
        total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    conn.close()
    pages = max(1, -(-total // page_size))
    return jsonify({"users": [dict(r) for r in rows], "total": total, "pages": pages, "page": page})


# ── Data: Buyers ───────────────────────────────────────────────────────────────

@app.route("/api/admin/buyers")
@_api_auth
def api_buyers():
    page      = max(1, int(request.args.get("page", 1)))
    page_size = 25
    offset    = (page - 1) * page_size

    conn   = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT p.purchase_id, p.user_id, u.username, u.full_name, "
        "p.plan_id, p.payment_method, p.telegram_charge_id, p.created_at "
        "FROM purchases p LEFT JOIN users u ON p.user_id = u.user_id "
        "ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
        (page_size, offset)
    ).fetchall()
    total = cursor.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    conn.close()

    pages = max(1, -(-total // page_size))
    return jsonify({"buyers": [dict(r) for r in rows], "total": total, "pages": pages, "page": page})


# ── Data: Pending ──────────────────────────────────────────────────────────────

@app.route("/api/admin/pending")
@_api_auth
def api_pending():
    conn   = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT user_id, username, full_name, selected_plan, join_date, last_seen "
        "FROM users WHERE payment_status='pending' ORDER BY join_date DESC"
    ).fetchall()
    conn.close()
    return jsonify({"users": [dict(r) for r in rows]})


# ── Data: Banned ───────────────────────────────────────────────────────────────

@app.route("/api/admin/banned")
@_api_auth
def api_banned():
    return jsonify({"users": get_banned_users()})


# ── Data: Videos ───────────────────────────────────────────────────────────────

@app.route("/api/admin/videos")
@_api_auth
def api_videos():
    return jsonify({"videos": get_all_demo_videos()})


# ── Actions ────────────────────────────────────────────────────────────────────

@app.route("/api/admin/approve", methods=["POST"])
@_api_auth
def api_approve():
    data = request.get_json(force=True) or {}
    try:
        uid = int(data.get("user_id", 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid user_id"}), 400
    if not uid:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    approve_user_payment(uid)
    logger.info(f"Dashboard: approved user {uid}")
    return jsonify({"ok": True})


@app.route("/api/admin/cancel", methods=["POST"])
@_api_auth
def api_cancel():
    data = request.get_json(force=True) or {}
    try:
        uid = int(data.get("user_id", 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid user_id"}), 400
    if not uid:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    cancel_user_payment(uid)
    logger.info(f"Dashboard: cancelled user {uid}")
    return jsonify({"ok": True})


@app.route("/api/admin/unban", methods=["POST"])
@_api_auth
def api_unban():
    data = request.get_json(force=True) or {}
    try:
        uid = int(data.get("user_id", 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid user_id"}), 400
    if not uid:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    unban_user(uid)
    logger.info(f"Dashboard: unbanned user {uid}")
    return jsonify({"ok": True})
