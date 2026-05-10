from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.i18n import get_text
from config import BOT_USERNAME, CASHIER_BOT_USERNAME
import urllib.parse

def get_buy_stars_button(lang: str, user_id: int, text: str = None):
    """Returns the correct Buy Stars inline button (Cashier URL or fallback)."""
    btn_text = text or get_text("btn_pricing", lang)
    if CASHIER_BOT_USERNAME and CASHIER_BOT_USERNAME != "YourCashierBotUsername" and user_id:
        pricing_url = f"tg://resolve?domain={CASHIER_BOT_USERNAME}&start=pay_{user_id}"
        return InlineKeyboardButton(btn_text, url=pricing_url)
    return InlineKeyboardButton(btn_text, callback_data="view_pricing")

def get_main_menu_markup(lang: str = "en", user_id: int = None):
    """Generates the main menu inline keyboard — 2 buttons per row."""
    pricing_btn = get_buy_stars_button(lang, user_id)

    keyboard = [
        [
            pricing_btn,
            InlineKeyboardButton(get_text("btn_demos", lang),    callback_data="view_demos"),
        ],
        [
            InlineKeyboardButton(get_text("btn_profile", lang),  callback_data="view_profile"),
            InlineKeyboardButton(get_text("btn_referral", lang), callback_data="view_referral"),
        ],
        [
            InlineKeyboardButton(get_text("btn_faq", lang),          callback_data="view_faq"),
            InlineKeyboardButton(get_text("btn_testimonials", lang),  callback_data="view_testimonials"),
        ],
        [
            InlineKeyboardButton(get_text("btn_change_language", lang), callback_data="change_language"),
        ],
    ]
    
    if user_id:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        share_text = get_text("share_msg", lang)
        share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"
        keyboard.insert(2, [InlineKeyboardButton(get_text("btn_share_friend", lang), url=share_url)])
        
    return InlineKeyboardMarkup(keyboard)

def back_to_main(lang: str = "en"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")]])
