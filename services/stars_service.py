"""
stars_service.py
────────────────
Handles all Telegram Stars (XTR) payment logic.
Stars use Telegram's native Payments API with provider_token="" (empty).
"""

from config import PRICING_PLANS
from telegram import LabeledPrice


def build_payload(user_id: int, plan_id: str) -> str:
    """
    Generates a unique, verifiable payload string for the Stars invoice.
    Format: "stars_{plan_id}_{user_id}"
    This is stored inside the invoice and returned unchanged in successful_payment.
    """
    return f"stars_{plan_id}_{user_id}"


def parse_payload(payload: str) -> tuple[str | None, int | None]:
    """
    Parses a Stars payload back into (plan_id, user_id).
    Returns (None, None) if the payload is invalid or not a Stars payload.
    """
    try:
        parts = payload.split("_", maxsplit=2)
        # Format: stars_{plan_id}_{user_id}  → parts = ['stars', plan_id, user_id]
        if parts[0] != "stars" or len(parts) != 3:
            return None, None
        plan_id = parts[1]
        user_id = int(parts[2])
        if plan_id not in PRICING_PLANS:
            return None, None
        return plan_id, user_id
    except (IndexError, ValueError):
        return None, None


async def send_stars_invoice(bot, chat_id: int, plan_id: str, user_id: int) -> None:
    """
    Sends a Telegram Stars invoice to the user.

    Key points:
    - provider_token must be "" (empty string) for Stars (XTR) payments.
    - currency must be "XTR" (Telegram Stars).
    - prices are in whole Stars (1 LabeledPrice = 1 Star).
    - The payload is embedded in the invoice and returned on successful_payment.
    """
    plan = PRICING_PLANS[plan_id]
    stars_amount = plan["stars_price"]  # Integer number of Stars
    payload = build_payload(user_id, plan_id)

    await bot.send_invoice(
        chat_id=chat_id,
        title=plan["name"],
        description=plan["description"],
        payload=payload,
        provider_token="",          # Empty string = Telegram Stars (no payment provider)
        currency="XTR",             # XTR = Telegram Stars currency code
        prices=[LabeledPrice(label=plan["name"], amount=stars_amount)],
        # Optional but recommended metadata
        protect_content=False,
    )
