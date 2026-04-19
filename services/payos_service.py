import os
import time
import logging
from payos import PayOS
from payos.type import ItemData, PaymentData
import config

logger = logging.getLogger(__name__)

payos_client = None

if config.PAYOS_CLIENT_ID and config.PAYOS_API_KEY and config.PAYOS_CHECKSUM_KEY:
    payos_client = PayOS(
        client_id=config.PAYOS_CLIENT_ID,
        api_key=config.PAYOS_API_KEY,
        checksum_key=config.PAYOS_CHECKSUM_KEY
    )

def create_payment_link(order_id: int, amount: int, description: str):
    if not payos_client:
        logger.error("PayOS config is missing. Cannot generate payment.")
        return None, None

    desc = description[:25]
    item = ItemData(name=f"Don hang {order_id}", quantity=1, price=amount)
    
    # Ensure a unique integer identifier for PayOS (combination of time and order_id)
    order_code = int(f"{int(time.time()) % 1000}{order_id}")
    
    payment_data = PaymentData(
        orderCode=order_code,
        amount=amount,
        description=desc,
        items=[item],
        cancelUrl="https://web.telegram.org/",
        returnUrl="https://web.telegram.org/"
    )
    
    try:
        payment_link = payos_client.createPaymentLink(payment_data)
        return payment_link, order_code
    except Exception as e:
        logger.error(f"PayOS Error: {e}")
        return None, None

def get_payment_status(order_code: int):
    if not payos_client: return None
    try:
        payment_info = payos_client.getPaymentLinkInformation(order_code)
        return payment_info.status
    except Exception as e:
        logger.error(f"Error checking PayOS status: {e}")
        return None
