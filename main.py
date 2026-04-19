import logging
from telegram.ext import ApplicationBuilder

from flask import Flask
import os
import threading

import config
from bot.handlers import get_customer_handlers
from owner.admin_handlers import get_admin_handlers
from database.db import init_db
from database import order_model
from services import payos_service

app = Flask(__name__)

@app.route('/')
def home():
    return "Mẹ AI đang thức và sẵn sàng bán trà sữa!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# -----------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def poll_payments(context):
    try:
        pending_orders = order_model.get_orders_by_status("PENDING")
        for order in pending_orders:
            p_code = order.get('payos_order_code')
            if not p_code: 
                continue
            status = payos_service.get_payment_status(p_code)
            if status == "PAID":
                order_model.update_order_status(order['id'], "PAID")
                logger.info(f"Order #{order['id']} marked as PAID from PayOS webhook/polling.")
    except Exception as e:
        logger.error(f"Error polling payments: {e}")

def main():
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram token provided. Vui lòng thêm vào file .env. Exiting.")
        return

    # Khởi tạo DB khi khởi động bot
    logger.info("Initializing database...")
    init_db()

    # --- Initialize Flask in a thread ---
    logger.info("Starting Flask server for Render...")
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add Admin Commands
    for handler in get_admin_handlers():
        application.add_handler(handler)

    # Add Customer Commands and LLM Chat Handler
    for handler in get_customer_handlers():
        application.add_handler(handler)
    
    # Add Polling Job for pending payments (every 15 seconds)
    application.job_queue.run_repeating(poll_payments, interval=15, first=5)
    
    logger.info("Starting Telegram Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
