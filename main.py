import asyncio
import logging
import os
import signal
import threading
import time
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# ── Health Server (keeps Render alive) ─────────────────────────────────────────
health_app = Flask(__name__)

@health_app.route("/")
@health_app.route("/health")
def health():
    return "Bot is running! ✅", 200

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Health server starting on port {port}")
    health_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

from config import (
    TOKEN,
    ADMIN_ID,
    CHANNEL_ID,
    PRICING_PLANS,
    SUPPORT_USERNAME,
    DEMO_LINK_1,
    DEMO_LINK_2,
    DEMO_LINK_3,
    DEMO_LINK_4,
    BOT_USERNAME,
)
from utils.messages import (
    WELCOME_TEXT,
    DEMO_MENU_TEXT,
    FAQ_ITEMS,
    BRAND_FOOTER,
)
from services.database import init_db
from services.user_service import (
    register_user,
    update_last_seen,
    log_interaction,
    update_selected_plan,
    get_user_status,
    approve_user_payment,
    get_pending_payments,
    get_stats,
    get_status_counts,
    get_users_by_status,
    get_all_users,
    cancel_user_payment,
    has_active_purchase,
    record_stars_purchase,
    get_interaction_stats,
    ban_user,
    unban_user,
    is_banned,
    get_banned_users,
    lookup_user_by_username,
)
from services.payment_service import get_payment_instructions
from services.stars_service import send_stars_invoice, parse_payload

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Demo names (for readable logging)
DEMO_NAMES = {
    DEMO_LINK_1: "demo_1",
    DEMO_LINK_2: "demo_2",
    DEMO_LINK_3: "demo_3",
    DEMO_LINK_4: "demo_4",
}

# ── Rate Limiting ──────────────────────────────────────────────────────────
import time
_user_last_action: dict[int, float] = {}  # user_id -> last action timestamp
RATE_LIMIT_SECONDS = 1.5  # minimum seconds between button presses per user

# ── MENU HELPERS ───────────────────────────────────────────────────────────────

from utils.keyboards import get_main_menu_markup, back_to_main

# ── COMMAND HANDLERS ───────────────────────────────────────────────────────────

from handlers.commands import (
    start, admin_approve, admin_cancel_user, admin_list_pending, admin_panel,
    admin_stats, admin_users, admin_demos, admin_broadcast, admin_ban, admin_unban,
    admin_lookup, admin_refund, admin_broadcast_pending, admin_broadcast_plan
)
from handlers.messages import handle_text_message

# ── CALLBACK HANDLER ───────────────────────────────────────────────────────────

from handlers.callbacks import handle_callback
from handlers.payments import pre_checkout_query_handler, successful_payment_handler

import html
import json
import traceback

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"🚨 <b>An exception was raised while handling an update</b>\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    try:
        # Telegram max message length is 4096 characters
        for i in range(0, len(message), 4000):
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=message[i:i+4000], parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Failed to send error alert to ADMIN_ID: {e}")

# ── MAIN EXECUTION ─────────────────────────────────────────────────────────────

def main():
    """Initializes and runs the bot."""
    init_db()

    # Graceful SIGTERM shutdown — Render sends SIGTERM before restarting containers
    def _on_sigterm(signum, frame):
        logger.info("Received SIGTERM — shutting down cleanly.")
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, _on_sigterm)

    if not TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN found in .env file.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # ── Command Handlers ───────────────────────────────────
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("approve",    admin_approve))
    app.add_handler(CommandHandler("cancel",     admin_cancel_user))
    app.add_handler(CommandHandler("pending",    admin_list_pending))
    app.add_handler(CommandHandler("stats",      admin_stats))
    app.add_handler(CommandHandler("admin",      admin_panel))
    app.add_handler(CommandHandler("users",      admin_users))      # all users list
    app.add_handler(CommandHandler("demos",      admin_demos))      # demo analytics
    app.add_handler(CommandHandler("broadcast",  admin_broadcast))  # P4: broadcast
    app.add_handler(CommandHandler("broadcast_pending", admin_broadcast_pending))
    app.add_handler(CommandHandler("broadcast_plan", admin_broadcast_plan))
    app.add_handler(CommandHandler("ban",        admin_ban))        # P4: ban user
    app.add_handler(CommandHandler("unban",      admin_unban))      # P4: unban user
    app.add_handler(CommandHandler("lookup",     admin_lookup))     # P4: lookup user
    app.add_handler(CommandHandler("refund",     admin_refund))     # P4: Stars refund

    # ── Inline Button Handler ──────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ── Telegram Stars Payment Handlers ────────────────────
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # ── Text Message Handler (for TxID) ────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # ── Error Handler ──────────────────────────────────────
    app.add_error_handler(error_handler)

    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    if WEBHOOK_URL:
        PORT = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting webhook on port {PORT} at {WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=os.environ.get("WEBHOOK_SECRET", "super-secret-token"),
            webhook_url=WEBHOOK_URL
        )
    else:
        # Start health server on background thread (required for Render free tier)
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        logger.info("Health server thread started.")
        logger.info("Bot started and listening for messages (Polling)...")
        app.run_polling()

if __name__ == "__main__":
    main()
