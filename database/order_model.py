import sqlite3
from .db import get_connection

def finalize_draft_to_order(customer_tg_id, order_details_json, total_amount, recipient_name, delivery_time):
    conn = get_connection()
    cursor = conn.cursor()
    # Temporarily insert without order_name
    cursor.execute('''
        INSERT INTO orders (order_name, customer_tg_id, recipient_name, delivery_time, order_details, total_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('temp', customer_tg_id, recipient_name, delivery_time, order_details_json, total_amount, 'PENDING'))
    order_id = cursor.lastrowid
    
    order_name = f"{customer_tg_id}_{order_id}"
    cursor.execute('UPDATE orders SET order_name = ? WHERE id = ?', (order_name, order_id))
    
    conn.commit()
    conn.close()
    return order_id, order_name

def update_order_info(order_id, recipient_name, delivery_time):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders 
        SET recipient_name = ?, delivery_time = ? 
        WHERE id = ?
    ''', (recipient_name, delivery_time, order_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def modify_order_items(order_id, new_details_json, new_total):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders 
        SET order_details = ?, total_amount = ? 
        WHERE id = ?
    ''', (new_details_json, new_total, order_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def update_preparation_status(order_id, prep_status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders SET preparation_status = ? WHERE id = ?
    ''', (prep_status, order_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def update_preparation_status_by_name(order_name, prep_status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders SET preparation_status = ? WHERE order_name = ?
    ''', (prep_status, order_name))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def update_order_status(order_id, status):
    """Status could be: PENDING, PAID, DELIVERED, CANCELLED"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders SET status = ? WHERE id = ?
    ''', (status, order_id))
    conn.commit()
    conn.close()

def get_orders_by_status(status):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE status = ?", (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_order_by_id(order_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_order_by_name(order_name):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_name = ?", (order_name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_payos_order_code(order_id, payos_order_code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders SET payos_order_code = ? WHERE id = ?
    ''', (payos_order_code, order_id))
    conn.commit()
    conn.close()

def delete_order_by_id(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def delete_order_by_name(order_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE order_name = ?", (order_name,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def delete_orders_by_status(status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE status = ?", (status,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def get_orders_by_customer(customer_tg_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE customer_tg_id = ? ORDER BY created_at DESC", (customer_tg_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
