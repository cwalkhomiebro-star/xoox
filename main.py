import asyncio
import logging
import os
import html
import json
import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

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
_user_last_action: dict[int, float] = {}
RATE_LIMIT_SECONDS = 1.5

from utils.keyboards import get_main_menu_markup, back_to_main

from handlers.commands import (
    start, admin_approve, admin_cancel_user, admin_list_pending, admin_panel,
    admin_stats, admin_users, admin_demos, admin_broadcast, admin_ban, admin_unban,
    admin_lookup, admin_refund, admin_broadcast_pending, admin_broadcast_plan,
    admin_giftstars, admin_setpreview, admin_listpreviews, handle_video_upload,
    admin_recategorize,
)
from handlers.messages import handle_text_message
from handlers.callbacks import handle_callback
from handlers.payments import pre_checkout_query_handler, successful_payment_handler


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
        for i in range(0, len(message), 4000):
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=message[i:i+4000], parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Failed to send error alert to ADMIN_ID: {e}")


def _register_handlers(app: Application) -> None:
    """Register all command, callback, and message handlers."""
    # Command Handlers
    app.add_handler(CommandHandler("start",              start))
    app.add_handler(CommandHandler("approve",            admin_approve))
    app.add_handler(CommandHandler("cancel",             admin_cancel_user))
    app.add_handler(CommandHandler("pending",            admin_list_pending))
    app.add_handler(CommandHandler("stats",              admin_stats))
    app.add_handler(CommandHandler("admin",              admin_panel))
    app.add_handler(CommandHandler("users",              admin_users))
    app.add_handler(CommandHandler("demos",              admin_demos))
    app.add_handler(CommandHandler("broadcast",          admin_broadcast))
    app.add_handler(CommandHandler("broadcast_pending",  admin_broadcast_pending))
    app.add_handler(CommandHandler("broadcast_plan",     admin_broadcast_plan))
    app.add_handler(CommandHandler("ban",                admin_ban))
    app.add_handler(CommandHandler("unban",              admin_unban))
    app.add_handler(CommandHandler("lookup",             admin_lookup))
    app.add_handler(CommandHandler("refund",             admin_refund))
    app.add_handler(CommandHandler("giftstars",          admin_giftstars))
    app.add_handler(CommandHandler("setpreview",         admin_setpreview))
    app.add_handler(CommandHandler("listpreviews",       admin_listpreviews))
    app.add_handler(CommandHandler("recategorize",       admin_recategorize))

    # Inline Button Handler
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Payment Handlers
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Text Message Handler (for TxID)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Video Upload Handler (admin preview uploads)
    app.add_handler(MessageHandler(
        (filters.VIDEO | filters.Document.VIDEO) & ~filters.COMMAND,
        handle_video_upload
    ))

    # Error Handler
    app.add_error_handler(error_handler)


def build_application() -> Application:
    """
    Build the PTB Application for Vercel webhook mode.
    Uses updater=None so PTB does NOT start its own server.
    The caller must call: await app.initialize() before processing updates.
    """
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    ptb_app = ApplicationBuilder().token(TOKEN).updater(None).build()
    _register_handlers(ptb_app)
    return ptb_app


def main():
    """Run in polling mode — for LOCAL development and Render only."""
    init_db()
    if not TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN found in .env file.")
        return
    ptb_app = ApplicationBuilder().token(TOKEN).build()
    _register_handlers(ptb_app)
    logger.info("Bot started in polling mode...")
    ptb_app.run_polling()


if __name__ == "__main__":
    main()
