import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    CHANNEL_ID,
    PRICING_PLANS,
    STAR_PACKAGES,
)

from services.user_service import log_interaction, get_user_language, record_stars_purchase, admin_gift_stars, record_package_purchase
from services.stars_service import parse_payload
from utils.i18n import get_text

logger = logging.getLogger(__name__)

async def pre_checkout_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    REQUIRED by Telegram: must answer every pre_checkout_query within 10 seconds.
    Answer OK to allow the payment to proceed.
    """
    query = update.pre_checkout_query
    plan_id, user_id = parse_payload(query.invoice_payload)

    if plan_id is None:
        logger.warning(f"pre_checkout_query: invalid payload '{query.invoice_payload}'")
        await query.answer(ok=False, error_message="Invalid order. Please try again.")
        return

    await query.answer(ok=True)
    logger.info(f"pre_checkout_query answered OK for user {user_id}, plan '{plan_id}'")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fired by Telegram after a Stars payment is completed.
    - Star top-up packages → credit internal stars balance
    - Legacy content plans  → generate invite link (backward compat)
    """
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    charge_id = payment.telegram_payment_charge_id

    plan_id, payload_user_id = parse_payload(payment.invoice_payload)

    if plan_id is None or payload_user_id != user_id:
        logger.error(
            f"successful_payment: invalid payload '{payment.invoice_payload}' "
            f"from user {user_id}"
        )
        await update.message.reply_text(
            "⚠️ Payment recorded but payload mismatch. Please contact support.",
            parse_mode="HTML"
        )
        return

    lang = get_user_language(user_id)

    # ── Star Top-Up Package ────────────────────────────────────────────────────
    if plan_id in STAR_PACKAGES:
        pkg = STAR_PACKAGES[plan_id]
        credited = pkg["stars_credited"]
        bonus    = pkg["bonus"]

        admin_gift_stars(user_id, credited, source=f"purchase_{plan_id}")
        log_interaction(user_id, "stars_topup", detail=f"{plan_id}:{credited}")
        record_package_purchase(user_id, plan_id, 'stars', charge_id)

        logger.info(
            f"Star top-up complete: user={user_id}, pkg='{plan_id}', "
            f"paid={payment.total_amount}, credited={credited}, charge={charge_id}"
        )

        bonus_text = f" (+{bonus} bonus)" if bonus > 0 else ""
        success_msg = (
            f"✅ <b>Stars Added!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💫 <b>+{credited} ⭐</b> have been added to your balance{bonus_text}.\n\n"
            f"<i>Go watch some previews! Tap 🌟 Watch with Stars from the menu.</i>"
        )
        await update.message.reply_text(success_msg, parse_mode="HTML")

        # Admin notification
        admin_msg = (
            f"💫 <b>NEW STAR TOP-UP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>User:</b> <code>{user_id}</code>\n"
            f"📦 <b>Package:</b> {pkg['name']}\n"
            f"⭐ <b>Paid:</b> {payment.total_amount:,} Stars\n"
            f"💰 <b>Credited:</b> {credited} Stars{bonus_text}\n"
            f"🔑 <b>Charge ID:</b> <code>{charge_id}</code>"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify admin of star top-up: {e}")
        return

    # ── Legacy Content Plan ────────────────────────────────────────────────────
    plan_info = PRICING_PLANS.get(plan_id)
    if not plan_info:
        await update.message.reply_text("⚠️ Unknown plan. Please contact support.")
        return

    plan_name = get_text(f"plan_{plan_id}_name", lang)
    newly_approved, referred_by = record_stars_purchase(user_id, plan_id, charge_id)
    log_interaction(user_id, "payment_completed_stars", detail=plan_id)

    logger.info(
        f"Stars purchase complete: user={user_id}, plan='{plan_id}', "
        f"stars={payment.total_amount}, charge_id={charge_id}"
    )

    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"Stars-{plan_id}-{user_id}"
        )
        link_url = invite_link.invite_link
    except Exception as e:
        logger.error(f"Failed to create invite link for user {user_id}: {e}")
        link_url = None

    if link_url:
        success_msg = get_text("payment_confirmed_link", lang, plan_name=plan_name, link_url=link_url)
    else:
        success_msg = get_text("payment_confirmed_no_link", lang, plan_name=plan_name)

    await update.message.reply_text(success_msg, parse_mode="HTML")

    admin_msg = (
        f"⭐ <b>NEW STARS PAYMENT — AUTO-APPROVED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>User:</b> <code>{user_id}</code>\n"
        f"📦 <b>Plan:</b> {plan_info['name']}\n"
        f"⭐ <b>Stars Paid:</b> {payment.total_amount:,}\n"
        f"🔑 <b>Charge ID:</b> <code>{charge_id}</code>\n"
        f"🔗 <b>Invite Link:</b> {link_url or 'Failed — check logs'}\n\n"
        f"<i>No action needed — access delivered automatically.</i>"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to notify admin of Stars payment: {e}")
