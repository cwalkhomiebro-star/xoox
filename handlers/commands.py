import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    CHANNEL_ID,
    PRICING_PLANS,
    BOT_USERNAME,
)
from utils.keyboards import get_main_menu_markup, get_buy_stars_button
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
    get_user_dashboard_data,
    admin_gift_stars,
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
        
    is_new, rewarded_referrer = register_user(user.id, user.username, user.full_name, referred_by=referred_by, language_code=lang)
    
    if rewarded_referrer:
        try:
            ref_lang = get_user_language(rewarded_referrer)
            reward_msg = get_text("referral_reward", ref_lang)
            await context.bot.send_message(chat_id=rewarded_referrer, text=reward_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send referral reward to {rewarded_referrer}: {e}")
    log_interaction(user.id, "start")

    # ── Build dynamic dashboard welcome ──────────────────────────────────────
    dash = get_user_dashboard_data(user.id)
    first_name = user.first_name or user.username or "User"
    stars = dash["stars_balance"]
    gift_from = dash["stars_gift_from"]
    ref_count = dash["referral_count"]
    ref_tag = f"ref_{user.id}"
    ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_tag}"

    # Stars line: show gift attribution if given by admin
    if gift_from and stars > 0:
        stars_line = f"🎁 <b>{stars} ⭐</b> from  {gift_from}"
    else:
        stars_line = f"⭐ <b>Stars Balance:</b>  {stars}"

    joined_line = f"<b>{ref_count}</b> friend{'s' if ref_count != 1 else ''} joined so far" if ref_count > 0 else "No one joined yet — share your link!"

    welcome_text = (
        f"👋 Hello, <b>{first_name}</b>\n"
        f"\n"
        f"{stars_line}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"🔗 <b>Invite &amp; Earn</b>\n"
        f"Tap to copy your link:\n"
        f"<code>{ref_link}</code>\n"
        f"\n"
        f"Each friend earns you <b>5 ⭐</b>  •  {joined_line}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"⬇️ <b>Pick an option below</b>"
    )

    if deep_plan:
        # Send welcome first, then simulate clicking into that plan
        reply_markup = get_main_menu_markup(lang, user_id=user.id)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
        plan_info = PRICING_PLANS[deep_plan]
        log_interaction(user.id, "view_plan", detail=deep_plan)
        
        plan_name = get_text(f"plan_{deep_plan}_name", lang)
        plan_desc = get_text(f"plan_{deep_plan}_desc", lang)
        
        keyboard = [
            [InlineKeyboardButton(get_text("btn_pay_crypto", lang), callback_data=f"pay_crypto_{deep_plan}")],
            [InlineKeyboardButton(get_text("btn_pay_stars", lang), callback_data=f"pay_stars_{deep_plan}")],
            [get_buy_stars_button(lang, user.id, text=get_text("btn_back_plans", lang))],
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

    reply_markup = get_main_menu_markup(lang, user_id=user.id)
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

    # ── Conversion Rate ─────────────────────────────────────
    total    = stats['total_users']
    approved = stats['approved_users']
    conv_rate = f"{(approved / total * 100):.1f}%" if total > 0 else "N/A"

    # ── Plan breakdown ──────────────────────────────────────
    plan_lines = ""
    for plan, count in stats.get("plan_breakdown", {}).items():
        plan_info = PRICING_PLANS.get(plan, {})
        plan_name = plan_info.get("name", plan.capitalize()) if plan_info else plan.capitalize()
        plan_lines += f"  • {plan_name}: {count} user(s)\n"

    # ── Revenue estimate ────────────────────────────────────
    total_revenue = 0
    for plan, count in stats.get("plan_breakdown", {}).items():
        price = PRICING_PLANS.get(plan, {}).get("price", 0)
        total_revenue += price * count

    # ── Interaction stats (all button clicks) ───────────────
    interaction_stats = get_interaction_stats()
    # Build a quick lookup: action -> cnt
    action_map = {row["action"]: row["cnt"] for row in interaction_stats}

    # Per-page/button clicks
    clicks_buy_stars   = action_map.get("view_pricing", 0)
    clicks_watch       = action_map.get("view_demos", 0)
    clicks_referral    = action_map.get("view_referral", 0)
    clicks_profile     = action_map.get("view_profile", 0)
    clicks_faq         = action_map.get("view_faq", 0)
    clicks_testimonials= action_map.get("view_testimonials", 0)
    clicks_buy_pkg     = action_map.get("buy_star_pkg", 0)
    clicks_start       = action_map.get("start", 0)

    # ── Demo views (category-based) ─────────────────────────
    cat_counts = {"regular": 0, "medium": 0, "premium": 0}
    total_demo_opens = clicks_watch  # same as view_demos
    for row in interaction_stats:
        if row["action"] == "view_demo":
            detail = row.get("detail") or ""
            for cat in ["regular", "medium", "premium"]:
                if detail.endswith(f"_{cat}"):
                    cat_counts[cat] += row["cnt"]
                    break
    total_watched = sum(cat_counts.values())

    # ── Referrers ───────────────────────────────────────────
    referrer_lines = ""
    for r in stats.get("top_referrers", []):
        name = f"@{r['username']}" if r['username'] else f"ID {r['user_id']}"
        referrer_lines += f"  • {name}: {r['referral_count']} referral(s)\n"

    # ── Funnel ──────────────────────────────────────────────
    viewed_pricing = stats.get("viewed_pricing", 0)
    clicked_plan   = stats.get("clicked_plan", 0)
    submitted      = stats.get("submitted_payment", 0)

    report = (
        "📈 <b>Admin Sales Dashboard</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {total}\n"
        f"📅 <b>New Today:</b> {stats['new_today']}  |  <b>This Week:</b> {stats['new_week']}\n"
        f"🔗 <b>/start opens:</b> {clicks_start}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🖱 <b>Button Clicks</b>\n"
        f"  💫 Buy Stars:       {clicks_buy_stars}\n"
        f"  📦 Bought a Pkg:    {clicks_buy_pkg}\n"
        f"  🎬 Watch Videos:    {clicks_watch}\n"
        f"  ▶️ Videos Watched:  {total_watched}  "
        f"(🎥{cat_counts['regular']} / 📺{cat_counts['medium']} / 💎{cat_counts['premium']})\n"
        f"  🔗 Referral Page:   {clicks_referral}\n"
        f"  👤 Profile:         {clicks_profile}\n"
        f"  💬 FAQ:             {clicks_faq}\n"
        f"  ⭐ Testimonials:    {clicks_testimonials}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Payment Funnel</b>\n"
        f"  • Viewed Pricing: {viewed_pricing}\n"
        f"  • Clicked a Plan: {clicked_plan}\n"
        f"  • Submitted Payment: {submitted}\n"
        f"  → <b>Conversion Rate:</b> {conv_rate}\n\n"
        f"✅ <b>Approved:</b> {approved}  |  "
        f"⏳ <b>Pending:</b> {stats['pending_users']}  |  "
        f"💰 <b>Est. Revenue:</b> ${total_revenue}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>Plan Breakdown:</b>\n{plan_lines or '  No approved plans yet.'}\n"
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
    """Admin command: shows video watch statistics by category."""
    if update.effective_user.id != ADMIN_ID:
        return

    stats = get_interaction_stats()

    # Aggregate by video type from new format: detail = demo_{slot}_{type}
    cat_counts = {"regular": 0, "medium": 0, "premium": 0}
    total_demo_section = 0

    for row in stats:
        if row["action"] == "view_demo":
            detail = row.get("detail") or ""
            for cat in ["regular", "medium", "premium"]:
                if detail.endswith(f"_{cat}"):
                    cat_counts[cat] += row["cnt"]
                    break
        if row["action"] == "view_demos":
            total_demo_section = row["cnt"]

    total_clicks = sum(cat_counts.values())
    bar_max = max(cat_counts.values()) if max(cat_counts.values()) > 0 else 1

    def bar(count):
        filled = round((count / bar_max) * 10)
        return "█" * filled + "░" * (10 - filled)

    report = (
        "🎬 <b>Video Watch Analytics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👁 <b>Watch Menu Opens:</b> {total_demo_section}\n"
        f"▶️ <b>Total Videos Watched:</b> {total_clicks}\n\n"
        f"🎥 <b>Regular (15 ⭐):</b> {cat_counts['regular']} watch(es)\n"
        f"<code>{bar(cat_counts['regular'])}</code>\n\n"
        f"📺 <b>Medium (25 ⭐):</b> {cat_counts['medium']} watch(es)\n"
        f"<code>{bar(cat_counts['medium'])}</code>\n\n"
        f"💎 <b>Premium (49 ⭐):</b> {cat_counts['premium']} watch(es)\n"
        f"<code>{bar(cat_counts['premium'])}</code>\n\n"
    )

    if total_clicks > 0:
        top_cat = max(cat_counts, key=cat_counts.get)
        emoji = {"regular": "🎥", "medium": "📺", "premium": "💎"}.get(top_cat, "")
        report += f"🏆 <b>Most Watched:</b> {emoji} {top_cat.capitalize()}"
    else:
        report += "<i>No videos watched yet.</i>"

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


async def admin_giftstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/giftstars USER_ID AMOUNT — gifts ⭐ stars to a user from the house."""
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /giftstars USER_ID AMOUNT\n\nExample: /giftstars 123456789 60")
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be a positive number.")
            return

        success = admin_gift_stars(user_id, amount, source="the house")
        if success:
            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎁 <b>You've received a gift!</b>\n\n"
                        f"⭐️ <b>{amount} Stars</b> have been added to your account from <b>the house</b>!\n\n"
                        f"Use /start to see your updated balance."
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not notify user {user_id} about gift: {e}")
            await update.message.reply_text(
                f"✅ Gifted <b>{amount} ⭐</b> to user <code>{user_id}</code> from the house.",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(f"❌ User <code>{user_id}</code> not found.", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Invalid arguments. USER_ID and AMOUNT must be numbers.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ── Preview Video Admin Commands ───────────────────────────────────────────────

from services.demo_service import set_demo_video, get_all_demo_videos, get_next_slot

async def admin_setpreview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setpreview SLOT PRICE TYPE — Admin sets a star-gated preview slot, then sends a video."""
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Usage: /setpreview SLOT PRICE TYPE\n\n"
            "Example: /setpreview 1 15 regular\n\n"
            "Types: regular, medium, premium\n\n"
            "After this command, send a video and I'll save it."
        )
        return
    try:
        slot = int(context.args[0])
        price = int(context.args[1])
        video_type = context.args[2].lower()
        if video_type not in ["regular", "medium", "premium"]:
            await update.message.reply_text("❌ TYPE must be 'regular', 'medium', or 'premium'.")
            return
            
        context.user_data["awaiting_preview"] = {"slot": slot, "price": price, "video_type": video_type}
        await update.message.reply_text(
            f"✅ Ready for {video_type.capitalize()} Video #{slot} at {price} ⭐\n\n"
            f"📹 Send me the video now."
        )
    except ValueError:
        await update.message.reply_text("❌ SLOT and PRICE must be numbers.")


async def admin_listpreviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/listpreviews — Shows all currently uploaded preview videos and their prices."""
    if update.effective_user.id != ADMIN_ID:
        return
    videos = get_all_demo_videos()
    if not videos:
        await update.message.reply_text(
            "📭 No previews uploaded yet.\n\n"
            "Use /setpreview SLOT PRICE TYPE then send a video."
        )
        return
    text = "🎬 <b>Uploaded Previews</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for v in videos:
        title = v.get("title") or f"Preview #{v['slot']}"
        video_type = v.get("video_type", "regular").capitalize()
        text += (
            f"🎞️ <b>Slot {v['slot']} ({video_type}):</b> {title} — {v['price']} ⭐\n"
            f"   Uploaded: {str(v.get('uploaded_at', ''))[:10]}\n\n"
        )
    text += "Send a video directly (no command needed) to auto-add it to the vault."
    await update.message.reply_text(text, parse_mode="HTML")


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sends any video — auto-assigns slot, auto-categorizes by duration. No /setpreview needed."""
    if update.effective_user.id != ADMIN_ID:
        return

    # Accept both proper video and video sent as document (uncompressed)
    video = update.message.video or update.message.document
    if not video:
        return

    file_id  = video.file_id
    duration = getattr(video, "duration", None)  # documents may not have duration

    # ── Auto-categorize by duration ────────────────────────────────────
    if duration is not None:
        if duration <= 60:
            video_type, price = "regular", 15
        elif duration <= 120:
            video_type, price = "medium", 25
        else:
            video_type, price = "premium", 49
        duration_note = f"🕐 <b>Duration:</b> {duration}s"
    else:
        # Fallback for uncompressed documents with no metadata
        video_type, price = "regular", 15
        duration_note = "⚠️ Duration unknown — defaulted to <b>Regular</b>"

    # ── Auto-assign next slot ───────────────────────────────────────
    slot  = get_next_slot()
    title = f"{video_type.capitalize()} Video #{slot}"

    set_demo_video(slot, file_id, price, title, video_type, duration)

    # Clear any leftover /setpreview state
    context.user_data.pop("awaiting_preview", None)

    type_emoji = {"regular": "🎥", "medium": "📺", "premium": "💎"}.get(video_type, "🎬")
    await update.message.reply_text(
        f"{type_emoji} <b>{video_type.capitalize()} Video saved as Slot #{slot}!</b>\n\n"
        f"{duration_note}\n"
        f"⭐ <b>Price:</b> {price} Stars\n\n"
        f"Users will pay <b>{price} ⭐</b> to watch this video.",
        parse_mode="HTML"
    )


async def admin_recategorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/recategorize — Re-categorizes all existing videos by their stored duration."""
    if update.effective_user.id != ADMIN_ID:
        return

    videos = get_all_demo_videos()
    if not videos:
        await update.message.reply_text("📭 No videos to recategorize.")
        return

    updated, skipped = 0, 0
    from services.demo_service import set_demo_video
    for v in videos:
        duration = v.get("duration")
        if duration is None:
            skipped += 1
            continue

        if duration <= 60:
            new_type, new_price = "regular", 15
        elif duration <= 120:
            new_type, new_price = "medium", 25
        else:
            new_type, new_price = "premium", 49

        title = f"{new_type.capitalize()} Video #{v['slot']}"
        set_demo_video(v["slot"], v["file_id"], new_price, title, new_type, duration)
        updated += 1

    await update.message.reply_text(
        f"✅ <b>Recategorization complete!</b>\n\n"
        f"🔄 Updated: {updated} video(s)\n"
        f"⏭️ Skipped (no duration stored): {skipped} video(s)\n\n"
        f"<i>Videos without duration were uploaded before auto-detection was added.\n"
        f"Re-upload them with /setpreview to auto-categorize.</i>",
        parse_mode="HTML"
    )
