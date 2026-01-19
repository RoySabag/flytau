import mysql.connector
import random

def populate_seats():
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "root",
        "database": "flytau"
    }

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Ensure Table Exists
        create_table = """
        CREATE TABLE IF NOT EXISTS seats (
            seat_id INT AUTO_INCREMENT PRIMARY KEY,
            aircraft_id INT NOT NULL,
            `row_number` INT NOT NULL,
            `column_number` VARCHAR(5) NOT NULL,
            `class` ENUM('Economy', 'Business') NOT NULL,
            FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE
        );
        """
        cursor.execute(create_table)

        # 2. Check if Empty
        cursor.execute("SELECT COUNT(*) FROM seats")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"Seats table already has {count} rows. Skipping.")
            return

        print("Populating seats...")
        
        # 3. Insert Seats
        # Aircrafts 1-6
        # Small: 1, 3, 6 (Rows 1-20, 3-3 config? A,B,C D,E,F. No business?)
        # Big: 2, 4, 5 (Rows 1-40, Business 1-5, Eco 6-40)

        seats_data = []
        
        # Fetch aircrafts to be sure (optional, but let's assume 1-6 from seed)
        aircraft_ids = [1, 2, 3, 4, 5, 6]
        
        for aid in aircraft_ids:
            # Simple logic: Odd = Small, Even = Big (Roughly matching manufacturers in seed)
            # Actually seed: 
            # 1: Small, 2: Big, 3: Small, 4: Big, 5: Big, 6: Small
            is_big = (aid in [2, 4, 5])
            
            if is_big:
                # Business: Rows 1-5, Cols A,C,D,F (2-2?) or A,B,E,F
                for r in range(1, 6):
                    for c in ['A', 'C', 'D', 'F']: 
                        seats_data.append((aid, r, c, 'Business'))
                # Economy: Rows 6-30
                for r in range(6, 31):
                    for c in ['A', 'B', 'C', 'D', 'E', 'F']:
                        seats_data.append((aid, r, c, 'Economy'))
            else:
                # Small: All Economy, Rows 1-25
                for r in range(1, 26):
                    for c in ['A', 'B', 'C', 'D', 'E', 'F']:
                        seats_data.append((aid, r, c, 'Economy'))
        
        query = "INSERT INTO seats (aircraft_id, `row_number`, `column_number`, `class`) VALUES (%s, %s, %s, %s)"
        
        # Batch insert
        cursor.executemany(query, seats_data)
        conn.commit()
        print(f"✅ inserted {len(seats_data)} seats.")

    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    populate_seats()
