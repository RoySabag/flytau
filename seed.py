import mysql.connector
import os

def seed_database():
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "root",
        "database": "flytau",
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci"
    }

    try:
        print("Connecting to database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        file_path = os.path.join("sql", "seed_data.sql")
        print(f"Reading seed file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # Execute statements one by one
        print("Executing seed data...")
        
        # Split by semicolon but ignore empty statements
        statements = sql_script.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                    print(f"Executed: {statement[:50]}...") 
                except mysql.connector.Error as err:
                    print(f"⚠️ Warning executing statement: {err}")

        conn.commit()
        print("✅ Database seeded successfully!")

    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    seed_database()
