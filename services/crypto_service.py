import logging
import requests
from config import WALLET_ADDRESS, PRICING_PLANS

logger = logging.getLogger(__name__)

def verify_trc20_txid(txid: str, expected_plan_id: str) -> dict:
    """
    Verifies a TRC20 transaction using TronScan API.
    Returns:
    {
        "status": "success" | "failed" | "pending" | "invalid" | "not_found",
        "message": "Human readable reason",
        "amount": 50.0 # if found
    }
    """
    if expected_plan_id not in PRICING_PLANS:
        return {"status": "invalid", "message": "Invalid plan selected"}
        
    expected_amount = PRICING_PLANS[expected_plan_id]["price"]
    
    url = f"https://apilist.tronscan.org/api/transaction-info?hash={txid}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return {"status": "not_found", "message": "Could not contact TronScan or transaction not found."}
            
        data = response.json()
        
        # If transaction doesn't exist
        if not data or "contractRet" not in data:
            return {"status": "not_found", "message": "Transaction not found on the blockchain."}
            
        if data["contractRet"] != "SUCCESS":
            return {"status": "failed", "message": "Transaction failed on the blockchain."}
            
        # Look for TRC20 transfer matching our criteria
        transfers = data.get("trc20TransferInfo", [])
        if not transfers:
            return {"status": "invalid", "message": "No TRC20 transfer found in this transaction."}
            
        for t in transfers:
            symbol = t.get("symbol", "").upper()
            to_addr = t.get("to_address", "")
            amount_str = t.get("amount_str", "0")
            decimals = int(t.get("decimals", 6))
            
            # Allow some flexibility on token symbol if it's USDT
            if "USDT" in symbol and to_addr == WALLET_ADDRESS:
                actual_amount = float(amount_str) / (10 ** decimals)
                if actual_amount >= expected_amount * 0.99: # 1% tolerance
                    return {"status": "success", "message": "Payment verified!", "amount": actual_amount}
                else:
                    return {"status": "invalid", "message": f"Payment amount too low. Expected {expected_amount}, found {actual_amount}."}
                    
        return {"status": "invalid", "message": "Transaction does not contain a transfer to our wallet address."}

    except Exception as e:
        logger.error(f"Error verifying TxID {txid}: {e}")
        return {"status": "pending", "message": "Error verifying transaction. Please try again later."}
