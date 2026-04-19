from database import menu_model, order_model
from sessions import cache
import json

def _find_item(query):
    """Resolve a menu item by ID or name. Prefers exact matches, then shortest substring match."""
    items = menu_model.get_all_items()
    if str(query).isdigit():
        return next((i for i in items if i["id"] == int(query)), None)
    q = str(query).lower().strip()
    # 1. Exact match first
    exact = next((i for i in items if i["name"].lower() == q), None)
    if exact:
        return exact
    # 2. Substring matches — pick the shortest name (closest semantic match)
    #    e.g. "Trân Châu Đen" should match "Trân Châu Đen" (len=14) not "Trà Sữa Trân Châu Đen" (len=22)
    candidates = [i for i in items if q in i["name"].lower()]
    if candidates:
        candidates.sort(key=lambda i: len(i["name"]))
        return candidates[0]
    return None

def get_menu_schema():
    return {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Fetch the current available menu items.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }

def add_to_cart_schema():
    return {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add an item to the DRAFT cart (a brand new order being built).",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Tên món hoặc ID. Ví dụ: 'Bột Trà Xanh'"},
                    "size": {"type": "string", "enum": ["M", "L"]},
                    "quantity": {"type": "integer"}
                },
                "required": ["item_name", "size", "quantity"]
            }
        }
    }

def remove_from_cart_schema():
    return {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove an item from the DRAFT cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Tên món hoặc ID. Ví dụ: 'Bột Trà Xanh'"},
                    "size": {"type": "string", "enum": ["M", "L"]},
                    "quantity": {"type": "integer"}
                },
                "required": ["item_name", "size", "quantity"]
            }
        }
    }

def cancel_pending_order_schema():
    return {
        "type": "function",
        "function": {
            "name": "cancel_pending_order",
            "description": "Cancel/Delete an entire PENDING order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"}
                },
                "required": ["order_id"]
            }
        }
    }

def check_user_orders_schema():
    return {
        "type": "function",
        "function": {"name": "check_user_orders", "description": "Check order history and statuses", "parameters": {"type": "object", "properties": {}}}
    }

def finalize_draft_order_schema():
    return {
        "type": "function",
        "function": {
            "name": "finalize_draft_order",
            "description": "Save the DRAFT cart as a PENDING order under the provided recipient name and delivery time. Call this when customer wants to check out a newly built cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_name": {"type": "string"},
                    "delivery_time": {"type": "string"}
                },
                "required": ["recipient_name", "delivery_time"]
            }
        }
    }

def update_order_info_schema():
    return {
        "type": "function",
        "function": {
            "name": "update_order_info",
            "description": "Update recipient name or delivery time for an existing order (PAID or PENDING).",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "recipient_name": {"type": "string"},
                    "delivery_time": {"type": "string"}
                },
                "required": ["order_id", "recipient_name", "delivery_time"]
            }
        }
    }

def modify_pending_order_schema():
    return {
        "type": "function",
        "function": {
            "name": "modify_pending_order",
            "description": "Add or remove items from a PENDING order. Not allowed on PAID orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "action": {"type": "string", "enum": ["add", "remove"]},
                    "item_name": {"type": "string", "description": "Tên món hoặc ID. Ví dụ: 'Bột Trà Xanh'"},
                    "size": {"type": "string", "enum": ["M", "L"]},
                    "quantity": {"type": "integer"}
                },
                "required": ["order_id", "action", "item_name", "size", "quantity"]
            }
        }
    }

def transfer_item_schema():
    return {
        "type": "function",
        "function": {
            "name": "transfer_item",
            "description": "Transfer an item from one PENDING order to another PENDING order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_order_id": {"type": "integer"},
                    "to_order_id": {"type": "integer"},
                    "item_name": {"type": "string", "description": "Tên món hoặc ID. Ví dụ: 'Bột Trà Xanh'"},
                    "size": {"type": "string", "enum": ["M", "L"]},
                    "quantity": {"type": "integer"}
                },
                "required": ["from_order_id", "to_order_id", "item_name", "size", "quantity"]
            }
        }
    }

def check_preparation_status_schema():
    return {
        "type": "function",
        "function": {
            "name": "check_preparation_status",
            "description": "Check if an order is PREPARING or READY.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"}
                },
                "required": ["order_id"]
            }
        }
    }

# ----------------- EXECUTIONS -----------------

def execute_get_menu():
    items = menu_model.get_all_items(only_available=True)
    if not items: return "Menu is currently empty."
    return "\n".join([f"- {item['name']} (ID: {item['id']}): M={item['price_m']}đ, L={item['price_l']}đ" for item in items])

def execute_add_to_cart(customer_tg_id, item_name, size="M", quantity=1):
    item_dict = _find_item(item_name)
    if not item_dict:
        return f"Error: Menu item '{item_name}' not found. Did you misspell it? Please use get_menu."
    
    new_item = item_dict.copy()
    new_item["size"] = size
    cache.add_to_cart(customer_tg_id, new_item, quantity)
    return f"Successfully added {quantity}x {new_item['name']} (Size {size}) to draft cart."

def execute_remove_from_cart(customer_tg_id, item_name, size):
    item_dict = _find_item(item_name)
    if not item_dict: return f"Error: Item {item_name} not found."
    removed = cache.remove_from_cart(customer_tg_id, item_dict['id'], size)
    return f"Removed {item_dict['name']} from draft cart." if removed else "Item not found in draft cart."

def execute_cancel_pending_order(order_id):
    o = order_model.get_order_by_id(order_id)
    if not o: return "Order not found."
    if o['status'] == 'PAID': return "Error: Cannot cancel an order that is already PAID."
    success = order_model.delete_order_by_id(order_id)
    return f"Successfully cancelled Order {order_id}." if success else "Failed to delete order."

def _format_details_short(details_json):
    try:
        details = json.loads(details_json)
        return ", ".join([f"{d['quantity']}x {d['item']['name']} (Size {d['item'].get('size', 'M')}, ID: {d['item']['id']})" for d in details])
    except:
        return "Lỗi hiển thị"

def execute_check_user_orders(customer_tg_id):
    orders = order_model.get_orders_by_customer(customer_tg_id)
    if not orders: return "Customer has no order history."
    res = "Customer Order History:\n"
    for o in orders[:5]:
        det = _format_details_short(o['order_details'])
        res += f"- Order {o['id']} ({o['order_name']}) | Amount: {o['total_amount']} | Payment: {o['status']} | Delivery: {o['delivery_time']} cho {o['recipient_name']} | Prep: {o['preparation_status']} | Items: {det}\n"
    return res

def execute_finalize_draft_order(customer_tg_id, recipient, time):
    cart_total = cache.get_cart_total(customer_tg_id)
    session = cache.get_session(customer_tg_id)
    if cart_total <= 0: return "DRAFT cart is empty. Nothing to finalize."
    
    cart_json = json.dumps(session['cart'], ensure_ascii=False)
    order_id, order_name = order_model.finalize_draft_to_order(customer_tg_id, cart_json, cart_total, recipient, time)
    cache.clear_cart(customer_tg_id)
    return f"SUCCESS_ORDER_ID:{order_id}"

def execute_update_order_info(order_id, name, time):
    success = order_model.update_order_info(order_id, name, time)
    return "Updated delivery info." if success else "Order not found."

def _recalc_total(details_list):
    tot = 0
    for c in details_list:
        p = c["item"].get("price_m", 0) if c["item"].get("size") == "M" else c["item"].get("price_l", 0)
        tot += p * c["quantity"]
    return tot

def execute_modify_pending_order(order_id, action, item_name, size, quantity):
    order = order_model.get_order_by_id(order_id)
    if not order: return "Order not found."
    if order['status'] == 'PAID': return "Error: Cannot modify an order that has already been PAID."
    
    details = json.loads(order['order_details'])
    item_data = _find_item(item_name)
    if not item_data: return "Error: Menu item not found."
    item_id = item_data['id']
    
    if action == "add":
        new_item = item_data.copy()
        new_item["size"] = size
        details.append({"item": new_item, "quantity": quantity})
    elif action == "remove":
        new_det = []
        to_remove = quantity
        for d in details:
            if d["item"]["id"] == item_id and d["item"]["size"] == size and to_remove > 0:
                if d["quantity"] > to_remove:
                    d["quantity"] -= to_remove
                    new_det.append(d)
                    to_remove = 0
                else:
                    to_remove -= d["quantity"]
            else:
                new_det.append(d)
        details = new_det
        if to_remove > 0:
            return f"Error: Could not remove {quantity} items. Item not found or quantity too low."
        
    new_tot = _recalc_total(details)
    order_model.modify_order_items(order_id, json.dumps(details, ensure_ascii=False), new_tot)
    return f"Successfully {action}ed items to Order ID {order_id}. New total: {new_tot}đ."

def execute_transfer_item(from_id, to_id, item_name, size, qty):
    o1 = order_model.get_order_by_id(from_id)
    o2 = order_model.get_order_by_id(to_id)
    if not o1 or not o2: return "Order not found."
    if o1['status'] == 'PAID' or o2['status'] == 'PAID': return "Cannot transfer items involving a PAID order."
    
    item_resolved = _find_item(item_name)
    if not item_resolved: return "Menu item not found."
    item_id = item_resolved['id']
    
    det1 = json.loads(o1['order_details'])
    found = False
    new_det1 = []
    item_data = None
    to_transfer = qty
    for d in det1:
        if d["item"]["id"] == item_id and d["item"]["size"] == size and to_transfer > 0:
            found = True
            item_data = d["item"]
            if d["quantity"] > to_transfer:
                d["quantity"] -= to_transfer
                new_det1.append(d)
                to_transfer = 0
            else:
                to_transfer -= d["quantity"]
        else:
            new_det1.append(d)
    
    if not found or to_transfer > 0: 
        return f"Error: Could not transfer, not enough quantity found."
    
    det2 = json.loads(o2['order_details'])
    added = False
    for d in det2:
        if d["item"]["id"] == item_id and d["item"]["size"] == size:
            d["quantity"] += qty
            added = True
            break
    
    if not added:
        det2.append({"item": item_data, "quantity": qty}) 
    
    order_model.modify_order_items(from_id, json.dumps(new_det1, ensure_ascii=False), _recalc_total(new_det1))
    order_model.modify_order_items(to_id, json.dumps(det2, ensure_ascii=False), _recalc_total(det2))
    
    return f"Successfully transferred item from Order {from_id} to {to_id}."

def execute_check_preparation_status(order_id):
    o = order_model.get_order_by_id(order_id)
    if not o: return "Order not found."
    return f"Order {order_id} prep status is: {o['preparation_status']}"
