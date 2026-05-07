import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    CHANNEL_ID,
    PRICING_PLANS,
)

from services.user_service import log_interaction, get_user_language
from services.stars_service import parse_payload, record_stars_purchase
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
    Fired by Telegram after a Stars payment is successfully completed.
    1. Parse and verify the payload
    2. Prevent duplicate delivery (idempotent via charge_id)
    3. Record purchase in database
    4. Generate a single-use invite link to the private channel
    5. Deliver the link to the user automatically
    6. Notify admin of the Stars sale
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

    plan_info = PRICING_PLANS[plan_id]
    lang = get_user_language(user_id)
    plan_name = get_text(f"plan_{plan_id}_name", lang)

    # Record purchase (IGNORE on duplicate charge_id = safe idempotent)
    newly_approved, referred_by = record_stars_purchase(user_id, plan_id, charge_id)
    log_interaction(user_id, "payment_completed_stars", detail=plan_id)

    logger.info(
        f"Stars purchase complete: user={user_id}, plan='{plan_id}', "
        f"stars={payment.total_amount}, charge_id={charge_id}"
    )

    # Generate Single-Use Invite Link
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

    # Give referral reward
    if newly_approved and referred_by:
        try:
            ref_lang = get_user_language(referred_by)
            reward_msg = get_text("referral_reward", ref_lang)
            await context.bot.send_message(chat_id=referred_by, text=reward_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send referral reward to {referred_by}: {e}")

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
