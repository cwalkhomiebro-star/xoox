import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Tokens
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CASHIER_BOT_TOKEN = os.getenv("CASHIER_BOT_TOKEN")
CASHIER_BOT_USERNAME = os.getenv("CASHIER_BOT_USERNAME", "YourCashierBotUsername").replace("@", "")

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
    "ultimate": {
        "label": "👑 BEST VALUE: Global Access — $99 | 15,000+ Videos",
        "name": "👑 Global Access",
        "price": 99,
        "original_price": 149,
        "stars_price": 7650,   # ~$99 in Stars
        "description": "15,000+ Videos · ALL Private Groups · Unlimited Megalinks · Full Vault Access · Lifetime Updates (2025–2026)"
    },
    "pro": {
        "label": "🔥 HOT DEAL: Pro Access — $50 | 1,200+ Videos",
        "name": "🔥 Pro Access",
        "price": 50,
        "original_price": 79,
        "stars_price": 3850,   # ~$50 in Stars
        "description": "1,200+ Videos · 10 VIP Groups · 3 Megalinks · New drops daily (2025–2026)"
    },
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

# Cost in Stars to unlock a single preview
DEMO_STAR_PRICE = 50

# ── Star Rewards (configurable) ─────────────────────────────────────────────────
# Stars gifted to every brand-new user on first /start
WELCOME_STARS = 600          # was 60, x10
# Stars awarded to a referrer each time one of their invites joins
REFERRAL_REWARD_STARS = 50   # was 5, x10
# Stars dropped to every active user once per day
DAILY_STARS = 5             # configurable daily bonus

# ── Star Top-Up Packages ────────────────────────────────────────────────────────
# Users pay Telegram Stars → credited to their in-bot balance.
# 1 Telegram Star ≈ $0.013 USD  →  $1 ≈ 77 Stars
STAR_PACKAGES = {
    "starter": {
        "name":            "🥉 Starter",
        "stars_paid":      6150,   # ~$80
        "stars_credited":  7000,   # +850 bonus
        "bonus":           850,
        "usd":             "$80",
    },
    "pro": {
        "name":            "🥈 Pro",
        "stars_paid":      11550,  # ~$150
        "stars_credited":  13500,  # +1950 bonus
        "bonus":           1950,
        "usd":             "$150",
    },
    "premium": {
        "name":            "🥇 Premium",
        "stars_paid":      23000,  # ~$299
        "stars_credited":  28000,  # +5000 bonus
        "bonus":           5000,
        "usd":             "$299",
    },
    "elite": {
        "name":            "💎 Elite",
        "stars_paid":      38400,  # ~$499
        "stars_credited":  50000,  # +11600 bonus
        "bonus":           11600,
        "usd":             "$499",
    },
}
