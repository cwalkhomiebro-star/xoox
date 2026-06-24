"""
api/daily_stars.py — Vercel Cron Job endpoint.
Triggered once per day by Vercel's scheduler (configured in vercel.json).
Credits DAILY_STARS to every non-banned user and sends them a notification.
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, abort
from telegram import Bot

from config import TOKEN, DAILY_STARS
from services.database import init_db
from services.user_service import get_all_user_ids, credit_daily_stars

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Shared secret — set CRON_SECRET in Vercel environment variables
CRON_SECRET = os.environ.get("CRON_SECRET", "")


@app.route("/api/daily_stars", methods=["GET", "POST"])
def daily_stars():
    """
    Vercel Cron endpoint — fires once per day.
    Vercel sends the Authorization header automatically when triggered by a cron job.
    """
    # Protect the endpoint: only Vercel cron (or manual calls with the secret) allowed
    auth = request.headers.get("Authorization", "")
    if CRON_SECRET and auth != f"Bearer {CRON_SECRET}":
        logger.warning("daily_stars: unauthorised call blocked.")
        abort(403)

    init_db()

    user_ids = get_all_user_ids()
    if not user_ids:
        logger.info("daily_stars: no users found, skipping.")
        return f"No users. Skipped.", 200

    # Credit stars to every user in one DB pass
    for uid in user_ids:
        credit_daily_stars(uid, DAILY_STARS)

    # Send notifications asynchronously
    async def _notify():
        bot = Bot(token=TOKEN)
        sent, failed = 0, 0
        async with bot:
            for uid in user_ids:
                try:
                    await bot.send_message(
                        chat_id=uid,
                        text=(
                            f"🎁 <b>Daily Stars Drop!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"⭐ <b>{DAILY_STARS} free Stars</b> have just been added to your balance!\n\n"
                            f"Use them to watch videos — enjoy! 🎬"
                        ),
                        parse_mode="HTML",
                    )
                    sent += 1
                except Exception:
                    failed += 1
                await asyncio.sleep(0.05)  # ~20 msg/s — safe under Telegram flood limits
        logger.info(f"daily_stars: {DAILY_STARS}⭐ sent to {sent} users ({failed} failed).")
        return sent, failed

    loop = asyncio.new_event_loop()
    sent, failed = loop.run_until_complete(_notify())
    loop.close()

    return f"Done. Credited {DAILY_STARS}⭐ to {len(user_ids)} users. Notified: {sent}, Failed: {failed}.", 200
