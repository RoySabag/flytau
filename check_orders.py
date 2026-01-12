from app.classes.db_manager import DB

def check_orders_schema():
    conn = DB.get_connection()
    cursor = conn.cursor()
    
    print("\n--- Orders Schema ---")
    try:
        cursor.execute("DESCRIBE Orders")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error describing Orders: {e}")

    print("\n--- Order_Lines Schema ---")
    try:
        cursor.execute("DESCRIBE Order_Lines")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error describing Order_Lines: {e}")
        
    conn.close()

if __name__ == "__main__":
    check_orders_schema()
