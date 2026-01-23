import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database.db_manager import DB
from app.services.seat_service import SeatService

def get_config_by_size(size):
    """
    Returns the seat configuration based on the aircraft size.
    """
    size = str(size).lower()
    
    if size == 'big':
        return {'rows': 45, 'cols': 'ABCDEFGH', 'business_rows': 5}
    else:
        return {'rows': 30, 'cols': 'ABCDEF', 'business_rows': 0}

def seed_configs():
    print("🚀 Seeding Aircraft Configurations (via SeatService)...")
    
    # Initialize Service
    seat_service = SeatService(DB)
    
    try:
        # 1. Clear existing
        seat_service.clear_configurations()
        
        # 2. Fetch Aircraft
        aircrafts = DB.fetch_all("SELECT * FROM aircraft")
        
        count = 0
        for aircraft in aircrafts:
            aircraft_id = aircraft['aircraft_id']
            size = aircraft.get('size')
            
            # 3. Determine Config
            config = get_config_by_size(size)
            
            total_rows = config['rows']
            cols = config['cols']
            biz_rows = config['business_rows']
            
            # 4. Define Business Class
            if biz_rows > 0:
                seat_service.define_aircraft_class(
                    aircraft_id, 'Business', 1, biz_rows, cols
                )
                
            # 5. Define Economy Class
            eco_start = biz_rows + 1
            if eco_start <= total_rows:
                seat_service.define_aircraft_class(
                    aircraft_id, 'Economy', eco_start, total_rows, cols
                )
            
            count += 1
            
        print(f"✅ Successfully configured {count} aircrafts.")
        
    except Exception as e:
        print(f"❌ Error seeding configs: {e}")

if __name__ == "__main__":
    seed_configs()
