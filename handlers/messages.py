import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, CHANNEL_ID, PRICING_PLANS
from services.crypto_service import verify_trc20_txid
from services.user_service import approve_user_payment, get_user_language
from utils.i18n import get_text

logger = logging.getLogger(__name__)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles plain text messages, checking for TxID input."""
    if not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    plan_id = context.user_data.get("awaiting_txid")
    if not plan_id:
        return # Ignore messages when not awaiting TxID
        
    if plan_id not in PRICING_PLANS:
        # Invalid state
        del context.user_data["awaiting_txid"]
        return
        
    lang = get_user_language(user_id)
    plan_name = get_text(f"plan_{plan_id}_name", lang)
        
    # We are awaiting a TxID! Let's verify it.
    await update.message.reply_text(get_text("tx_verifying", lang), parse_mode="HTML")
    
    # We remove the state so they can't spam it. If it fails, they can restart.
    del context.user_data["awaiting_txid"]
    
    result = verify_trc20_txid(text, plan_id)
    
    if result["status"] == "success":
        # Approve the user
        newly_approved, referred_by = approve_user_payment(user_id)
        
        try:
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                name=f"Crypto-{plan_id}-{user_id}"
            )
            link_url = invite_link.invite_link
        except Exception as e:
            logger.error(f"Error generating invite link: {e}")
            link_url = "Error generating link. Please contact admin."
            
        if link_url:
            success_msg = get_text("payment_confirmed_link", lang, plan_name=plan_name, link_url=link_url)
        else:
            success_msg = get_text("payment_confirmed_no_link", lang, plan_name=plan_name)
            
        await update.message.reply_text(success_msg, parse_mode="HTML")
        
        # Notify Admin
        admin_notif = (
            "✅ <b>AUTO-VERIFIED CRYPTO PAYMENT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💎 <b>Plan:</b> {PRICING_PLANS[plan_id]['name']}\n"
            f"💰 <b>Amount:</b> ${result['amount']} USDT\n"
            f"🔍 <b>TxID:</b> <code>{text}</code>"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notif, parse_mode="HTML")
        
    elif result["status"] == "pending":
        await update.message.reply_text(get_text("tx_pending", lang), parse_mode="HTML")
        # Notify admin for manual review
        admin_notif = (
            "🔔 <b>MANUAL REVIEW REQUIRED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💎 <b>Plan:</b> {PRICING_PLANS[plan_id]['name']}\n"
            f"🔍 <b>TxID provided:</b> <code>{text}</code>\n\n"
            f"▶️ To approve:\n<code>/approve {user_id}</code>"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notif, parse_mode="HTML")
    else:
        await update.message.reply_text(get_text("tx_failed", lang, reason=result['message']), parse_mode="HTML")
