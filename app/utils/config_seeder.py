import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database.db_manager import DB

# Logic ported from old seats_seeder.py
AIRCRAFT_CONFIG = {
    1: {'rows': 30, 'cols': 'ABCDEF', 'business_rows': 0},           
    2: {'rows': 40, 'cols': 'ABCDEFGH', 'business_rows': 6},         
    3: {'rows': 25, 'cols': 'ABCDEF', 'business_rows': 0},           
    4: {'rows': 45, 'cols': 'ABCDEFGHK', 'business_rows': 8},        
    5: {'rows': 55, 'cols': 'ABCDEFGHK', 'business_rows': 10},       
    6: {'rows': 20, 'cols': 'ACDF', 'business_rows': 0},             
}

def seed_configs():
    print("🚀 Seeding Aircraft Configurations...")
    
    conn = DB.get_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        # Clear existing configs
        cursor.execute("TRUNCATE TABLE aircraft_classes")
        
        aircrafts = DB.fetch_all("SELECT * FROM aircraft")
        
        count = 0
        for a in aircrafts:
            aid = a['aircraft_id']
            size_val = str(a.get('size', '')).lower()
            is_big = size_val == 'big'
            
            # Determine logic
            config = None
            if aid in AIRCRAFT_CONFIG:
                config = AIRCRAFT_CONFIG[aid]
            else:
                if is_big:
                    config = {'rows': 45, 'cols': 'ABCDEFGH', 'business_rows': 5}
                else:
                    config = {'rows': 30, 'cols': 'ABCDEF', 'business_rows': 0}
            
            total_rows = config['rows']
            cols = config['cols']
            biz_rows = config['business_rows']
            
            # Insert Business Class (if exists)
            if biz_rows > 0:
                sql_biz = """
                    INSERT INTO aircraft_classes (aircraft_id, class_name, row_start, row_end, columns)
                    VALUES (%s, 'Business', 1, %s, %s)
                """
                cursor.execute(sql_biz, (aid, biz_rows, cols))
                
            # Insert Economy Class
            # Starts after business, or at 1
            eco_start = biz_rows + 1
            if eco_start <= total_rows:
                sql_eco = """
                    INSERT INTO aircraft_classes (aircraft_id, class_name, row_start, row_end, columns)
                    VALUES (%s, 'Economy', %s, %s, %s)
                """
                cursor.execute(sql_eco, (aid, eco_start, total_rows, cols))
            
            count += 1
            
        conn.commit()
        print(f"✅ Configured {count} aircrafts successfully.")
        
    except Exception as e:
        print(f"❌ Error seeding configs: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_configs()
