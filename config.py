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
# crypto_usd = usd price with 30% discount (for USDT crypto payment path)
STAR_PACKAGES = {
    "starter": {
        "name":            "🥉 Starter",
        "stars_paid":      2050,    # 1/3 of original
        "stars_credited":  2330,    # 1/3 of original
        "bonus":           280,     # 1/3 of original
        "usd":             "$80",
        "crypto_usd":      "$80",   # Full price
    },
    "pro": {
        "name":            "🥈 Pro",
        "stars_paid":      4100,    # 1/3 of original
        "stars_credited":  4660,    # 1/3 of original
        "bonus":           560,     # 1/3 of original
        "usd":             "$160",
        "crypto_usd":      "$160",  # Full price
    },
    "premium": {
        "name":            "🥇 Premium",
        "stars_paid":      8980,    # 1/3 of original
        "stars_credited":  10660,   # 1/3 of original
        "bonus":           1680,    # 1/3 of original
        "usd":             "$350",
        "crypto_usd":      "$350",  # Full price
    },
    "elite": {
        "name":            "💎 Elite",
        "stars_paid":      15380,   # 1/3 of original
        "stars_credited":  19330,   # 1/3 of original
        "bonus":           3950,    # 1/3 of original
        "usd":             "$599",
        "crypto_usd":      "$599",  # Full price
    },
}
