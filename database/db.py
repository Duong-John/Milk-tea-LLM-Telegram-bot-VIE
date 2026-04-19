import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tea_shop.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Menu Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price_m INTEGER NOT NULL,
            price_l INTEGER NOT NULL,
            available BOOLEAN NOT NULL DEFAULT 1,
            description TEXT
        )
    ''')

    # Create Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_name TEXT NOT NULL,
            customer_tg_id TEXT NOT NULL,
            recipient_name TEXT,
            delivery_time TEXT,
            order_details TEXT NOT NULL,
            total_amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            preparation_status TEXT DEFAULT 'PREPARING',
            payos_order_code INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
