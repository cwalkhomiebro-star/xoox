#!/usr/bin/env python3
"""
setup_webhook.py
────────────────
Run this ONCE after deploying to Vercel to register both bots' webhook URLs.

Usage:
    python setup_webhook.py https://your-project.vercel.app

What it does:
    1. Registers the main bot    → POST /api/webhook
    2. Registers the cashier bot → POST /api/cashier
    3. Prints confirmation / error for each bot
"""

import sys
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAIN_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
CASHIER_TOKEN = os.getenv("CASHIER_BOT_TOKEN")
SECRET        = os.getenv("WEBHOOK_SECRET", "super-secret-token")


def set_webhook(token: str, url: str, secret: str, label: str) -> None:
    print(f"\n🔗  Setting webhook for {label}...")
    print(f"    URL: {url}")
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": url,
            "secret_token": secret,
            "allowed_updates": [
                "message",
                "callback_query",
                "pre_checkout_query",
                "successful_payment",
            ],
            "drop_pending_updates": True,
        },
        timeout=15,
    )
    data = resp.json()
    if data.get("ok"):
        print(f"    ✅  Success: {data.get('description', 'Webhook set.')}")
    else:
        print(f"    ❌  Failed:  {data}")


def get_webhook_info(token: str, label: str) -> None:
    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getWebhookInfo",
        timeout=15,
    )
    data = resp.json().get("result", {})
    print(f"\n📋  Webhook info for {label}:")
    print(f"    URL:            {data.get('url', 'N/A')}")
    print(f"    Pending updates:{data.get('pending_update_count', 0)}")
    last_error = data.get("last_error_message")
    if last_error:
        print(f"    ⚠️  Last error:  {last_error}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_webhook.py https://your-project.vercel.app")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    print(f"\n🚀  Registering webhooks for: {base_url}")

    if not MAIN_TOKEN:
        print("❌  TELEGRAM_BOT_TOKEN not found in .env — skipping main bot.")
    else:
        set_webhook(MAIN_TOKEN,    f"{base_url}/api/webhook", SECRET, "Main Bot")
        get_webhook_info(MAIN_TOKEN, "Main Bot")

    if not CASHIER_TOKEN:
        print("❌  CASHIER_BOT_TOKEN not found in .env — skipping cashier bot.")
    else:
        set_webhook(CASHIER_TOKEN, f"{base_url}/api/cashier", SECRET, "Cashier Bot")
        get_webhook_info(CASHIER_TOKEN, "Cashier Bot")

    print("\n✅  Done! Both bots are now registered.\n")
