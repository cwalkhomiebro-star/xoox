import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    PRICING_PLANS,
    SUPPORT_USERNAME,
    DEMO_LINK_1,
    DEMO_LINK_2,
    DEMO_LINK_3,
    DEMO_LINK_4,
    BOT_USERNAME,
)
from utils.i18n import get_text
from utils.keyboards import get_main_menu_markup, back_to_main

BRAND_FOOTER = "\n\n<i>— 🌟 9-17 —</i>"

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
)
from services.payment_service import get_payment_instructions
from services.stars_service import send_stars_invoice, has_active_purchase

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
            reply_markup=get_main_menu_markup(lang), 
            parse_mode="HTML"
        )
        return

    # ── Main Menu ──────────────────────────────────────────
    if data == "main_menu":
        await query.edit_message_text(
            get_text("welcome_text", lang), reply_markup=get_main_menu_markup(lang), parse_mode="HTML"
        )

    # ── Pricing ────────────────────────────────────────────
    elif data == "view_pricing":
        log_interaction(user_id, "view_pricing")
        keyboard = []
        for plan_id, info in PRICING_PLANS.items():
            stars_hint = f"  ·  ⭐ {info['stars_price']:,}"
            plan_label = get_text(f"plan_{plan_id}_label", lang)
            keyboard.append([InlineKeyboardButton(
                plan_label + stars_hint,
                callback_data=f"buy_{plan_id}"
            )])
        keyboard.append([InlineKeyboardButton(get_text("btn_testimonials", lang), callback_data="view_testimonials")])
        keyboard.append([InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")])

        await query.edit_message_text(
            get_text("select_access_plan", lang) + BRAND_FOOTER,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── Buy a Plan — Payment Method Selection ──────────────
    elif data.startswith("buy_"):
        plan_id = data.replace("buy_", "")
        plan_info = PRICING_PLANS.get(plan_id)
        if not plan_info:
            await query.edit_message_text(get_text("plan_not_found", lang), reply_markup=back_to_main(lang))
            return
        log_interaction(user_id, "view_plan", detail=plan_id)

        # Upgrade / already-owned detection
        _plan_order = ["starter", "pro", "ultimate"]
        _ustat = get_user_status(user_id)
        _current = (_ustat or {}).get("selected_plan") if (_ustat or {}).get("is_approved") else None
        
        plan_name = get_text(f"plan_{plan_id}_name", lang)
        
        upgrade_note = ""
        if _current == plan_id:
            await query.edit_message_text(
                get_text("already_own_plan", lang, plan_name=plan_name) + BRAND_FOOTER,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(get_text("btn_contact_support", lang), url=f"https://t.me/{SUPPORT_USERNAME}")],
                    [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")],
                ]),
                parse_mode="HTML"
            )
            return
        elif _current and _current in _plan_order and plan_id in _plan_order:
            _cur_name = get_text(f"plan_{_current}_name", lang)
            if _plan_order.index(plan_id) > _plan_order.index(_current):
                upgrade_note = get_text("upgrade_from", lang, cur_name=_cur_name)
            else:
                upgrade_note = get_text("currently_have", lang, cur_name=_cur_name)

        keyboard = [
            [InlineKeyboardButton(get_text("btn_pay_crypto", lang), callback_data=f"pay_crypto_{plan_id}")],
            [InlineKeyboardButton(get_text("btn_pay_stars", lang), callback_data=f"pay_stars_{plan_id}")],
            [InlineKeyboardButton(get_text("btn_back_plans", lang), callback_data="view_pricing")],
        ]
        
        plan_desc = get_text(f"plan_{plan_id}_desc", lang)
        plan_text = get_text("plan_details", lang, 
                             plan_name=plan_name, 
                             description=plan_desc, 
                             price=plan_info['price'], 
                             stars_price=f"{plan_info['stars_price']:,}", 
                             upgrade_note=upgrade_note)

        await query.edit_message_text(
            plan_text + BRAND_FOOTER,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

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

    # ── Pay with Telegram Stars ────────────────────────────
    elif data.startswith("pay_stars_"):
        plan_id = data.replace("pay_stars_", "")
        plan_info = PRICING_PLANS.get(plan_id)
        if not plan_info:
            await query.edit_message_text(get_text("plan_not_found", lang), reply_markup=back_to_main(lang))
            return
        log_interaction(user_id, "pay_stars", detail=plan_id)
        
        plan_name = get_text(f"plan_{plan_id}_name", lang)

        if has_active_purchase(user_id, plan_id):
            await query.edit_message_text(
                get_text("already_own_plan", lang, plan_name=plan_name) + BRAND_FOOTER,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(get_text("btn_contact_support", lang), url=f"https://t.me/{SUPPORT_USERNAME}")],
                    [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")],
                ]),
                parse_mode="HTML"
            )
            return

        await send_stars_invoice(
            bot=context.bot,
            chat_id=user_id,
            plan_id=plan_id,
            user_id=user_id
        )

        await query.edit_message_text(
            get_text("stars_invoice_sent", lang, plan_name=plan_name, stars_price=f"{plan_info['stars_price']:,}") + BRAND_FOOTER,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("btn_back_plans", lang), callback_data=f"buy_{plan_id}")]
            ]),
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

    # ── Free Demos ─────────────────────────────────────────
    elif data == "view_demos":
        log_interaction(user_id, "view_demos")
        keyboard = [
            [InlineKeyboardButton("▶️ Preview #1", callback_data="demo_click_1")],
            [InlineKeyboardButton("▶️ Preview #2", callback_data="demo_click_2")],
            [InlineKeyboardButton("▶️ Preview #3", callback_data="demo_click_3")],
            [InlineKeyboardButton("▶️ Preview #4", callback_data="demo_click_4")],
            [InlineKeyboardButton(get_text("btn_pricing", lang), callback_data="view_pricing")],
            [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            get_text("demo_menu_text", lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # ── Demo Click Tracking ────────────────────────────────
    elif data.startswith("demo_click_"):
        demo_num = data.replace("demo_click_", "")
        demo_key = f"demo_{demo_num}"
        log_interaction(user_id, "view_demo", detail=demo_key)

        demo_url_map = {
            "1": DEMO_LINK_1,
            "2": DEMO_LINK_2,
            "3": DEMO_LINK_3,
            "4": DEMO_LINK_4,
        }
        url = demo_url_map.get(demo_num, DEMO_LINK_1)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎬 <b>Preview #{demo_num}</b>\n\n👉 <a href=\"{url}\">Click here to watch</a>\n\n"
                 f"<i>Enjoy the preview! Tap 💎 Pricing Plans to get full access.</i>"
                 + BRAND_FOOTER,
            parse_mode="HTML",
            disable_web_page_preview=False
        )

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
        await query.edit_message_text(text, reply_markup=profile_markup, parse_mode="HTML")

    # ── Refer & Earn ───────────────────────────────────────
    elif data == "view_referral":
        log_interaction(user_id, "view_referral")
        status = get_user_status(user_id)
        referral_count = status.get("referral_count", 0) if status else 0
        if BOT_USERNAME == "YourBotUsername":
            link_display = "Referral links not configured - set BOT_USERNAME in .env"
        else:
            link_display = f"<code>https://t.me/{BOT_USERNAME}?start=ref_{user_id}</code>"
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
        await query.edit_message_text(text, reply_markup=back_to_main(), parse_mode="HTML")

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
        await query.edit_message_text(faq_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

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
            [InlineKeyboardButton("💎 Get Full Access", callback_data="view_pricing")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            testimonials_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
