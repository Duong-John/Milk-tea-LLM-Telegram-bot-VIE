import sqlite3
from .db import get_connection

def add_menu_item(name, price_m, price_l, description=''):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO menu (name, price_m, price_l, description)
        VALUES (?, ?, ?, ?)
    ''', (name, price_m, price_l, description))
    conn.commit()
    conn.close()

def get_all_items(only_available=True):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if only_available:
        cursor.execute("SELECT * FROM menu WHERE available = 1")
    else:
        cursor.execute("SELECT * FROM menu")
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_item_by_id(item_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_availability(item_id, available: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE menu SET available = ? WHERE id = ?
    ''', (1 if available else 0, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM menu WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
