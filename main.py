import logging
import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
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
    health_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    logger.info(f"Health server started on port {port}")

from config import (
    TOKEN,
    ADMIN_ID,
    CHANNEL_ID,
    PRICING_PLANS,
    SUPPORT_USERNAME,
    DEMO_LINK_1,
    DEMO_LINK_2,
    DEMO_LINK_3,
    WELCOME_TEXT,
    DEMO_MENU_TEXT,
    PLAN_BADGES,
    FAQ_ITEMS,
    BOT_USERNAME,
)
from services.database import init_db
from services.user_service import (
    register_user,
    update_selected_plan,
    get_user_status,
    approve_user_payment,
    get_pending_payments,
    get_stats,
    get_status_counts,
    get_users_by_status,
    cancel_user_payment,
)
from services.payment_service import get_payment_instructions

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- MENU HELPERS ---

def get_main_menu_markup():
    """Generates the main menu inline keyboard."""
    keyboard = [
        [InlineKeyboardButton("💎 Pricing Plans", callback_data="view_pricing")],
        [InlineKeyboardButton("🎬 Free Demo Previews", callback_data="view_demos")],
        [InlineKeyboardButton("👤 My Account", callback_data="view_profile")],
        [InlineKeyboardButton("🔗 Refer & Earn", callback_data="view_referral")],
        [InlineKeyboardButton("💬 Help & FAQ", callback_data="view_faq")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]])

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Professional welcome message with inline buttons."""
    user = update.effective_user

    # Handle referral: /start ref_12345678
    referred_by = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referred_by = int(arg.split("_")[1])
            except (IndexError, ValueError):
                pass

    register_user(user.id, user.username, user.full_name, referred_by=referred_by)

    reply_markup = get_main_menu_markup()
    await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup, parse_mode="HTML")

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to approve a user and generate an invite link."""
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /approve USER_ID")
        return

    try:
        user_id = int(context.args[0])
        
        # Approve in Database
        approve_user_payment(user_id)
        
        # Generate Dynamic Invite Link
        try:
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                name=f"Access for {user_id}"
            )
            link_url = invite_link.invite_link
        except Exception as e:
            logger.error(f"Error generating invite link: {e}")
            link_url = "Error generating link. Please contact admin."

        # Notify User
        success_msg = (
            "✅ <b>Congratulations! Your payment has been verified.</b>\n\n"
            "You now have access to our premium content and private group.\n\n"
            f"🔗 <b>Your Invite Link:</b> {link_url}\n"
            "<i>(Note: This link is unique and for single use only.)</i>"
        )
        await context.bot.send_message(chat_id=user_id, text=success_msg, parse_mode="HTML")
        await update.message.reply_text(f"✅ Approved user {user_id} and sent invite link.")

    except ValueError:
        await update.message.reply_text("❌ Invalid User ID. Please provide a numeric ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: shows overview menu with pending/approved/cancelled counts."""
    if update.effective_user.id != ADMIN_ID:
        return

    counts = get_status_counts()
    keyboard = [
        [InlineKeyboardButton(f"⏳ Pending ({counts['pending']})", callback_data="admin_list_pending")],
        [InlineKeyboardButton(f"✅ Approved ({counts['approved']})", callback_data="admin_list_approved")],
        [InlineKeyboardButton(f"❌ Cancelled ({counts['cancelled']})", callback_data="admin_list_cancelled")],
    ]
    await update.message.reply_text(
        "🛡️ <b>Admin Panel</b>\n\nSelect a category to view users:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def admin_cancel_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /cancel USER_ID — marks a user as cancelled."""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /cancel USER_ID")
        return
    try:
        user_id = int(context.args[0])
        cancel_user_payment(user_id)
        await update.message.reply_text(f"❌ Marked user {user_id} as cancelled.")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")

async def admin_list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list users waiting for verification."""
    if update.effective_user.id != ADMIN_ID:
        return

    pending_list = get_pending_payments()
    if not pending_list:
        await update.message.reply_text("📭 No pending payments at the moment.")
        return

    report = "📋 <b>Pending Payments:</b>\n\n"
    for user in pending_list:
        report += (
            f"👤 User: @{user['username'] if user['username'] else 'N/A'}\n"
            f"🆔 ID: <code>{user['user_id']}</code>\n"
            f"💳 Plan: {user['selected_plan'].capitalize()}\n"
            f"👉 /approve {user['user_id']}\n"
            "-------------------------\n"
        )
    
    await update.message.reply_text(report, parse_mode="HTML")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command for a sales dashboard overview."""
    if update.effective_user.id != ADMIN_ID:
        return

    stats = get_stats()

    plan_lines = ""
    for plan, count in stats.get("plan_breakdown", {}).items():
        plan_info = PRICING_PLANS.get(plan, {})
        plan_name = plan_info.get("name", plan.capitalize()) if plan_info else plan.capitalize()
        plan_lines += f"  • {plan_name}: {count} user(s)\n"

    referrer_lines = ""
    for r in stats.get("top_referrers", []):
        name = f"@{r['username']}" if r['username'] else f"ID {r['user_id']}"
        referrer_lines += f"  • {name}: {r['referral_count']} referral(s)\n"

    report = (
        "📈 <b>Admin Sales Dashboard</b>\n\n"
        f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        f"✅ Approved: <b>{stats['approved_users']}</b>\n"
        f"⏳ Pending Payment: <b>{stats['pending_users']}</b>\n\n"
        f"💎 <b>Plan Breakdown (Approved):</b>\n{plan_lines or '  No approved plans yet.'}\n"
        f"🤝 <b>Top Referrers:</b>\n{referrer_lines or '  No referrals yet.'}"
    )
    await update.message.reply_text(report, parse_mode="HTML")

# --- CALLBACK HANDLERS ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline button clicks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    username = update.effective_user.username

    # ── Main Menu ──────────────────────────────────────────
    if data == "main_menu":
        await query.edit_message_text(
            WELCOME_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML"
        )

    # ── Pricing ────────────────────────────────────────────
    elif data == "view_pricing":
        keyboard = []
        for plan_id, info in PRICING_PLANS.items():
            keyboard.append([InlineKeyboardButton(
                info["label"],
                callback_data=f"buy_{plan_id}"
            )])
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])

        await query.edit_message_text(
            "💎 <b>Select Your Access Plan</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📅 <b>2025–2026 content only</b> — fresh, exclusive & HD.\n"
            "🔒 Access is delivered instantly after payment is confirmed.\n"
            "⚡ Slots are limited — secure yours before they're gone.\n\n"
            "👇 Pick a plan to get started:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── Buy a Plan ─────────────────────────────────────────
    elif data.startswith("buy_"):
        plan_id = data.replace("buy_", "")
        plan_info = PRICING_PLANS[plan_id]
        update_selected_plan(user_id, plan_id)
        instructions = get_payment_instructions(plan_id)

        keyboard = [
            [InlineKeyboardButton("✅ I've Sent the Payment", callback_data=f"confirm_payment_{plan_id}")],
            [InlineKeyboardButton("« Back to Plans", callback_data="view_pricing")]
        ]
        await query.edit_message_text(
            f"🛒 <b>{plan_info['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 {plan_info['description']}\n"
            f"💰 <b>Price: ${plan_info['price']} USDT</b>\n\n"
            f"{instructions}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── Payment Confirmation Step 1 ────────────────────────
    elif data.startswith("confirm_payment_"):
        plan_id = data.replace("confirm_payment_", "")
        plan_info = PRICING_PLANS[plan_id]
        keyboard = [
            [InlineKeyboardButton("✅ Yes — Payment Sent", callback_data=f"final_confirm_{plan_id}")],
            [InlineKeyboardButton("‹ Not Yet, Go Back", callback_data=f"buy_{plan_id}")]
        ]
        await query.edit_message_text(
            f"⚠️ <b>Final Confirmation</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Please confirm you have sent <b>${plan_info['price']} USDT (TRC20)</b> "
            f"to the correct wallet address.\n\n"
            f"<i>⚡ Once confirmed, your access will be processed and delivered shortly.</i>\n"
            f"<i>⚠️ False confirmations will result in account restriction.</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── Payment Confirmation Step 2 ────────────────────────
    elif data.startswith("final_confirm_"):
        plan_id = data.replace("final_confirm_", "")
        await query.edit_message_text(
            "✅ <b>Payment Submitted!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 Your transaction is being verified.\n"
            "🔗 Your private access link will be sent here as soon as it's confirmed."
            " This usually takes just a few minutes.\n\n"
            "🙏 <i>Thank you — sit tight, your access is on its way!</i>",
            parse_mode="HTML"
        )
        admin_notif = (
            "🔔 <b>NEW PAYMENT — ACTION REQUIRED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💎 <b>Plan:</b> {PRICING_PLANS[plan_id]['name']}\n"
            f"💰 <b>Amount:</b> ${PRICING_PLANS[plan_id]['price']} USDT\n\n"
            f"▶️ To approve:\n<code>/approve {user_id}</code>\n"
            f"❌ To cancel:\n<code>/cancel {user_id}</code>"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notif, parse_mode="HTML")

    # ── Free Demos ─────────────────────────────────────────
    elif data == "view_demos":
        keyboard = [
            [InlineKeyboardButton("▶️ Preview #1", url=DEMO_LINK_1)],
            [InlineKeyboardButton("▶️ Preview #2", url=DEMO_LINK_2)],
            [InlineKeyboardButton("▶️ Preview #3", url=DEMO_LINK_3)],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            DEMO_MENU_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── My Profile ─────────────────────────────────────────
    elif data == "view_profile":
        status = get_user_status(user_id)
        if not status:
            text = (
                "👤 <b>My Account</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "No profile found. Please send /start to register."
            )
        else:
            plan = status.get("selected_plan") or "None"
            plan_name = PRICING_PLANS.get(plan, {}).get("name", plan.capitalize()) if plan != "None" else "—"
            payment_status = (status.get("payment_status") or "none").capitalize()
            access = "✅ Active" if status.get("is_approved") else "⏳ Pending"
            join_date = str(status.get("join_date", "Unknown"))[:10]
            referrals = status.get("referral_count", 0)
            text = (
                "👤 <b>My Account</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 <b>Plan:</b> {plan_name}\n"
                f"💳 <b>Payment:</b> {payment_status}\n"
                f"🔐 <b>Access:</b> {access}\n"
                f"📅 <b>Member Since:</b> {join_date}\n"
                f"🔗 <b>Referrals:</b> {referrals} friend(s)"
            )
        await query.edit_message_text(text, reply_markup=back_to_main(), parse_mode="HTML")

    # ── Refer & Earn ───────────────────────────────────────
    elif data == "view_referral":
        status = get_user_status(user_id)
        referral_count = status.get("referral_count", 0) if status else 0
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        text = (
            "🔗 <b>Refer & Earn</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Share your unique link with friends. Every person who joins through "
            "your link is counted as your referral and earns you rewards!\n\n"
            f"<b>Your Link:</b>\n<code>{referral_link}</code>\n\n"
            f"👥 <b>Total Referrals:</b> {referral_count} friend(s)\n\n"
            "<i>Rewards are credited automatically once referrals complete a purchase.</i>"
        )
        await query.edit_message_text(text, reply_markup=back_to_main(), parse_mode="HTML")

    # ── FAQ ────────────────────────────────────────────────
    elif data == "view_faq":
        faq_text = (
            "💬 <b>Help & FAQ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        for question, answer in FAQ_ITEMS:
            faq_text += f"<b>{question}</b>\n{answer}\n\n"
        keyboard = [
            [InlineKeyboardButton("📩 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(faq_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    # ── Admin List Views ───────────────────────────────────
    elif data in ("admin_list_pending", "admin_list_approved", "admin_list_cancelled"):
        status = data.replace("admin_list_", "")
        emoji = {"⏳": "pending", "✅": "approved", "❌": "cancelled"}
        icon = {
            "pending":   "⏳",
            "approved":  "✅",
            "cancelled": "❌",
        }.get(status, "")
        users = get_users_by_status(status)
        if not users:
            text = f"{icon} <b>No {status.capitalize()} Users</b>\n\nNothing here yet."
        else:
            text = f"{icon} <b>{status.capitalize()} Users ({len(users)})</b>\n\n"
            for u in users:
                plan = (u.get('selected_plan') or 'None').capitalize()
                joined = str(u.get('join_date', ''))[:10]
                text += (
                    f"🆔 <code>{u['user_id']}</code>\n"
                    f"💳 Plan: {plan}\n"
                    f"📅 Joined: {joined}\n"
                )
                if status == "pending":
                    text += f"✅ /approve {u['user_id']}\n"
                elif status == "approved":
                    text += f"❌ /cancel {u['user_id']}\n"
                text += "─────────────────\n"

        # Refresh button
        counts = get_status_counts()
        back_keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data=data)],
            [
                InlineKeyboardButton(f"⏳ Pending ({counts['pending']})", callback_data="admin_list_pending"),
                InlineKeyboardButton(f"✅ Approved ({counts['approved']})", callback_data="admin_list_approved"),
                InlineKeyboardButton(f"❌ Cancelled ({counts['cancelled']})", callback_data="admin_list_cancelled"),
            ],
        ]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML"
        )

# --- MAIN EXECUTION ---

def main():
    """Initializes and runs the bot."""
    init_db()

    if not TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN found in .env file.")
        return

    # Start health server on background thread (required for Render free tier)
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health server thread started.")

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("cancel", admin_cancel_user))
    app.add_handler(CommandHandler("pending", admin_list_pending))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Bot started and listening for messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
