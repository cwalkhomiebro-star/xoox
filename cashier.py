import logging
import os
import signal
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

from config import CASHIER_BOT_TOKEN, STAR_PACKAGES
from services.database import init_db
from services.user_service import log_interaction
from services.stars_service import send_star_package_invoice

# Re-use the exact same payment handlers from the main bot
from handlers.payments import pre_checkout_query_handler, successful_payment_handler
from handlers.commands import admin_stats

# Set up basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_cashier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles deep linking: /start pay_<user_id>
    """
    args = context.args
    if not args or not args[0].startswith("pay_"):
        await update.message.reply_text("👋 Welcome to the secure payment portal. Please return to the main bot and tap 'Buy Stars'.")
        return

    # Extract user_id from pay_12345
    target_user_id_str = args[0].replace("pay_", "")
    try:
        target_user_id = int(target_user_id_str)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    # Log interaction for stats (optional, but good for tracking)
    log_interaction(target_user_id, "cashier_opened")

    keyboard = []
    for pkg_id, pkg in STAR_PACKAGES.items():
        bonus_text = f" (+{pkg['bonus']} bonus)" if pkg['bonus'] > 0 else ""
        label = f"{pkg['name']}:  {pkg['stars_paid']} ⭐ → {pkg['stars_credited']} ⭐{bonus_text}  ·  {pkg['usd']}"
        # Store target_user_id in callback data so we know who to credit!
        # Max callback_data is 64 bytes. "buy_pkg_premium_1234567890" is ~26 bytes. Safe.
        keyboard.append([InlineKeyboardButton(label, callback_data=f"buy_pkg_{pkg_id}_{target_user_id}")])

    text = (
        f"💫 <b>Secure Top-Up Portal</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Pay with Telegram Stars. Your balance on the main bot will be updated instantly.\n"
        f"Bigger pack = more bonus ⭐ free!\n\n"
        f"<i>Choose a package below:</i>"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def handle_cashier_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the package selection in the cashier bot."""
    query = update.callback_query
    data = query.data

    if data.startswith("buy_pkg_"):
        # Parse buy_pkg_premium_1234567890
        parts = data.split("_")
        if len(parts) != 4:
            await query.answer("❌ Invalid package data.", show_alert=True)
            return
            
        pkg_id = parts[2]
        target_user_id = int(parts[3])
        
        pkg = STAR_PACKAGES.get(pkg_id)
        if not pkg:
            await query.answer("❌ Package not found.", show_alert=True)
            return

        log_interaction(target_user_id, "buy_star_pkg", detail=pkg_id)

        bonus_text = f" (+{pkg['bonus']} bonus)" if pkg["bonus"] > 0 else ""

        await send_star_package_invoice(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            pkg_id=pkg_id,
            user_id=target_user_id  # Very important: pass the TARGET user_id to the invoice payload!
        )

        confirm_text = (
            f"💫 <b>{pkg['name']} Package</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pay: <b>{pkg['stars_paid']} ⭐</b>  {pkg['usd']}\n"
            f"Get: <b>{pkg['stars_credited']} ⭐</b>{bonus_text}\n\n"
            f"<i>An invoice has been sent above. Tap Pay to complete.</i>"
        )
        try:
            await query.edit_message_text(confirm_text, parse_mode="HTML")
        except Exception:
            pass


def main():
    if not CASHIER_BOT_TOKEN:
        logger.error("No CASHIER_BOT_TOKEN found in .env file. Cashier bot will not start.")
        return

    # Initialize DB to ensure it exists (though main bot likely handles this)
    init_db()

    app = ApplicationBuilder().token(CASHIER_BOT_TOKEN).build()

    # Cashier routes
    app.add_handler(CommandHandler("start", start_cashier))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(handle_cashier_callback))

    # Payment routes (reusing the exact code from main bot)
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    logger.info("Cashier Bot started and listening for payments...")
    app.run_polling()

if __name__ == "__main__":
    main()
