import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Admin ID (ensure it's an integer)
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

# Private Channel ID
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Wallet Address
WALLET_ADDRESS = os.getenv("USDT_TRC20_WALLET", "0xYourWalletAddressHere")

# Support Username
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "YourSupportUsername")

# Pricing Plans
PRICING_PLANS = {
    "starter": {
        "label": "💎 Elite Starter — $20",
        "name": "💎 Elite Starter",
        "price": 20,
        "description": "137+ Ultra HD Videos (2025–2026)"
    },
    "pro": {
        "label": "🔥 HOT DEAL: Pro Access — $50",
        "name": "🔥 Pro Access",
        "price": 50,
        "description": "250+ Videos · 5 VIP Groups · 1 Megalink (2025–2026)"
    },
    "ultimate": {
        "label": "👑 BEST VALUE: Global Access — $99",
        "name": "👑 Global Access",
        "price": 99,
        "description": "9999+ Videos · All Private Groups · Full Vault Access (2025–2026)"
    }
}

# Demo Links
DEMO_LINK_1 = "https://jumpshare.com/share/l6NICLlEE2FV7itvSQ5l"
DEMO_LINK_2 = "https://jumpshare.com/folder/xPjbu3uarCFI4K4nBV87"
DEMO_LINK_3 = "https://jumpshare.com/share/03GI49IvaOWbc9ty4sTX"

# Welcome Message
WELCOME_TEXT = (
    "<b>Welcome to 9-17 🌟</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "💎 Exclusive 2025–2026 premium videos, delivered instantly after payment.\n\n"
    "Browse our plans, preview demos, or check your account below."
)

# Demo Menu Message
DEMO_MENU_TEXT = (
    "🎬 <b>Free Demo Previews</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Get a taste of what’s inside. All previews are from our <b>2025–2026</b> vault.\n\n"
    "⏳ <b>More content dropping soon...</b>"
)

# Plan Urgency Badges (kept for reference — badges now baked into label)
PLAN_BADGES = {
    "starter": "",
    "pro": "",
    "ultimate": "",
}

# FAQ Items
FAQ_ITEMS = [
    ("💰 How do I pay?", "Send USDT (TRC20) to the wallet address shown on the payment screen, then tap \u2018I've Sent the Payment\u2019."),
    ("⏱ How long does it take?", "Payments are verified manually. Access is usually delivered within a few minutes of confirmation."),
    ("🔗 What do I get after payment?", "A private invite link to the exclusive group with all premium videos."),
    ("🔒 Is it safe?", "Yes. Every payment is verified before access is granted."),
    ("❓ I paid but got no link?", "Please contact support using the button below."),
]

# Bot Username (for referral links — set this to your bot's @username without @)
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername")

# Database path
DB_PATH = "bot_database.db"
