import time
import datetime
import logging
import urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    PRICING_PLANS,
    STAR_PACKAGES,
    SUPPORT_USERNAME,
    DEMO_LINK_1,
    DEMO_LINK_2,
    DEMO_LINK_3,
    DEMO_LINK_4,
    BOT_USERNAME,
    DEMO_STAR_PRICE,
)
from utils.i18n import get_text
from utils.keyboards import get_main_menu_markup, back_to_main, get_buy_stars_button

BRAND_FOOTER = ""

from services.user_service import (
    update_last_seen,
    log_interaction,
    update_selected_plan,
    get_user_status,
    get_users_by_status,
    get_status_counts,
    is_banned,
    check_rate_limit,
    get_user_language,
    update_user_language,
    has_active_purchase,
    get_user_dashboard_data,
    deduct_stars,
)
from services.payment_service import get_payment_instructions
from services.stars_service import send_stars_invoice, send_star_package_invoice
from services.demo_service import get_all_demo_videos, get_demo_video

logger = logging.getLogger(__name__)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline button clicks."""
    query = update.callback_query
    user_id = update.effective_user.id

    lang = get_user_language(user_id)

    # Ban gate
    if is_banned(user_id):
        await query.answer(get_text("not_authorized", lang), show_alert=True)
        return

    # Rate limiting — prevent button spam
    if not check_rate_limit(user_id, min_interval=1.5):
        await query.answer(get_text("slow_down", lang), show_alert=False)
        return

    await query.answer()

    try:
        await _handle_callback_inner(update, context)
    except Exception as e:
        logger.exception(f"handle_callback error for user {user_id}: {e}")
        try:
            await query.edit_message_text(
                get_text("something_went_wrong", lang),
                reply_markup=back_to_main(lang)
            )
        except Exception:
            pass

async def _handle_callback_inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inner handler — all business logic lives here, wrapped by handle_callback."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    username = update.effective_user.username

    lang = get_user_language(user_id)

    # Update last seen on every interaction
    update_last_seen(user_id)

    # ── Language Selection ─────────────────────────────────
    if data == "change_language":
        log_interaction(user_id, "change_language")
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="set_lang_es")],
            [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")],
        ]
        await query.edit_message_text(
            get_text("choose_language", lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    elif data.startswith("set_lang_"):
        new_lang = data.replace("set_lang_", "")
        update_user_language(user_id, new_lang)
        lang = new_lang
        # Redirect to main menu
        await query.edit_message_text(
            get_text("welcome_text", lang), 
            reply_markup=get_main_menu_markup(lang, user_id=user_id), 
            parse_mode="HTML"
        )
        return

    # ── Main Menu ──────────────────────────────────────────
    if data == "main_menu":
        dash = get_user_dashboard_data(user_id)
        first_name = update.effective_user.first_name or update.effective_user.username or "User"
        stars = dash["stars_balance"]
        gift_from = dash["stars_gift_from"]
        ref_count = dash["referral_count"]
        ref_tag = f"ref_{user_id}"
        ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_tag}"

        if gift_from and stars > 0:
            stars_line = f"🎁 <b>{stars} ⭐</b> — gifted to you by the house"
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
        
        try:
            await query.edit_message_text(
                welcome_text, reply_markup=get_main_menu_markup(lang, user_id=user_id), parse_mode="HTML"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=user_id, 
                text=welcome_text, 
                reply_markup=get_main_menu_markup(lang, user_id=user_id), 
                parse_mode="HTML"
            )

    # ── Buy Stars (Redirect to Cashier) ────────────────────
    elif data == "view_pricing":
        log_interaction(user_id, "view_pricing")
        from config import CASHIER_BOT_USERNAME
        
        if CASHIER_BOT_USERNAME == "YourCashierBotUsername":
            await query.answer("❌ Cashier bot not configured.", show_alert=True)
            return

        cashier_link = f"https://t.me/{CASHIER_BOT_USERNAME}?start=pay_{user_id}"
        
        keyboard = [
            [InlineKeyboardButton("💫 Open Secure Top-Up Portal", url=cashier_link)],
            [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")]
        ]

        text = (
            f"💫 <b>Buy Stars</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"For security and to ensure your balance is never lost, all payments are handled by our dedicated Cashier bot.\n\n"
            f"Tap the button below to top up your account securely. Your balance will update here instantly!"
        )
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")



    # ── Pay with Crypto ────────────────────────────────────
    elif data.startswith("pay_crypto_"):
        plan_id = data.replace("pay_crypto_", "")
        plan_info = PRICING_PLANS.get(plan_id)
        if not plan_info:
            await query.edit_message_text(get_text("plan_not_found", lang), reply_markup=back_to_main(lang))
            return
        log_interaction(user_id, "pay_crypto", detail=plan_id)
        update_selected_plan(user_id, plan_id)
        instructions = get_payment_instructions(plan_id, lang)

        keyboard = [
            [InlineKeyboardButton("✅ I've Sent the Payment", callback_data=f"confirm_payment_{plan_id}")],
            [InlineKeyboardButton(get_text("btn_back_plans", lang), callback_data=f"buy_{plan_id}")]
        ]
        await query.edit_message_text(
            instructions + BRAND_FOOTER,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── Payment Confirmation Step 1 (Crypto) ───────────────
    elif data.startswith("confirm_payment_"):
        plan_id = data.replace("confirm_payment_", "")
        plan_info = PRICING_PLANS.get(plan_id)
        if not plan_info:
            await query.edit_message_text(get_text("plan_not_found", lang), reply_markup=back_to_main(lang))
            return

        context.user_data["awaiting_txid"] = plan_id

        await query.edit_message_text(
            get_text("final_crypto_confirm", lang) + BRAND_FOOTER,
            parse_mode="HTML"
        )

    # ── Watch with Stars ───────────────────────────────────
    elif data == "view_demos":
        log_interaction(user_id, "view_demos")
        dash = get_user_dashboard_data(user_id)
        balance = dash["stars_balance"]

        # Fetch all videos and calculate available counts per type
        videos = get_all_demo_videos()
        real_regular = sum(1 for v in videos if v.get("video_type", "regular") == "regular")
        real_medium  = sum(1 for v in videos if v.get("video_type", "regular") == "medium")
        real_premium = sum(1 for v in videos if v.get("video_type", "regular") == "premium")

        # Display inflated "bait" counts to encourage engagement
        # Real videos are still served randomly — users just see a bigger vault
        BAIT_REGULAR = 21460
        BAIT_MEDIUM  = 12831
        BAIT_PREMIUM = 5416
        regular_count = real_regular + BAIT_REGULAR
        medium_count  = real_medium  + BAIT_MEDIUM
        premium_count = real_premium + BAIT_PREMIUM

        keyboard = []
        keyboard.append([InlineKeyboardButton(get_text("btn_watch_regular", lang), callback_data="demo_type_regular")])
        keyboard.append([InlineKeyboardButton(get_text("btn_watch_medium", lang), callback_data="demo_type_medium")])
        keyboard.append([InlineKeyboardButton(get_text("btn_watch_premium", lang), callback_data="demo_type_premium")])
        keyboard.append([get_buy_stars_button(lang, user_id)])
        keyboard.append([InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")])

        header = get_text("demo_menu_text", lang,
                          balance=balance,
                          regular_count=regular_count,
                          medium_count=medium_count,
                          premium_count=premium_count)

        try:
            await query.edit_message_text(
                header,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=user_id,
                text=header,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

    # ── Demo Click — Deduct Stars & Send Protected Video ───
    elif data.startswith("demo_type_"):
        video_type = data.replace("demo_type_", "")
        
        prices = {"regular": 15, "medium": 25, "premium": 49}
        price = prices.get(video_type, 15)

        from services.demo_service import get_random_video_by_type
        demo = get_random_video_by_type(video_type)
        if not demo:
            msg = get_text("no_videos_available", lang).replace("{type}", video_type)
            await query.answer(msg, show_alert=True)
            return

        slot = demo["slot"]

        # Deduct stars — fail gracefully if insufficient
        success = deduct_stars(user_id, price)
        if not success:
            dash = get_user_dashboard_data(user_id)
            balance = dash["stars_balance"]
            insufficient_text = get_text("demo_insufficient_stars", lang, price=price, balance=balance)
            insufficient_kb = InlineKeyboardMarkup([
                [get_buy_stars_button(lang, user_id)],
                [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")],
            ])
            try:
                await query.edit_message_text(insufficient_text, reply_markup=insufficient_kb, parse_mode="HTML")
            except Exception:
                await context.bot.send_message(chat_id=user_id, text=insufficient_text, reply_markup=insufficient_kb, parse_mode="HTML")
            return

        log_interaction(user_id, "view_demo", detail=f"demo_{slot}_{video_type}")

        # Updated balance after deduction
        dash = get_user_dashboard_data(user_id)
        new_balance = dash["stars_balance"]

        # Build video inline keyboard
        video_keyboard = []
        all_prices = {"regular": 15, "medium": 25, "premium": 49}
        for v_type, v_price in all_prices.items():
            if new_balance >= v_price:
                label = f"▶️ Watch Another {v_type.capitalize()}  ·  {v_price} ⭐"
            else:
                need = v_price - new_balance
                label = f"⚠️ Watch {v_type.capitalize()}  ·  {v_price} ⭐  (need {need})"
            video_keyboard.append([InlineKeyboardButton(label, callback_data=f"demo_type_{v_type}")])


        video_keyboard.append([
            get_buy_stars_button(lang, user_id, text="💫 Buy Stars"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ])

        type_emoji = {"regular": "🎥", "medium": "📺", "premium": "💎"}.get(video_type, "🎬")
        caption = (
            f"{type_emoji} <b>{video_type.capitalize()} Video</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ <b>{price} Stars deducted</b>  •  Balance: <b>{new_balance} ⭐</b>\n\n"
            f"<i>Want more? Tap 💫 Buy Stars to top up.</i>"
        )

        await context.bot.send_video(
            chat_id=user_id,
            video=demo["file_id"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(video_keyboard),
            parse_mode="HTML",
            supports_streaming=True,
            protect_content=True,
        )

        # Silently acknowledge — the video itself carries the keyboard
        await query.answer()

    # ── My Profile ─────────────────────────────────────────
    elif data == "view_profile":
        log_interaction(user_id, "view_profile")
        status = get_user_status(user_id)
        if not status:
            text = (
                "👤 <b>My Account</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "No profile found. Please send /start to register."
                + BRAND_FOOTER
            )
        else:
            plan = status.get("selected_plan") or "None"
            plan_name = PRICING_PLANS.get(plan, {}).get("name", plan.capitalize()) if plan != "None" else "—"
            payment_status = (status.get("payment_status") or "none").capitalize()
            access = "Active" if status.get("is_approved") else "Pending"
            is_approved = status.get("is_approved")
            join_date = str(status.get("join_date", "Unknown"))[:10]
            referrals = status.get("referral_count", 0)
            method = status.get("payment_method", "crypto").capitalize()
            text = (
                "👤 <b>My Account</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 <b>Plan:</b> {plan_name}\n"
                f"💳 <b>Payment:</b> {payment_status} ({method})\n"
                f"🔐 <b>Access:</b> {access}\n"
                f"📅 <b>Member Since:</b> {join_date}\n"
                f"🔗 <b>Referrals:</b> {referrals} friend(s)"
                + BRAND_FOOTER
            )
            if is_approved:
                support_url = (
                    f"https://t.me/{SUPPORT_USERNAME}"
                    f"?text=Hi%2C+I+need+my+access+link+re-sent+(Plan%3A+{plan_name})"
                )
                profile_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Re-send My Access Link", url=support_url)],
                    [InlineKeyboardButton("Main Menu", callback_data="main_menu")],
                ])
            else:
                profile_markup = back_to_main()
        try:
            await query.edit_message_text(text, reply_markup=profile_markup, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=profile_markup, parse_mode="HTML")

    # ── Refer & Earn ───────────────────────────────────────
    elif data == "view_referral":
        log_interaction(user_id, "view_referral")
        status = get_user_status(user_id)
        referral_count = status.get("referral_count", 0) if status else 0
        
        keyboard = []
        if BOT_USERNAME == "YourBotUsername":
            link_display = "Referral links not configured - set BOT_USERNAME in .env"
        else:
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
            link_display = f"<code>{ref_link}</code>"
            share_text = get_text("share_msg", lang)
            share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"
            keyboard.append([InlineKeyboardButton(get_text("btn_share_friend", lang), url=share_url)])
            
        keyboard.append([InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")])

        text = (
            "🔗 <b>Refer & Earn</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Share your unique link with friends. Every person who joins through "
            "your link is counted as your referral and earns you rewards!\n\n"
            f"<b>Your Link:</b>\n{link_display}\n\n"
            f"👥 <b>Total Referrals:</b> {referral_count} friend(s)\n\n"
            "<i>Rewards are credited automatically once referrals complete a purchase.</i>"
            + BRAND_FOOTER
        )
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    # ── FAQ ────────────────────────────────────────────────
    elif data == "view_faq":
        log_interaction(user_id, "view_faq")
        faq_text = get_text("faq_title", lang)
        
        # We have 7 FAQ items in our JSON
        for i in range(1, 8):
            q = get_text(f"faq_q{i}", lang)
            a = get_text(f"faq_a{i}", lang)
            faq_text += f"<b>{q}</b>\n{a}\n\n"
            
        faq_text += BRAND_FOOTER.strip()
        keyboard = [
            [InlineKeyboardButton(get_text("btn_contact_support", lang), url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")]
        ]
        try:
            await query.edit_message_text(faq_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    # ── Admin List Views ───────────────────────────────────
    elif data in ("admin_list_pending", "admin_list_approved", "admin_list_cancelled"):
        status_key = data.replace("admin_list_", "")
        icon = {
            "pending":   "⏳",
            "approved":  "✅",
            "cancelled": "❌",
        }.get(status_key, "")
        users = get_users_by_status(status_key)
        if not users:
            text = f"{icon} <b>No {status_key.capitalize()} Users</b>\n\nNothing here yet."
        else:
            text = f"{icon} <b>{status_key.capitalize()} Users ({len(users)})</b>\n\n"
            for u in users:
                plan = (u.get('selected_plan') or 'None').capitalize()
                joined = str(u.get('join_date', ''))[:10]
                uname = f"@{u['username']}" if u.get('username') else "N/A"
                text += (
                    f"🆔 <code>{u['user_id']}</code> {uname}\n"
                    f"💳 Plan: {plan}  |  📅 {joined}\n"
                )
                if status_key == "pending":
                    text += f"✅ /approve {u['user_id']}\n"
                elif status_key == "approved":
                    text += f"❌ /cancel {u['user_id']}\n"
                text += "─────────────────\n"

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

    # ── Testimonials / Social Proof ────────────────────────
    elif data == "view_testimonials":
        log_interaction(user_id, "view_testimonials")
        testimonials_text = (
            "⭐ <b>What Our Members Say</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <i>\"Joined the Pro plan last month — the daily drops are insane. "
            "Worth every star.\"</i>\n"
            "— @mike_d ✅ <b>Verified Buyer</b>\n\n"
            "💬 <i>\"Got the Global Access pack. 15k+ videos and still growing. This is the real deal.\"</i>\n"
            "— @sarah_k ✅ <b>Verified Buyer</b>\n\n"
            "💬 <i>\"Fastest delivery I've ever seen — invite link landed in seconds after Stars payment.\"</i>\n"
            "— @ryu_99 ✅ <b>Verified Buyer</b>\n\n"
            "💬 <i>\"The Ultra HD quality is on another level. No more sketchy sites.\"</i>\n"
            "— @nadia_v ✅ <b>Verified Buyer</b>\n\n"
            "💬 <i>\"Support was quick when I needed help. Top-tier service.\"</i>\n"
            "— @james_o ✅ <b>Verified Buyer</b>"
            + BRAND_FOOTER
        )
        keyboard = [
            [get_buy_stars_button(lang, user_id, text="💎 Get Full Access")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            testimonials_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

async def send_nudge(context: ContextTypes.DEFAULT_TYPE):
    """Background task: Follow up with a user who viewed a plan 24h ago but didn't buy."""
    job = context.job
    data = job.data
    user_id = data["user_id"]
    plan_id = data["plan_id"]
    lang = data["lang"]
    
    # Check if they already bought
    if has_active_purchase(user_id, plan_id):
        return
        
    user_status = get_user_status(user_id)
    if not user_status:
        return
        
    # Also check DB for crypto approval on this plan
    if user_status.get("is_approved") and user_status.get("selected_plan") == plan_id:
        return

    plan_name = PRICING_PLANS.get(plan_id, {}).get("name", plan_id.capitalize())
    first_name = user_status.get("full_name") or user_status.get("username") or "there"
    
    nudge_text = get_text("re_engagement_nudge", lang, first_name=first_name, plan_name=plan_name)
    
    keyboard = [
        [InlineKeyboardButton("💎 Complete Purchase", callback_data=f"buy_{plan_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=nudge_text + BRAND_FOOTER,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send re-engagement nudge to {user_id}: {e}")
