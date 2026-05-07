from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.i18n import get_text

def get_main_menu_markup(lang: str = "en"):
    """Generates the main menu inline keyboard."""
    keyboard = [
        [InlineKeyboardButton(get_text("btn_pricing", lang), callback_data="view_pricing")],
        [InlineKeyboardButton(get_text("btn_demos", lang), callback_data="view_demos")],
        [InlineKeyboardButton(get_text("btn_profile", lang), callback_data="view_profile")],
        [InlineKeyboardButton(get_text("btn_referral", lang), callback_data="view_referral")],
        [InlineKeyboardButton(get_text("btn_faq", lang), callback_data="view_faq")],
        [InlineKeyboardButton(get_text("btn_change_language", lang), callback_data="change_language")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main(lang: str = "en"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")]])
