import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters
from llm import agent
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    # Wipe stale history and cart so the LLM starts completely fresh
    from sessions import cache
    cache.clear_history(user_id)
    cache.clear_cart(user_id)
    welcome = "Chị chào em đến trang đặt trà sữa của mẹ. Hôm nay em muốn uống gì em nhỉ?"
    await update.message.reply_text(welcome)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    response_text = await agent.process_user_message(user_id, text)
    
    match = re.search(r"\[CHECKOUT_ORDER\]\s*([\w\d_]+)", response_text, re.IGNORECASE)
    if match:
        order_str = match.group(1).strip()
        
        clean_text = re.sub(r"\[CHECKOUT_ORDER\]\s*[\w\d_]+", "", response_text, flags=re.IGNORECASE).strip()
        if clean_text:
            await update.message.reply_text(clean_text)
        
        from database import order_model
        from services import payos_service
        
        # The LLM might output '12' or '7658298727_12'
        if "_" in order_str:
            order = order_model.get_order_by_name(order_str)
        else:
            try:
                order = order_model.get_order_by_id(int(order_str))
            except ValueError:
                order = None

        if order and order['total_amount'] > 0:
            order_id = order['id']
            cart_total = order['total_amount']
            payment_info, order_code = payos_service.create_payment_link(order_id, cart_total, f"Thanh toan don {order_id}")
            
            if order_code:
                order_model.update_payos_order_code(order_id, order_code)

            if payment_info and hasattr(payment_info, 'checkoutUrl'):
                qr_message = f"Link thanh toán của Đơn Hàng #{order_id} đây nhé: {payment_info.checkoutUrl}\nSau khi thanh toán xong hệ thống sẽ lên đơn chuẩn bị cho em nha!"
            else:
                qr_message = f"À xin lỗi chị đang không tạo được mã QR, nhưng đơn của em là {cart_total}đ nhé (ID Đơn Hàng #{order_id})."
            
            await update.message.reply_text(qr_message)
        else:
            await update.message.reply_text("Chị không tìm thấy đơn hàng này hoặc đơn hàng bị lỗi!")
    else:
        await update.message.reply_text(response_text)

def get_customer_handlers():
    return [
        CommandHandler("start", start),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    ]
