"""
PhonePe Payment Gateway Integration for PixelBoost PropLeadAi
Supports PhonePe Standard Checkout (v1) with SHA256 checksum verification,
hosted payment page (UPI, QR, Cards, Netbanking), and automatic credit top-up.
"""

import os
import json
import base64
import hashlib
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("phonepe_gateway")

# PhonePe Credentials from Developer Settings
PHONEPE_MERCHANT_ID = os.getenv("PHONEPE_MERCHANT_ID", "M22SSI6NF7FT")
PHONEPE_CLIENT_ID = os.getenv("PHONEPE_CLIENT_ID", "SU2607031513498092434533")
PHONEPE_SALT_KEY = os.getenv("PHONEPE_SALT_KEY", "3b5f46ef-bf4c-416c-ba59-0ad837d53bb9")
PHONEPE_SALT_INDEX = int(os.getenv("PHONEPE_SALT_INDEX", "1"))
PHONEPE_ENV = os.getenv("PHONEPE_ENV", "PROD").upper()  # 'PROD' or 'UAT'

# Endpoints
PROD_BASE_URL = "https://api.phonepe.com/apis/hermes"
UAT_BASE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox"

def get_base_url() -> str:
    return PROD_BASE_URL if PHONEPE_ENV == "PROD" else UAT_BASE_URL

def calculate_checksum(payload_b64: str, api_endpoint: str) -> str:
    """Calculate SHA256 checksum header for PhonePe requests: sha256(b64 + endpoint + salt_key) + '###' + salt_index"""
    string_to_hash = payload_b64 + api_endpoint + PHONEPE_SALT_KEY
    sha256_hash = hashlib.sha256(string_to_hash.encode("utf-8")).hexdigest()
    return f"{sha256_hash}###{PHONEPE_SALT_INDEX}"

def verify_checksum(payload_b64: str, received_checksum: str, api_endpoint: str = "") -> bool:
    """Verify incoming PhonePe callback checksum."""
    try:
        calculated = calculate_checksum(payload_b64, api_endpoint)
        return calculated == received_checksum
    except Exception as e:
        logger.error(f"Checksum verification failed: {e}")
        return False

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
    Initiates a standard hosted checkout payment request with PhonePe.
    Returns checkout redirect URL or error.
    """
    import time
    import uuid

    # Unique Transaction ID
    txn_unique = uuid.uuid4().hex[:8].upper()
    merchant_txn_id = f"PL_{user_id}_{int(time.time())}_{txn_unique}"
    merchant_user_id = f"PB_USR_{user_id}"

    # Amount in Paise (INR to Paise)
    amount_paise = int(round(amount_inr * 100))

    redirect_url = f"{callback_base_url}/api/payment/phonepe/callback?txnId={merchant_txn_id}"
    webhook_url = f"{callback_base_url}/api/payment/phonepe/webhook"

    # Normalized phone
    clean_mobile = "9999999999"
    if mobile and len(mobile.replace("+91", "").strip()) == 10:
        clean_mobile = mobile.replace("+91", "").strip()

    payload = {
        "merchantId": PHONEPE_MERCHANT_ID,
        "merchantTransactionId": merchant_txn_id,
        "merchantUserId": merchant_user_id,
        "amount": amount_paise,
        "redirectUrl": redirect_url,
        "redirectMode": "POST",
        "callbackUrl": webhook_url,
        "mobileNumber": clean_mobile,
        "paymentInstrument": {
            "type": "PAY_PAGE"
        }
    }

    # Encode JSON to Base64
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("utf-8")

    api_endpoint = "/pg/v1/pay"
    x_verify = calculate_checksum(payload_b64, api_endpoint)

    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify,
        "accept": "application/json"
    }

    body = {
        "request": payload_b64
    }

    url = f"{get_base_url()}{api_endpoint}"
    logger.info(f"Initiating PhonePe payment for Txn: {merchant_txn_id}, Plan: {plan_name}, Amount: ₹{amount_inr}")

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(url, json=body, headers=headers)
            res_data = response.json()
            logger.info(f"PhonePe Init Response [{response.status_code}]: {res_data}")

            if res_data.get("success") is True:
                data = res_data.get("data", {})
                instrument_response = data.get("instrumentResponse", {})
                redirect_info = instrument_response.get("redirectInfo", {})
                pay_page_url = redirect_info.get("url")

                return {
                    "success": True,
                    "merchant_txn_id": merchant_txn_id,
                    "redirect_url": pay_page_url,
                    "amount_inr": amount_inr,
                    "plan_name": plan_name,
                    "leads_count": leads_count,
                    "status": "INITIATED"
                }
            else:
                error_msg = res_data.get("message", "Payment initiation failed with PhonePe.")
                return {
                    "success": False,
                    "error": error_msg,
                    "code": res_data.get("code", "ERROR"),
                    "merchant_txn_id": merchant_txn_id
                }
        except Exception as e:
            logger.error(f"Error calling PhonePe API: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to connect to PhonePe: {str(e)}",
                "merchant_txn_id": merchant_txn_id
            }

async def check_phonepe_order_status(merchant_txn_id: str) -> Dict[str, Any]:
    """
    Checks the real-time status of a PhonePe transaction from PhonePe Server.
    Endpoint: /pg/v1/status/{merchantId}/{merchantTransactionId}
    """
    api_endpoint = f"/pg/v1/status/{PHONEPE_MERCHANT_ID}/{merchant_txn_id}"
    string_to_hash = api_endpoint + PHONEPE_SALT_KEY
    sha256_hash = hashlib.sha256(string_to_hash.encode("utf-8")).hexdigest()
    x_verify = f"{sha256_hash}###{PHONEPE_SALT_INDEX}"

    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify,
        "X-MERCHANT-ID": PHONEPE_MERCHANT_ID,
        "accept": "application/json"
    }

    url = f"{get_base_url()}{api_endpoint}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, headers=headers)
            res_data = response.json()
            logger.info(f"PhonePe Status Check for {merchant_txn_id}: {res_data}")

            code = res_data.get("code", "")
            is_success = (res_data.get("success") is True) and (code == "PAYMENT_SUCCESS")

            return {
                "success": is_success,
                "code": code,
                "message": res_data.get("message", ""),
                "data": res_data.get("data", {})
            }
        except Exception as e:
            logger.error(f"Error checking PhonePe order status: {e}")
            return {
                "success": False,
                "code": "API_ERROR",
                "message": str(e)
            }
