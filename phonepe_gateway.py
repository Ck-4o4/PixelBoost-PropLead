"""
PhonePe Payment Gateway Integration for PixelBoost PropLeadAi
Supports PhonePe PG V2 with OAuth 2.0 authentication,
hosted payment page (UPI, QR, Cards, Netbanking), and automatic credit top-up.
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("phonepe_gateway")

# PhonePe Credentials from Developer Settings
PHONEPE_MERCHANT_ID = os.getenv("PHONEPE_MERCHANT_ID", "M22SSI6NF7FT")
PHONEPE_CLIENT_ID = os.getenv("PHONEPE_CLIENT_ID", "SU2607031513498092434533")
PHONEPE_CLIENT_SECRET = os.getenv("PHONEPE_SALT_KEY", "3b5f46ef-bf4c-416c-ba59-0ad837d53bb9")
PHONEPE_CLIENT_VERSION = os.getenv("PHONEPE_SALT_INDEX", "1")
PHONEPE_ENV = os.getenv("PHONEPE_ENV", "PROD").upper()  # 'PROD' or 'UAT'

# In-memory token cache
_cached_token = None
_token_expires_at = 0

async def get_phonepe_oauth_token() -> Optional[str]:
    """Fetch or return cached OAuth 2.0 access token from PhonePe Identity Manager."""
    global _cached_token, _token_expires_at

    now = time.time()
    if _cached_token and now < _token_expires_at:
        return _cached_token

    url = (
        "https://api.phonepe.com/apis/identity-manager/v1/oauth/token"
        if PHONEPE_ENV == "PROD"
        else "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token"
    )

    data = {
        "client_id": PHONEPE_CLIENT_ID,
        "client_version": PHONEPE_CLIENT_VERSION,
        "client_secret": PHONEPE_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, data=data, headers=headers)
            if res.status_code == 200:
                token_data = res.json()
                _cached_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                _token_expires_at = now + (expires_in - 120)  # Refresh 2 min early
                logger.info("PhonePe OAuth 2.0 Access Token refreshed successfully.")
                return _cached_token
            else:
                logger.error(f"PhonePe OAuth Token Error [{res.status_code}]: {res.text}")
                return None
    except Exception as e:
        logger.error(f"Failed to fetch PhonePe OAuth token: {e}", exc_info=True)
        return None

async def initiate_phonepe_payment(
    user_id: int,
    user_name: str,
    user_email: str,
    plan_name: str,
    leads_count: int,
    amount_inr: float,
    callback_base_url: str,
    mobile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initiates a standard hosted checkout payment request with PhonePe PG V2.
    Returns checkout redirect URL or error.
    """
    # Unique Transaction ID
    txn_unique = uuid.uuid4().hex[:8].upper()
    merchant_order_id = f"PL_{user_id}_{int(time.time())}_{txn_unique}"
    amount_paise = int(round(amount_inr * 100))

    redirect_url = f"{callback_base_url}/api/payment/phonepe/callback?txnId={merchant_order_id}"

    token = await get_phonepe_oauth_token()
    if not token:
        return {
            "success": False,
            "error": "Failed to authenticate with PhonePe Payment Gateway.",
            "merchant_txn_id": merchant_order_id
        }

    pay_url = (
        "https://api.phonepe.com/apis/pg/checkout/v2/pay"
        if PHONEPE_ENV == "PROD"
        else "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"
    )

    payload = {
        "merchantOrderId": merchant_order_id,
        "amount": amount_paise,
        "expireAfter": 1200,
        "paymentFlow": {
            "type": "PG_CHECKOUT",
            "merchantUrls": {
                "redirectUrl": redirect_url
            }
        },
        "metaInfo": {
            "user_id": str(user_id),
            "user_email": user_email,
            "plan_name": plan_name,
            "leads_count": str(leads_count)
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"O-Bearer {token}",
        "accept": "application/json"
    }

    logger.info(f"Initiating PhonePe V2 payment for Order: {merchant_order_id}, Plan: {plan_name}, Amount: ₹{amount_inr}")

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(pay_url, json=payload, headers=headers)
            res_data = response.json() if response.content else {}
            logger.info(f"PhonePe V2 Init Response [{response.status_code}]: {res_data}")

            if response.status_code in (200, 201) and res_data.get("redirectUrl"):
                return {
                    "success": True,
                    "merchant_txn_id": merchant_order_id,
                    "redirect_url": res_data.get("redirectUrl"),
                    "amount_inr": amount_inr,
                    "plan_name": plan_name,
                    "leads_count": leads_count,
                    "status": "INITIATED"
                }
            elif res_data.get("code") == "BLOCKED_MERCHANT":
                error_msg = (
                    "Your PhonePe Merchant Account (M22SSI6NF7FT) is pending activation or website approval by PhonePe. "
                    "Please ensure PG is enabled on your PhonePe Business dashboard or proceed via UPI / WhatsApp Concierge."
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "code": "BLOCKED_MERCHANT",
                    "merchant_txn_id": merchant_order_id
                }
            else:
                error_msg = res_data.get("message") or "PhonePe payment initiation failed."
                return {
                    "success": False,
                    "error": error_msg,
                    "code": res_data.get("code", "ERROR"),
                    "merchant_txn_id": merchant_order_id
                }
        except Exception as e:
            logger.error(f"Error calling PhonePe API: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to connect to PhonePe: {str(e)}",
                "merchant_txn_id": merchant_order_id
            }

async def check_phonepe_order_status(merchant_order_id: str) -> Dict[str, Any]:
    """
    Checks the real-time status of a PhonePe PG V2 transaction.
    Endpoint: /checkout/v2/order/{merchantOrderId}/status
    """
    token = await get_phonepe_oauth_token()
    if not token:
        return {"success": False, "code": "AUTH_ERROR", "message": "Could not authenticate with PhonePe"}

    status_url = (
        f"https://api.phonepe.com/apis/pg/checkout/v2/order/{merchant_order_id}/status"
        if PHONEPE_ENV == "PROD"
        else f"https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{merchant_order_id}/status"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"O-Bearer {token}",
        "accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(status_url, headers=headers)
            res_data = response.json() if response.content else {}
            logger.info(f"PhonePe V2 Status Check for {merchant_order_id}: {res_data}")

            state = res_data.get("state") or res_data.get("status") or ""
            is_success = state.upper() in ("COMPLETED", "SUCCESS", "PAYMENT_SUCCESS")

            return {
                "success": is_success,
                "code": state,
                "message": res_data.get("message", ""),
                "data": res_data
            }
        except Exception as e:
            logger.error(f"Error checking PhonePe order status: {e}")
            return {
                "success": False,
                "code": "API_ERROR",
                "message": str(e)
            }
