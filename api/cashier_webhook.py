"""
api/cashier_webhook.py — Cashier bot serverless entry point for Vercel.
Telegram sends a POST to /api/cashier for every incoming update.
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, abort
from telegram import Update

from services.database import init_db
from cashier import build_cashier_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── One-time initialisation ────────────────────────────────────────────────────
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

init_db()
_ptb = build_cashier_application()
_loop.run_until_complete(_ptb.initialize())
logger.info("Cashier bot PTB application initialised.")

# ── Flask WSGI app ─────────────────────────────────────────────────────────────
app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "super-secret-token")


@app.route("/api/cashier", methods=["POST"])
def cashier_webhook():
    """Receive a Telegram update for the cashier bot."""
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if token != WEBHOOK_SECRET:
        logger.warning("Cashier webhook called with invalid secret token.")
        abort(403)

    update = Update.de_json(request.get_json(force=True), _ptb.bot)
    _loop.run_until_complete(_ptb.process_update(update))
    return "OK", 200


@app.route("/cashier-health")
def health():
    """Health check endpoint."""
    return "Cashier bot is running ✅", 200
