import logging
import os
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

from config import CASHIER_BOT_TOKEN, STAR_PACKAGES, WALLET_ADDRESS
from services.database import init_db
from services.user_service import log_interaction
from services.stars_service import send_star_package_invoice

from handlers.payments import pre_checkout_query_handler, successful_payment_handler
from handlers.commands import admin_stats

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_cashier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles deep linking: /start pay_<user_id>_<mode>"""
    args = context.args
    if not args or not args[0].startswith("pay_"):
        await update.message.reply_text(
            "👋 Welcome to the secure payment portal. Please return to the main bot and tap 'Buy Stars'."
        )
        return

    payload = args[0].replace("pay_", "")
    parts = payload.split("_")
    try:
        target_user_id = int(parts[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    is_crypto = len(parts) > 1 and parts[1] == "crypto"
    log_interaction(target_user_id, "cashier_opened")

    keyboard = []
    for pkg_id, pkg in STAR_PACKAGES.items():
        bonus_text = f" (+{pkg['bonus']} bonus)" if pkg['bonus'] > 0 else ""
        crypto_price = pkg.get("crypto_usd", pkg["usd"])
        
        if is_crypto:
            # Crypto path: crypto first, stars in ()
            label = f"{pkg['name']}: {crypto_price} USDT ({pkg['stars_paid']} ⭐){bonus_text}"
            callback_data = f"buy_crypto_{pkg_id}_{target_user_id}"
        else:
            # Stars path: stars first, crypto in ()
            label = f"{pkg['name']}: {pkg['stars_paid']} ⭐ ({crypto_price} USDT){bonus_text}"
            callback_data = f"buy_stars_{pkg_id}_{target_user_id}"
            
        keyboard.append([InlineKeyboardButton(label, callback_data=callback_data)])

    if is_crypto:
        text = (
            f"🪙 <b>Secure Crypto Top-Up</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔥 <b>Crypto Exclusive: 30% OFF all packages!</b>\n"
            f"Pay with USDT (TRC20) and receive your Stars balance.\n\n"
            f"Bigger pack = more bonus ⭐ free!\n\n"
            f"<i>Choose a package to get wallet details:</i>"
        )
    else:
        text = (
            f"💫 <b>Secure Star Top-Up</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pay with Telegram Stars at standard price.\n\n"
            f"Bigger pack = more bonus ⭐ free!\n\n"
            f"<i>Choose a package below:</i>"
        )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def handle_cashier_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the package selection in the cashier bot."""
    query = update.callback_query
    data = query.data

    if data.startswith("buy_stars_"):
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
            user_id=target_user_id
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

    elif data.startswith("buy_crypto_"):
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

        context.user_data["awaiting_crypto_star_txid"] = pkg_id

        crypto_price = pkg.get("crypto_usd", pkg["usd"])
        usd_amount = crypto_price.replace("≈ ", "").replace("$", "")

        text = (
            f"🪙 <b>Crypto Payment (USDT TRC20)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💎 <b>Package:</b> {pkg['name']} ({pkg['stars_credited']} ⭐)\n"
            f"💵 <b>Amount to Send:</b> ${usd_amount} USDT  <s>{pkg['usd']}</s>  <b>(-30% crypto deal!)</b>\n\n"
            f"🏦 <b>Wallet Address (TRC20):</b>\n"
            f"<code>{WALLET_ADDRESS}</code>\n\n"
            f"⚠️ <b>Important:</b>\n"
            f"1. Send exactly <b>{usd_amount} USDT</b> on the <b>TRC20</b> network.\n"
            f"2. Wait for the transaction to confirm.\n"
            f"3. <b>Paste the Transaction ID (TxID / Hash)</b> directly into this cashier chat.\n\n"
            f"<i>Your stars will be credited as soon as we verify the transaction!</i>"
        )
        await query.edit_message_text(text, parse_mode="HTML")


async def cashier_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles TxID submission in the cashier bot."""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    crypto_star_pkg_id = context.user_data.get("awaiting_crypto_star_txid")
    if not crypto_star_pkg_id:
        return

    pkg = STAR_PACKAGES.get(crypto_star_pkg_id)
    if not pkg:
        del context.user_data["awaiting_crypto_star_txid"]
        return

    await update.message.reply_text(
        "✅ <b>TxID Received!</b>\n\nYour transaction is now pending review. Your stars will be credited once the payment is confirmed.",
        parse_mode="HTML"
    )
    del context.user_data["awaiting_crypto_star_txid"]

    from config import ADMIN_ID
    admin_notif = (
        "🔔 <b>CRYPTO PAYMENT FOR STARS (MANUAL REVIEW)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Username:</b> @{update.effective_user.username or 'N/A'}\n"
        f"📦 <b>Package:</b> {pkg['name']} ({pkg['usd']})\n"
        f"⭐ <b>Stars to Credit:</b> {pkg['stars_credited']}\n\n"
        f"🔍 <b>TxID provided:</b>\n"
        f"<code>{text}</code>\n\n"
        f"▶️ <b>To approve and grant stars, copy & send:</b>\n"
        f"<code>/giftstars {user_id} {pkg['stars_credited']}</code>"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notif, parse_mode="HTML")


def build_cashier_application() -> Application:
    """
    Build the cashier PTB Application for Vercel webhook mode.
    Uses updater=None.
    """
    if not CASHIER_BOT_TOKEN:
        raise RuntimeError("CASHIER_BOT_TOKEN is not set.")
    app = ApplicationBuilder().token(CASHIER_BOT_TOKEN).updater(None).build()
    app.add_handler(CommandHandler("start", start_cashier))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(handle_cashier_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cashier_text_message))
    return app


def main():
    """Run cashier in polling mode — for LOCAL development only."""
    if not CASHIER_BOT_TOKEN:
        logger.error("No CASHIER_BOT_TOKEN found. Cashier bot will not start.")
        return
    init_db()
    app = ApplicationBuilder().token(CASHIER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cashier))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(handle_cashier_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    logger.info("Cashier Bot started in polling mode...")
    app.run_polling()


if __name__ == "__main__":
    main()
