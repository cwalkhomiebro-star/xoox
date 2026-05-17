"""
api/webhook.py — Main bot serverless entry point for Vercel.
Telegram sends a POST to /api/webhook for every incoming update.
"""
import asyncio
import logging
import os
import sys

# Ensure the project root is on the path so all local imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, abort
from telegram import Update

from services.database import init_db
from main import build_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── One-time initialisation (runs once per Vercel cold start) ──────────────────
# A persistent event loop lets us reuse the PTB application across warm requests.
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

init_db()
_ptb = build_application()
_loop.run_until_complete(_ptb.initialize())
logger.info("Main bot PTB application initialised.")

# ── Flask WSGI app — Vercel detects the `app` variable automatically ──────────
app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "super-secret-token")


@app.route("/api/webhook", methods=["POST"])
def webhook():
    """Receive a Telegram update and process it."""
    # Validate the secret token header Telegram sends with every request
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if token != WEBHOOK_SECRET:
        logger.warning("Webhook called with invalid secret token.")
        abort(403)

    update = Update.de_json(request.get_json(force=True), _ptb.bot)
    _loop.run_until_complete(_ptb.process_update(update))
    return "OK", 200


@app.route("/")
@app.route("/health")
def health():
    """Health check endpoint."""
    return "Main bot is running ✅", 200
