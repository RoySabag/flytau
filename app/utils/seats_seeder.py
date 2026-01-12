import sys
import os

# Adjust path to find 'app' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.classes.db_manager import DB

# --- תצורת מטוסים (Hardcoded Layouts) ---
# Each aircraft has a unique configuration for Rows and Columns.
# The 'Small'/'Big' classification (Economy vs Business+Economy) is determined by the DB 'size' column.
AIRCRAFT_CONFIG = {
    1: {'rows': 30, 'cols': 'ABCDEF', 'business_rows': 0},           # Boeing 737-800
    2: {'rows': 40, 'cols': 'ABCDEFGH', 'business_rows': 6},         # Boeing 787
    3: {'rows': 25, 'cols': 'ABCDEF', 'business_rows': 0},           # Airbus A320
    4: {'rows': 45, 'cols': 'ABCDEFGHK', 'business_rows': 8},        # Airbus A350
    5: {'rows': 55, 'cols': 'ABCDEFGHK', 'business_rows': 10},       # Boeing 747-8
    6: {'rows': 20, 'cols': 'ACDF', 'business_rows': 0},             # Embraer E195
}

def create_seats_for_aircraft(aircraft_data):
    """
    Creates seats for a specific aircraft using DBManager for efficiency.
    Uniqueness defined by AIRCRAFT_CONFIG + DB 'size' property.
    """
    aircraft_id = aircraft_data['aircraft_id']
    size_value = aircraft_data.get('size') 
    
    # 1. Determine Logic Class Policy (Economy Only vs Mixed) based on 'size' from DB
    # User requirement: "Size == 'Big'/'Small' at the DB"
    # Logic: 
    #   - 'Big' (string) or >= 200 (int) -> Big (Business + Economy)
    #   - 'Small' (string) or < 200 (int) -> Small (Economy Only)
    
    is_big = False
    
    if isinstance(size_value, str):
        if size_value.lower() == 'big':
            is_big = True
            
    policy_name = "Business + Economy" if is_big else "Economy Only"
    print(f"🔹 Processing Aircraft {aircraft_id}: DB Size='{size_value}' ({type(size_value).__name__}) -> Policy='{policy_name}'")

    # 2. Get Layout Configuration
    if aircraft_id not in AIRCRAFT_CONFIG:
        print(f"⚠️ No layout config found for aircraft ID {aircraft_id}. Skipping.")
        return

    config = AIRCRAFT_CONFIG[aircraft_id]
    total_rows = config['rows']
    columns = list(config['cols'])
    business_rows_limit = config.get('business_rows', 0)

    # 3. Generate Seat Data
    seats_data = []
    
    for row in range(1, total_rows + 1):
        # Determine Class
        seat_class = 'Economy'
        
        if is_big:
            # Only Big aircrafts get Business class
            if row <= business_rows_limit:
                seat_class = 'Business'
        
        for col in columns:
            seats_data.append((aircraft_id, row, col, seat_class))

    # 4. Batch Insert using DBManager's connection
    # We use direct connection for executemany speed
    conn = DB.get_connection()
    if not conn:
        print("❌ Failed to get DB connection.")
        return

    try:
        cursor = conn.cursor()
        sql = "INSERT INTO seats (aircraft_id, `row_number`, column_number, class) VALUES (%s, %s, %s, %s)"
        cursor.executemany(sql, seats_data)
        conn.commit()
        print(f"✅ Created {len(seats_data)} seats for Aircraft {aircraft_id}.")
    except Exception as e:
        print(f"❌ Error inserting seats for Aircraft {aircraft_id}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    print("🚀 Starting Seats Seeder (Refactored)...")
    
    # Fetch all aircrafts
    # Note: We rely on the internal DBManager pool
    all_aircrafts = DB.fetch_all("SELECT * FROM aircraft")
    
    if not all_aircrafts:
        print("❌ No aircrafts found in DB.")
        return

    print(f"ℹ️ Found {len(all_aircrafts)} aircrafts.")
    
    for aircraft in all_aircrafts:
        create_seats_for_aircraft(aircraft)
        
    print("\n✨ Done!")

if __name__ == "__main__":
    main()