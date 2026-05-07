from config import WALLET_ADDRESS, PRICING_PLANS
from utils.i18n import get_text

def get_payment_instructions(plan_id, lang="en"):
    """Generates the payment message and instructions for a selected plan."""
    if plan_id not in PRICING_PLANS:
        return get_text("plan_not_found", lang)
    
    plan_info = PRICING_PLANS[plan_id]
    plan_name = get_text(f"plan_{plan_id}_name", lang)
    
    return get_text(
        "crypto_payment_instructions", 
        lang, 
        plan_name=plan_name, 
        price=plan_info['price'], 
        wallet_address=WALLET_ADDRESS
    )
