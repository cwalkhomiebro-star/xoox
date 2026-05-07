import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    CHANNEL_ID,
    PRICING_PLANS,
)
from utils.keyboards import get_main_menu_markup
from utils.i18n import get_text

# Brand Footer is appended locally now
BRAND_FOOTER = "\n\n<i>— 🌟 9-17 —</i>"

from services.user_service import (
    register_user,
    log_interaction,
    approve_user_payment,
    cancel_user_payment,
    get_pending_payments,
    get_status_counts,
    get_stats,
    get_all_users,
    get_interaction_stats,
    ban_user,
    unban_user,
    is_banned,
    get_user_status,
    lookup_user_by_username,
    get_user_language,
)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with inline buttons. Supports deep links for referrals and direct plan access."""
    user = update.effective_user

    # Ban gate — silently ignore banned users
    if is_banned(user.id):
        return

    referred_by = None
    deep_plan = None

    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referred_by = int(arg.split("_")[1])
            except (IndexError, ValueError):
                pass
        elif arg.startswith("plan_"):
            # Deep link: /start plan_starter  → go straight to that plan
            deep_plan = arg.replace("plan_", "")
            if deep_plan not in PRICING_PLANS:
                deep_plan = None

    lang = update.effective_user.language_code or "en"
    # Basic normalization (e.g., 'es-ES' -> 'es')
    lang = lang.split('-')[0]
    if lang not in ["en", "es"]:
        lang = "en"
        
    register_user(user.id, user.username, user.full_name, referred_by=referred_by, language_code=lang)
    log_interaction(user.id, "start")

    welcome_text = get_text("welcome_text", lang)

    if deep_plan:
        # Send welcome first, then simulate clicking into that plan
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu_markup(lang), parse_mode="HTML")
        plan_info = PRICING_PLANS[deep_plan]
        log_interaction(user.id, "view_plan", detail=deep_plan)
        
        plan_name = get_text(f"plan_{deep_plan}_name", lang)
        plan_desc = get_text(f"plan_{deep_plan}_desc", lang)
        
        keyboard = [
            [InlineKeyboardButton(get_text("btn_pay_crypto", lang), callback_data=f"pay_crypto_{deep_plan}")],
            [InlineKeyboardButton(get_text("btn_pay_stars", lang), callback_data=f"pay_stars_{deep_plan}")],
            [InlineKeyboardButton(get_text("btn_back_plans", lang), callback_data="view_pricing")],
        ]
        
        plan_text = get_text("plan_details", lang, 
                             plan_name=plan_name, 
                             description=plan_desc, 
                             price=plan_info['price'], 
                             stars_price=f"{plan_info['stars_price']:,}", 
                             upgrade_note="")
                             
        await update.message.reply_text(
            plan_text + BRAND_FOOTER,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    reply_markup = get_main_menu_markup(lang)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")


async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to approve a user and generate an invite link."""
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /approve USER_ID")
        return

    try:
        user_id = int(context.args[0])
        newly_approved, referred_by = approve_user_payment(user_id)

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

        success_msg = (
            "✅ <b>Congratulations! Your payment has been verified.</b>\n\n"
            "You now have access to our premium content and private group.\n\n"
            f"🔗 <b>Your Invite Link:</b> {link_url}\n"
            "<i>(Note: This link is unique and for single use only.)</i>"
        )
        approve_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="main_menu")]])
        await context.bot.send_message(chat_id=user_id, text=success_msg, parse_mode="HTML", reply_markup=approve_kb)
        await update.message.reply_text(f"✅ Approved user {user_id} and sent invite link.")

        # Give referral reward
        if newly_approved and referred_by:
            try:
                reward_msg = (
                    f"🎉 <b>Referral Reward!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Someone you referred just completed a purchase!\n"
                    f"A reward will be credited to your account shortly."
                )
                await context.bot.send_message(chat_id=referred_by, text=reward_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send referral reward to {referred_by}: {e}")

    except ValueError:
        await update.message.reply_text("❌ Invalid User ID. Please provide a numeric ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

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

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: full analytics dashboard."""
    if update.effective_user.id != ADMIN_ID:
        return

    stats = get_stats()

    # ── Conversion Rate ────────────────────────────────────
    total = stats['total_users']
    approved = stats['approved_users']
    conv_rate = f"{(approved / total * 100):.1f}%" if total > 0 else "N/A"

    # ── Plan breakdown ─────────────────────────────────────
    plan_lines = ""
    for plan, count in stats.get("plan_breakdown", {}).items():
        plan_info = PRICING_PLANS.get(plan, {})
        plan_name = plan_info.get("name", plan.capitalize()) if plan_info else plan.capitalize()
        plan_lines += f"  • {plan_name}: {count} user(s)\n"

    # ── Revenue estimate ──────────────────────────────────
    total_revenue = 0
    for plan, count in stats.get("plan_breakdown", {}).items():
        price = PRICING_PLANS.get(plan, {}).get("price", 0)
        total_revenue += price * count

    # ── Demo views ────────────────────────────────────────
    demo_views = stats.get("demo_views", {})
    demo_lines = ""
    for key, label in [("demo_1", "Preview #1"), ("demo_2", "Preview #2"), ("demo_3", "Preview #3"), ("demo_4", "Preview #4")]:
        count = demo_views.get(key, 0)
        demo_lines += f"  • {label}: {count} click(s)\n"

    # ── Referrers ─────────────────────────────────────────
    referrer_lines = ""
    for r in stats.get("top_referrers", []):
        name = f"@{r['username']}" if r['username'] else f"ID {r['user_id']}"
        referrer_lines += f"  • {name}: {r['referral_count']} referral(s)\n"

    # ── Funnel ────────────────────────────────────────────
    viewed_pricing   = stats.get("viewed_pricing", 0)
    clicked_plan     = stats.get("clicked_plan", 0)
    submitted        = stats.get("submitted_payment", 0)

    report = (
        "📈 <b>Admin Sales Dashboard</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {total}\n"
        f"📅 <b>New Today:</b> {stats['new_today']}  |  <b>This Week:</b> {stats['new_week']}\n\n"
        f"✅ <b>Approved:</b> {approved}\n"
        f"⏳ <b>Pending:</b> {stats['pending_users']}\n"
        f"💰 <b>Est. Revenue:</b> ${total_revenue} USDT\n\n"
        f"📊 <b>Funnel:</b>\n"
        f"  • Viewed Pricing: {viewed_pricing}\n"
        f"  • Clicked a Plan: {clicked_plan}\n"
        f"  • Submitted Payment: {submitted}\n"
        f"  → <b>Conversion Rate:</b> {conv_rate}\n\n"
        f"🎬 <b>Demo Views:</b>\n{demo_lines or '  No demo clicks yet.'}\n"
        f"💎 <b>Plan Breakdown (Approved):</b>\n{plan_lines or '  No approved plans yet.'}\n"
        f"🤝 <b>Top Referrers:</b>\n{referrer_lines or '  No referrals yet.'}"
    )
    await update.message.reply_text(report, parse_mode="HTML")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: lists ALL registered users with join date, status, last seen."""
    if update.effective_user.id != ADMIN_ID:
        return

    # Support pagination: /users 2  → page 2
    page = 1
    if context.args:
        try:
            page = max(1, int(context.args[0]))
        except ValueError:
            pass

    page_size = 20
    offset = (page - 1) * page_size
    users, total = get_all_users(limit=page_size, offset=offset)
    total_pages = max(1, -(-total // page_size))  # ceiling division

    if not users:
        await update.message.reply_text("📭 No users registered yet.")
        return

    status_icon = {
        "approved":  "✅",
        "pending":   "⏳",
        "cancelled": "❌",
        "none":      "👤",
    }

    lines = f"👥 <b>All Users — Page {page}/{total_pages} ({total} total)</b>\n"
    lines += "━━━━━━━━━━━━━━━━━━━━\n\n"

    for u in users:
        icon = status_icon.get(u.get("payment_status", "none"), "👤")
        uname = f"@{u['username']}" if u.get("username") else f"#{u['user_id']}"
        joined = str(u.get("join_date", ""))[:10]
        last   = str(u.get("last_seen", ""))[:10]
        plan   = (u.get("selected_plan") or "—").capitalize()
        lines += (
            f"{icon} <code>{u['user_id']}</code> {uname}\n"
            f"   📅 Joined: {joined}  |  👁 Last: {last}\n"
            f"   💳 {plan}\n"
        )

    if total_pages > 1:
        lines += f"\n📄 Use <code>/users {page + 1}</code> for next page." if page < total_pages else ""

    await update.message.reply_text(lines, parse_mode="HTML")

async def admin_demos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: shows demo view statistics."""
    if update.effective_user.id != ADMIN_ID:
        return

    stats = get_interaction_stats()

    # Build demo-specific view
    demo_counts = {"demo_1": 0, "demo_2": 0, "demo_3": 0, "demo_4": 0}
    total_demo_section = 0

    for row in stats:
        if row["action"] == "view_demo" and row["detail"] in demo_counts:
            demo_counts[row["detail"]] = row["cnt"]
        if row["action"] == "view_demos":
            total_demo_section = row["cnt"]

    total_clicks = sum(demo_counts.values())
    bar_max = max(demo_counts.values()) if max(demo_counts.values()) > 0 else 1

    def bar(count):
        filled = round((count / bar_max) * 10)
        return "█" * filled + "░" * (10 - filled)

    report = (
        "🎬 <b>Demo Analytics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👁 <b>Demo Section Opens:</b> {total_demo_section}\n"
        f"🖱 <b>Total Demo Clicks:</b> {total_clicks}\n\n"
        f"<b>Preview #1:</b> {demo_counts['demo_1']} click(s)\n"
        f"<code>{bar(demo_counts['demo_1'])}</code>\n\n"
        f"<b>Preview #2:</b> {demo_counts['demo_2']} click(s)\n"
        f"<code>{bar(demo_counts['demo_2'])}</code>\n\n"
        f"<b>Preview #3:</b> {demo_counts['demo_3']} click(s)\n"
        f"<code>{bar(demo_counts['demo_3'])}</code>\n\n"
        f"<b>Preview #4:</b> {demo_counts['demo_4']} click(s)\n"
        f"<code>{bar(demo_counts['demo_4'])}</code>\n\n"
    )

    # Which demo converts best?
    top_demo = max(demo_counts, key=demo_counts.get)
    top_label = {"demo_1": "Preview #1", "demo_2": "Preview #2", "demo_3": "Preview #3", "demo_4": "Preview #4"}.get(top_demo, top_demo)
    if total_clicks > 0:
        report += f"🏆 <b>Most Clicked:</b> {top_label}"

    await update.message.reply_text(report, parse_mode="HTML")

# ── NEW ADMIN COMMANDS ─────────────────────────────────────────────────────────

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast MESSAGE — sends a message to every registered user."""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast Your message here")
        return

    message_text = " ".join(context.args)
    users, total = get_all_users(limit=100000, offset=0)

    sent, failed = 0, 0
    status_msg = await update.message.reply_text(f"📡 Broadcasting to {total} users...")

    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 <b>Announcement</b>\n\n{message_text}" + BRAND_FOOTER,
                parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.05)  # ~20 msg/s — safe under Telegram flood limits
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Broadcast complete!</b>\n\n"
        f"📨 Sent: {sent}\n❌ Failed (blocked/deleted): {failed}",
        parse_mode="HTML"
    )

async def admin_broadcast_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast_pending MESSAGE — sends a message to all users with pending payments."""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast_pending Your message here")
        return

    message_text = " ".join(context.args)
    users = get_pending_payments()
    
    if not users:
        await update.message.reply_text("📭 No pending payments to broadcast to.")
        return

    sent, failed = 0, 0
    status_msg = await update.message.reply_text(f"📡 Broadcasting to {len(users)} pending users...")

    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 <b>Reminder</b>\n\n{message_text}" + BRAND_FOOTER,
                parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Broadcast complete!</b>\n\n"
        f"📨 Sent: {sent}\n❌ Failed: {failed}",
        parse_mode="HTML"
    )

async def admin_broadcast_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast_plan PLAN_ID MESSAGE — sends a message to all approved users on a specific plan."""
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /broadcast_plan PLAN_ID Your message here")
        return

    plan_id = context.args[0]
    if plan_id not in PRICING_PLANS:
        valid_plans = ", ".join(PRICING_PLANS.keys())
        await update.message.reply_text(f"❌ Invalid plan. Available plans: {valid_plans}")
        return

    message_text = " ".join(context.args[1:])
    all_users, _ = get_all_users(limit=100000, offset=0)
    target_users = [u for u in all_users if u.get("is_approved") and u.get("selected_plan") == plan_id]

    if not target_users:
        await update.message.reply_text(f"📭 No approved users found for plan '{plan_id}'.")
        return

    sent, failed = 0, 0
    status_msg = await update.message.reply_text(f"📡 Broadcasting to {len(target_users)} users on plan {plan_id}...")

    for u in target_users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 <b>Update for {PRICING_PLANS[plan_id]['name']} members</b>\n\n{message_text}" + BRAND_FOOTER,
                parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Broadcast complete!</b>\n\n"
        f"📨 Sent: {sent}\n❌ Failed: {failed}",
        parse_mode="HTML"
    )

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ban USER_ID [reason] — bans a user from using the bot."""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /ban USER_ID [reason]")
        return
    try:
        user_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
        ban_user(user_id, reason)
        reason_text = f" Reason: {reason}" if reason else ""
        await update.message.reply_text(f"🚫 User <code>{user_id}</code> has been banned.{reason_text}", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unban USER_ID — removes a ban."""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /unban USER_ID")
        return
    try:
        user_id = int(context.args[0])
        unban_user(user_id)
        await update.message.reply_text(f"✅ User <code>{user_id}</code> has been unbanned.", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")

async def admin_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/lookup @username — quick user search by Telegram username."""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /lookup @username")
        return
    arg = context.args[0].lstrip("@")
    # Support both @username and numeric user_id lookups
    if arg.isdigit():
        user = get_user_status(int(arg))
        display_label = f"ID {arg}"
    else:
        user = lookup_user_by_username(arg)
        display_label = f"@{arg}"
    if not user:
        await update.message.reply_text(f"❌ No user found for {display_label}")
        return
    status_icon = {"approved": "✅", "pending": "⏳", "cancelled": "❌"}.get(user.get("payment_status", "none"), "👤")
    plan = PRICING_PLANS.get(user.get("selected_plan", ""), {}).get("name", "—") or "—"
    joined = str(user.get("join_date", ""))[:10]
    last = str(user.get("last_seen", ""))[:10]
    text = (
        f"🔍 <b>User Lookup: {display_label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Name: {user.get('full_name', 'N/A')}\n"
        f"{status_icon} Status: {(user.get('payment_status') or 'none').capitalize()}\n"
        f"💎 Plan: {plan}\n"
        f"📅 Joined: {joined}  |  👁 Last seen: {last}\n"
        f"🔗 Referrals: {user.get('referral_count', 0)}\n\n"
        f"✅ /approve {user['user_id']}\n"
        f"❌ /cancel {user['user_id']}\n"
        f"🚫 /ban {user['user_id']}"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def admin_refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/refund USER_ID CHARGE_ID — issues a Stars refund via Telegram API."""
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /refund USER_ID TELEGRAM_CHARGE_ID")
        return
    try:
        user_id = int(context.args[0])
        charge_id = context.args[1]
        await context.bot.refund_star_payment(user_id=user_id, telegram_payment_charge_id=charge_id)
        await update.message.reply_text(
            f"✅ Stars refund issued to user <code>{user_id}</code> for charge <code>{charge_id}</code>.",
            parse_mode="HTML"
        )
        logger.info(f"Admin issued Stars refund: user={user_id}, charge={charge_id}")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Refund failed: {e}")
