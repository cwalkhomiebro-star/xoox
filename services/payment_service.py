from config import WALLET_ADDRESS, PRICING_PLANS

def get_payment_instructions(plan_id):
    """Generates the payment message and instructions for a selected plan."""
    if plan_id not in PRICING_PLANS:
        return "Invalid plan selected."
    
    plan_info = PRICING_PLANS[plan_id]
    
    instructions = (
        f"<b>🛒 Purchase: {plan_info['name']}</b>\n\n"
        f"💰 <b>Amount:</b> ${plan_info['price']} USDT (TRC20)\n"
        f"🏦 <b>Wallet Address:</b>\n"
        f"<code>{WALLET_ADDRESS}</code>\n\n"
        f"⚠️ <b>Important:</b>\n"
        f"- Send the EXACT amount mentioned above.\n"
        f"- Ensure you use the <b>USDT (TRC20)</b> network.\n"
        f"- After successful payment, click the <b>'I Have Paid'</b> button below."
    )
    
    return instructions

def verify_crypto_payment_placeholder(user_id, amount):
    """
    Placeholder for future crypto API integration (e.g., NowPayments, Coinbase, etc.).
    Currently, we return None as payments are processed via the automated system.
    """
    # Logic to check on-chain transaction would go here
    return None
