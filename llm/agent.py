import json
import logging
import litellm
import config
from . import tools
from sessions import cache

# For openai endpoints using litellm
import os
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY if config.OPENAI_API_KEY else ""

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Bạn là một người mẹ hiền lành, chủ tiệm trà sữa, xưng hô là "Chị" và gọi khách hàng là "em".
Phong cách nói chuyện: ấm áp, gần gũi, hay dùng từ đệm như "nhé", "nha", "đợi chị xíu nhé".
Luôn trả lời bằng tiếng Việt tự nhiên và không quá trang trọng, bình dân nhưng vẫn dễ thương.

NGUYÊN TẮC CHỐNG ẢO GIÁC (BẮT BUỘC!!!):
- TUYỆT ĐỐI KHÔNG NHỚ GIỎ HÀNG HAY ĐƠN HÀNG BẰNG TRÍ NHỚ CỦA BẠN! Bạn PHẢI đọc CHÍNH XÁC thông tin "Tình trạng Giỏ hàng Mới hiện tại" mà hệ thống cung cấp ở đầu mỗi lượt.
- Nếu muốn biết đơn cũ (PENDING/PAID), PHẢI GỌI `check_user_orders`. Không bao giờ trả lời "em đang có đơn tương tự" nếu bạn chưa gọi tool kiểm tra!
- Khi khách thêm món, GỌI `add_to_cart` NGAY LẬP TỨC, không nói "chị thêm vào nha" rồi quên gọi tool!

Nhiệm vụ Quản Lý Giỏ Hàng Mới (DRAFT):
1. Dùng `get_menu` để xem menu. CẤM BỊA MÓN HAY BỊA item_id. Nếu không nhớ tên món, PHẢI gọi `get_menu`!
2. Dùng `add_to_cart` để thêm món vào Giỏ Hàng Mới (DRAFT). Mặc định số lượng là 1 nếu khách nói "Cho 1 ly...". NẾU KHÁCH CHƯA NÓI SỐ LƯỢNG (Ví dụ "Cho em Trà xanh"), BẠN PHẢI HỎI lại khách. Dùng `remove_from_cart` để bỏ món.
3. Tuyệt đối KHÔNG tự ý hối thúc khách chốt đơn, không xin tên/giờ giao nếu khách chỉ đang thêm món. Phải đợi khách chủ động bảo "Lên đơn" hoặc "Chốt đơn".
4. LƯU LÊN ĐƠN GỐC: Chỉ khi khách muốn chốt giỏ DRAFT, BẠN BẮT BUỘC HỎI Tên và Thời gian giao hàng rồi MỚI gọi `finalize_draft_order`. Sau khi dọi tool này xong, KHÔNG XUẤT MÃ QR LUÔN! Chỉ báo: "Chị đã lưu lại Đơn (mã ID). Em muốn tính tiền luôn không?".

Nhiệm vụ Quản Lý Đơn Cũ (Đã Lưu PENDING/PAID):
1. BƯỚC THANH TOÁN (LẤY MÃ QR):
   - Nếu khách vừa lưu đơn xong và nói "Thanh toán luôn": TUYỆT ĐỐI KHÔNG GỌI LẠI `finalize_draft_order` vì giỏ DRAFT đã trống! Bạn CHỈ CẦN XUẤT RA DUY NHẤT LỆNH: `[CHECKOUT_ORDER] X` (X là mã ID của đơn vừa tạo).
   - Nếu khách yêu cầu thanh toán một đơn PENDING cũ (ví dụ: "chị tính tiền đơn 25 cho em"): Bạn cũng CHỈ XUẤT DUY NHẤT LỆNH: `[CHECKOUT_ORDER] X`. KHÔNG ĐƯỢC HỎI LẠI TÊN!
2. Khách muốn thêm/bớt món vào Đơn Số X (PENDING): Dùng `modify_pending_order`. Truyền trực tiếp TÊN MÓN bằng Tiếng Việt (item_name) thay vì ID!
3. Đổi thông tin: Dùng `update_order_info(order_id, name, time)`. Chuyển món: Dùng `transfer_item(from, to, item_name, size, qty)`. Xoá hẳn đơn: Dùng `cancel_pending_order(order_id)`.
4. Trạng thái: Dùng `check_user_orders` để xem đơn PENDING/PAID. Đơn ĐÃ PAID thì cấm gọi modify_pending_order. Dùng `check_preparation_status` xem đồ uống xong chưa.
"""

async def process_user_message(customer_tg_id: str, text: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    cart_total = cache.get_cart_total(customer_tg_id)
    session = cache.get_session(customer_tg_id)
    
    cart_ctx = "Giỏ hàng MỚI (DRAFT) của em:\n"
    if len(session['cart']) == 0:
        cart_ctx += "Chưa có món nào.\n"
    else:
        for c in session['cart']:
            cart_ctx += f"- {c['quantity']}x {c['item']['name']} (Size {c['item'].get('size')}, ID: {c['item']['id']})\n"
        cart_ctx += f"Tổng tiền: {cart_total}đ\n"
        
    messages.append({"role": "system", "content": f"Tình trạng Giỏ hàng Mới hiện tại:\n{cart_ctx}"})
    for msg in session.get("history", []): messages.append(msg)
    user_msg = {"role": "user", "content": text}
    messages.append(user_msg)
    cache.append_history(customer_tg_id, user_msg)

    available_tools = [
        tools.get_menu_schema(),
        tools.add_to_cart_schema(),
        tools.remove_from_cart_schema(),
        tools.check_user_orders_schema(),
        tools.finalize_draft_order_schema(),
        tools.update_order_info_schema(),
        tools.modify_pending_order_schema(),
        tools.transfer_item_schema(),
        tools.check_preparation_status_schema(),
        tools.cancel_pending_order_schema()
    ]
    
    try:
        for _ in range(4):
            response = await litellm.acompletion(
                model="gpt-4o-mini",
                api_key=config.OPENAI_API_KEY,
                messages=messages,
                tools=available_tools,
                tool_choice="auto"
            )
            response_message = response.choices[0].message
            
            if not response_message.tool_calls:
                final_content = response_message.content or ""
                cache.append_history(customer_tg_id, {"role": "assistant", "content": final_content})
                return final_content
            
            messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except Exception:
                    arguments = {}
                    
                func_result = "Unknown function"
                if function_name == "get_menu": func_result = tools.execute_get_menu()
                elif function_name == "add_to_cart": func_result = tools.execute_add_to_cart(customer_tg_id, arguments.get("item_name"), arguments.get("size"), arguments.get("quantity", 1))
                elif function_name == "remove_from_cart": func_result = tools.execute_remove_from_cart(customer_tg_id, arguments.get("item_name"), arguments.get("size"))
                elif function_name == "check_user_orders": func_result = tools.execute_check_user_orders(customer_tg_id)
                elif function_name == "finalize_draft_order": func_result = tools.execute_finalize_draft_order(customer_tg_id, arguments.get("recipient_name"), arguments.get("delivery_time"))
                elif function_name == "update_order_info": func_result = tools.execute_update_order_info(arguments.get("order_id"), arguments.get("recipient_name"), arguments.get("delivery_time"))
                elif function_name == "modify_pending_order": func_result = tools.execute_modify_pending_order(arguments.get("order_id"), arguments.get("action"), arguments.get("item_name"), arguments.get("size"), arguments.get("quantity"))
                elif function_name == "transfer_item": func_result = tools.execute_transfer_item(arguments.get("from_order_id"), arguments.get("to_order_id"), arguments.get("item_name"), arguments.get("size"), arguments.get("quantity"))
                elif function_name == "check_preparation_status": func_result = tools.execute_check_preparation_status(arguments.get("order_id"))
                elif function_name == "cancel_pending_order": func_result = tools.execute_cancel_pending_order(arguments.get("order_id"))
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": str(func_result)
                })
        
        return "Chị đang bận xíu, em nhắn lại sau nha!"
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return "Chị đang bận xíu, em chờ xíu giúp chị nha!"
