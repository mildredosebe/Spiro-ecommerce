import base64
import requests
from datetime import datetime
from django.utils import timezone

MPESA_CONSUMER_KEY = "ydNuvXROVfX1yb23tz46rxneAMfeHGJlRCDzLoDeIQWqKzoA"
MPESA_CONSUMER_SECRET = "FD6Yo1WKkWaReMz39optPHTIrOzdaQVHdIg74tTUOT55yGoANg7g1W28F9KVz2GH"
MPESA_SHORTCODE = "174379"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919" 

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET)
    )

    if response.status_code != 200:
        raise Exception(f"Auth failed: {response.text}")

    return response.json()["access_token"]


def generate_password(shortcode, passkey, timestamp):
    data = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def stk_push(phone_number, amount, account_reference, transaction_desc, callback_url, payment):
    access_token = get_access_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = generate_password(
        MPESA_SHORTCODE,
        MPESA_PASSKEY,
        timestamp
    )

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    if "CheckoutRequestID" in data:
        payment.mpesa_checkout_request_id = data["CheckoutRequestID"]
        payment.merchant_request_id = data.get("MerchantRequestID")
        payment.status = "waiting_for_payment"
        payment.stk_push_initiated_at = timezone.now()
        payment.save()

    return data