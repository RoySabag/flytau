from app.classes.db_manager import DB

def check_schema():
    conn = DB.get_connection()
    cursor = conn.cursor()
    
    print("--- Aircraft Schema ---")
    cursor.execute("DESCRIBE Aircraft")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Employees Schema ---")
    cursor.execute("DESCRIBE Employees")
    for row in cursor.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_schema()
