# utils/messages.py

from config import SUPPORT_USERNAME

# ── Brand Footer ────────────────────────────────────────────────────────────────
# Appended to every user-facing screen for consistent identity.
BRAND_FOOTER = "\n\n<i>— 🌟 9-17 —</i>"

# Welcome Message
WELCOME_TEXT = (
    "<b>Welcome to 9-17 🌟</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "💎 Exclusive 2025–2026 premium videos, delivered instantly after payment.\n\n"
    "Browse our plans, preview demos, or check your account below."
    + BRAND_FOOTER
)

# Demo Menu Message
DEMO_MENU_TEXT = (
    "🎬 <b>Free Demo Previews</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Get a taste of what's inside. All previews are from our <b>2025–2026</b> vault.\n\n"
    "⏳ <b>More content dropping soon...</b>"
    + BRAND_FOOTER
)

# FAQ Items
FAQ_ITEMS = [
    ("💰 How do I pay?", "Send USDT (TRC20) to the wallet address shown on the payment screen, then provide your Transaction Hash (TxID) to automatically verify the payment."),
    ("⏱ How long does it take?", "Crypto payments are automatically verified usually within 1-3 minutes of network confirmation. Stars payments are instant."),
    ("🔗 What do I get after payment?", "A private invite link to the exclusive group with all premium videos."),
    ("🔒 Is it safe?", "Yes. Every payment is verified before access is granted."),
    ("❓ I paid but got no link?", "Please contact support using the button below."),
    ("⭐ What are Telegram Stars?", "Stars are Telegram's built-in payment currency. Buy them inside the Telegram app (Settings → Stars). 1 Star ≈ $0.013 USD — no crypto wallet needed."),
    ("💫 Can I get a Stars refund?", "Stars refunds can be issued within 30 days if there is a genuine issue. Contact support with your Charge ID and we will process it immediately."),
]
