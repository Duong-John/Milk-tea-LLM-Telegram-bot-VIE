from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import menu_model, order_model
import config
import json

async def check_is_owner(update: Update) -> bool:
    if str(update.message.from_user.id) != config.OWNER_TELEGRAM_ID:
        await update.message.reply_text("Xin lỗi, bạn không có quyền truy cập lệnh này.")
        return False
    return True

async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    
    args = context.args
    # To handle spaces easily, we ask the shop owner to use underscores for the name: Tra_Sua_Mat_Cha
    if len(args) < 3:
        await update.message.reply_text("Sai cú pháp. Dùng: /add_item Tên_Món Giá_M Giá_L")
        return

    name = args[0].replace('_', ' ')
    try:
        price_m = int(args[1])
        price_l = int(args[2])
        desc = " ".join(args[3:]) if len(args) > 3 else ""
        
        menu_model.add_menu_item(name, price_m, price_l, desc)
        await update.message.reply_text(f"Đã thêm món: {name} ({price_m}đ, {price_l}đ)")
    except ValueError:
        await update.message.reply_text("Giá tiền phải là số nguyên.")

async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    
    if len(context.args) < 1:
        await update.message.reply_text("Thiếu ID món cần xoá: /delete_item <id>")
        return
    
    try:
        item_id = int(context.args[0])
        menu_model.delete_item(item_id)
        await update.message.reply_text(f"Đã xoá món có ID: {item_id}")
    except ValueError:
        await update.message.reply_text("ID phải là số.")

def _format_details(details_json):
    try:
        details = json.loads(details_json)
        res = ""
        for d in details:
            item_name = d["item"].get("name", "Unknown")
            size = d["item"].get("size", "M")
            qty = d.get("quantity", 1)
            res += f"\n    + {qty}x {item_name} (Size {size})"
        return res
    except Exception:
        return "Lỗi hiển thị chi tiết"

async def view_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    
    pending_orders = order_model.get_orders_by_status("PENDING")
    paid_orders = order_model.get_orders_by_status("PAID")
    
    message = "**Đơn hàng chờ thanh toán (PENDING):**\n"
    if not pending_orders:
        message += "Không có đơn.\n"
    else:
        for o in pending_orders:
            details_str = _format_details(o['order_details'])
            message += f"- Đơn #{o['id']} ({o.get('order_name', '')})\n"
            message += f"  Người nhận: {o.get('recipient_name', 'Chưa có')} | Giao: {o.get('delivery_time', 'Chưa có')}\n"
            message += f"  Tổng: {o['total_amount']}đ\n"
            message += f"  Chi tiết: {details_str}\n\n"
        
    message += "**Đơn hàng đã thanh toán (PAID):**\n"
    if not paid_orders:
        message += "Không có đơn.\n"
    else:
        for o in paid_orders:
            details_str = _format_details(o['order_details'])
            message += f"- Đơn #{o['id']} ({o.get('order_name', '')}) -> Prep: {o.get('preparation_status', '')}\n"
            message += f"  Người nhận: {o.get('recipient_name', 'Chưa có')} | Giao: {o.get('delivery_time', 'Chưa có')}\n"
            message += f"  Tổng: {o['total_amount']}đ\n"
            message += f"  Chi tiết: {details_str}\n\n"
        
    await update.message.reply_text(message)

async def mark_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    if len(context.args) < 1:
        await update.message.reply_text("Thiếu ID đơn. Cú pháp: /mark_ready <order_id_hoặc_order_name>")
        return
    arg = context.args[0]
    
    if "_" in arg:
        order = order_model.get_order_by_name(arg)
    else:
        try:
            order_id = int(arg)
            order = order_model.get_order_by_id(order_id)
        except ValueError:
            await update.message.reply_text("ID đơn phải là số hoặc đúng định dạng order_name.")
            return
            
    if not order:
        await update.message.reply_text(f"Không tìm thấy đơn hàng {arg}.")
        return
        
    if order['status'] != 'PAID':
        await update.message.reply_text(f"Lỗi: Đơn hàng {arg} đang ở trạng thái {order['status']} (chưa thanh toán). Không thể đánh dấu READY!")
        return
        
    if "_" in arg:
        success = order_model.update_preparation_status_by_name(arg, "READY")
    else:
        success = order_model.update_preparation_status(int(arg), "READY")
            
    if success:
        await update.message.reply_text(f"Đã cập nhật đơn hàng {arg} thành READY!")
    else:
        await update.message.reply_text(f"Không tìm thấy đơn hàng {arg} để cập nhật.")

async def delete_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    if len(context.args) < 1:
        await update.message.reply_text("Thiếu ID đơn. Cú pháp: /delete_order <order_id_hoặc_order_name>")
        return
    arg = context.args[0]
    
    if "_" in arg:
        success = order_model.delete_order_by_name(arg)
    else:
        try:
            order_id = int(arg)
            success = order_model.delete_order_by_id(order_id)
        except ValueError:
            await update.message.reply_text("ID đơn phải là số hoặc đúng định dạng order_name.")
            return

    if success:
        await update.message.reply_text(f"Đã xoá đơn hàng {arg} thành công.")
    else:
        await update.message.reply_text(f"Không tìm thấy đơn hàng {arg}.")

async def delete_all_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    count = order_model.delete_orders_by_status("PAID")
    await update.message.reply_text(f"Đã xoá toàn bộ {count} đơn hàng đã thanh toán (PAID).")

async def delete_all_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_is_owner(update): return
    count = order_model.delete_orders_by_status("PENDING")
    await update.message.reply_text(f"Đã xoá toàn bộ {count} đơn hàng chờ thanh toán (PENDING).")

def get_admin_handlers():
    return [
        CommandHandler("add_item", add_item),
        CommandHandler("delete_item", delete_item),
        CommandHandler("view_orders", view_requests),
        CommandHandler("delete_order", delete_order),
        CommandHandler("delete_all_paid", delete_all_paid),
        CommandHandler("delete_all_pending", delete_all_pending),
        CommandHandler("mark_ready", mark_ready)
    ]
