import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Admin ID (ensure it's an integer)
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

# Private Channel ID
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None

# Wallet Address
WALLET_ADDRESS = os.getenv("USDT_TRC20_WALLET", "0xYourWalletAddressHere")

# Support Username
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "YourSupportUsername")

# Pricing Plans
# 'price'       → USD amount charged via crypto (USDT TRC20)
# 'stars_price' → Telegram Stars amount (XTR). 1 Star ≈ $0.013 USD.
#                 Use Telegram's Stars Store for the latest rate.
PRICING_PLANS = {
    "basic": {
        "label": "🌟 Basic Access — $5 | 50 Videos",
        "name": "🌟 Basic Access",
        "price": 5,
        "stars_price": 385,    # ~$5 in Stars
        "description": "50 Premium Videos"
    },
    "starter": {
        "label": "💎 Elite Starter — $25 | 500+ Videos",
        "name": "💎 Elite Starter",
        "price": 25,
        "stars_price": 1925,   # ~$25 in Stars
        "description": "500+ Ultra HD Videos · 2 VIP Groups · Daily Drops (2025–2026)"
    },
    "pro": {
        "label": "🔥 HOT DEAL: Pro Access — $50 | 1,200+ Videos",
        "name": "🔥 Pro Access",
        "price": 50,
        "stars_price": 3850,   # ~$50 in Stars
        "description": "1,200+ Videos · 10 VIP Groups · 3 Megalinks · New drops daily (2025–2026)"
    },
    "ultimate": {
        "label": "👑 BEST VALUE: Global Access — $99 | 15,000+ Videos",
        "name": "👑 Global Access",
        "price": 99,
        "stars_price": 7650,   # ~$99 in Stars
        "description": "15,000+ Videos · ALL Private Groups · Unlimited Megalinks · Full Vault Access · Lifetime Updates (2025–2026)"
    }
}

# Demo Links
DEMO_LINK_1 = "https://jumpshare.com/share/uTJzBBoWUhnYfIbnWc4c"
DEMO_LINK_2 = "https://jumpshare.com/folder/xPjbu3uarCFI4K4nBV87"
DEMO_LINK_3 = "https://jumpshare.com/share/03GI49IvaOWbc9ty4sTX"
DEMO_LINK_4 = "https://jumpshare.com/share/l6NICLlEE2FV7itvSQ5l"

# ── Startup Validation ──────────────────────────────────────────────────────────
import logging as _logging
_val_logger = _logging.getLogger("config")
if SUPPORT_USERNAME == "YourSupportUsername":
    _val_logger.warning("⚠️  SUPPORT_USERNAME is still the default placeholder — set it in .env!")
if not TOKEN:
    _val_logger.error("❌  TELEGRAM_BOT_TOKEN is not set — bot will not start!")
if not CHANNEL_ID:
    _val_logger.error("❌  CHANNEL_ID is not set — invite links will fail!")

# Bot Username (for referral links — set this to your bot's @username without @)
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername")

# Database path
DB_PATH = "bot_database.db"
