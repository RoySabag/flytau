from app.classes.db_manager import DB

def check_customer_schema():
    conn = DB.get_connection()
    cursor = conn.cursor()
    
    print("--- All Tables ---")
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Customers Schema ---")
    try:
        cursor.execute("DESCRIBE customers")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error describing customers: {e}")

    print("\n--- Customer Phone Numbers Schema ---")
    try:
        cursor.execute("DESCRIBE customer_phone_numbers")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error describing customer_phone_numbers: {e}")
        
    conn.close()

if __name__ == "__main__":
    check_customer_schema()
