from app.classes.db_manager import DB

def debug_db():
    conn = DB.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("\n--- 1. Orders Content ---")
    cursor.execute("SELECT * FROM orders LIMIT 5")
    orders = cursor.fetchall()
    for o in orders:
        print(o)

    print("\n--- 2. Order_Lines Content ---")
    cursor.execute("SELECT * FROM order_lines LIMIT 5")
    lines = cursor.fetchall()
    for l in lines:
        print(l)

    print("\n--- 3. Schema Inspection ---")
    cursor.execute("DESCRIBE orders")
    print("Orders Columns:", [row['Field'] for row in cursor.fetchall()])
    
    cursor.execute("DESCRIBE order_lines")
    print("Order_Lines Columns:", [row['Field'] for row in cursor.fetchall()])
    
    conn.close()

if __name__ == "__main__":
    debug_db()
