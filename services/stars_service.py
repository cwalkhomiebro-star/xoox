"""
stars_service.py
────────────────
Handles all Telegram Stars (XTR) payment logic.
Stars use Telegram's native Payments API with provider_token="" (empty).
"""

from config import PRICING_PLANS, STAR_PACKAGES
from telegram import LabeledPrice


# ── Legacy content-plan helpers ──────────────────────────────────────────────

def build_payload(user_id: int, plan_id: str) -> str:
    """Payload for content-plan purchases: 'stars_{plan_id}_{user_id}'"""
    return f"stars_{plan_id}_{user_id}"


def parse_payload(payload: str) -> tuple[str | None, int | None]:
    """
    Parses a Stars payload back into (plan_id, user_id).
    Handles both legacy content-plan payloads AND new star-package payloads.
    Returns (None, None) if invalid.
    """
    try:
        parts = payload.split("_", maxsplit=2)
        if parts[0] != "stars" or len(parts) != 3:
            return None, None
        plan_id  = parts[1]
        user_id  = int(parts[2])
        # Accept both content plans and star packages
        if plan_id not in PRICING_PLANS and plan_id not in STAR_PACKAGES:
            return None, None
        return plan_id, user_id
    except (IndexError, ValueError):
        return None, None


async def send_stars_invoice(bot, chat_id: int, plan_id: str, user_id: int) -> None:
    """Sends a Telegram Stars invoice for a legacy content plan."""
    plan = PRICING_PLANS[plan_id]
    stars_amount = plan["stars_price"]
    payload = build_payload(user_id, plan_id)

    await bot.send_invoice(
        chat_id=chat_id,
        title=plan["name"],
        description=plan["description"],
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["name"], amount=stars_amount)],
        protect_content=False,
    )


# ── Star package (top-up) helpers ─────────────────────────────────────────────

def build_pkg_payload(user_id: int, pkg_id: str) -> str:
    """Payload for star-package top-up purchases: 'stars_{pkg_id}_{user_id}'"""
    return f"stars_{pkg_id}_{user_id}"


async def send_star_package_invoice(bot, chat_id: int, pkg_id: str, user_id: int) -> None:
    """
    Sends a Telegram Stars invoice for a star top-up package.
    User pays pkg['stars_paid'] Telegram Stars → bot credits pkg['stars_credited'].
    """
    pkg = STAR_PACKAGES[pkg_id]
    payload = build_pkg_payload(user_id, pkg_id)

    bonus_text = f" (+{pkg['bonus']} bonus)" if pkg["bonus"] > 0 else ""
    description = (
        f"Top up your balance with {pkg['stars_credited']} ⭐{bonus_text}. "
        f"Real value: {pkg['usd']}."
    )

    await bot.send_invoice(
        chat_id=chat_id,
        title=f"{pkg['name']}  ·  {pkg['stars_credited']} ⭐{bonus_text}",
        description=description,
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{pkg['stars_paid']} Stars", amount=pkg["stars_paid"])],
        protect_content=False,
    )
