"""
Lightweight in-memory cache to manage current user orders before they are saved to DB.
"""

# Structure: { customer_tg_id: {"cart": [{"item": dict, "quantity": 1}], "state": "ordering"} }
_user_sessions = {}

def get_session(customer_tg_id):
    if customer_tg_id not in _user_sessions:
        _user_sessions[customer_tg_id] = {
            "cart": [],
            "state": "ordering",
            "history": []
        }
    return _user_sessions[customer_tg_id]

def append_history(customer_tg_id, message_dict):
    session = get_session(customer_tg_id)
    session["history"].append(message_dict)
    # limit to last 10 elements to prevent stale context pollution
    if len(session["history"]) > 10: 
        session["history"] = session["history"][-10:]

def clear_history(customer_tg_id):
    """Wipe conversation history so the LLM starts fresh with no ghost memory."""
    session = get_session(customer_tg_id)
    session["history"] = []

def add_to_cart(customer_tg_id, item_dict, quantity=1):
    session = get_session(customer_tg_id)
    session["cart"].append({"item": item_dict, "quantity": quantity})

def remove_from_cart(customer_tg_id, item_id, size):
    session = get_session(customer_tg_id)
    new_cart = []
    removed = False
    for c in session["cart"]:
        if c["item"]["id"] == item_id and c["item"].get("size") == size:
            removed = True
        else:
            new_cart.append(c)
    session["cart"] = new_cart
    return removed

def clear_cart(customer_tg_id):
    if customer_tg_id in _user_sessions:
        _user_sessions[customer_tg_id]["cart"] = []

def get_cart_total(customer_tg_id):
    session = get_session(customer_tg_id)
    total = 0
    for cart_item in session["cart"]:
        item = cart_item["item"]
        size = item.get("size", "M")
        price = item.get("price_m", 0) if size == "M" else item.get("price_l", 0)
        total += price * cart_item["quantity"]
    return total

def update_session_state(customer_tg_id, state):
    session = get_session(customer_tg_id)
    session["state"] = state
