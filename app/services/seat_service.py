import math
from database.db_manager import DBManager

class SeatService:
    def __init__(self, db_manager):
        self.db = db_manager

    def generate_seats(self, aircraft_id, business_seats, economy_seats):
        """
        Dynamically generates seat records for an aircraft based on capacity.
        """
        seats_data = []
        
        # Configuration Assumptions
        # Business: 4 seats per row (AC DF) - Spacious
        # Economy: 6 seats per row (ABC DEF) - Standard
        
        biz_seats_per_row = 4
        eco_seats_per_row = 6
        
        biz_cols = ['A', 'C', 'D', 'F']
        eco_cols = ['A', 'B', 'C', 'D', 'E', 'F']
        
        current_row = 1
        
        # 1. Generate Business Class Rows
        if business_seats > 0:
            num_biz_rows = math.ceil(business_seats / biz_seats_per_row)
            for _ in range(num_biz_rows):
                # Ensure we don't exceed exact count if strictly required, 
                # but usually aircraft correspond to full rows. 
                # We'll generate full rows for simplicity as partial rows are rare in config.
                for col in biz_cols:
                    seats_data.append((aircraft_id, current_row, col, 'Business'))
                current_row += 1
                
        # 2. Generate Economy Class Rows
        if economy_seats > 0:
            # Start economy a few rows after business? Or immediately?
            # Standard: Immediately next row.
            num_eco_rows = math.ceil(economy_seats / eco_seats_per_row)
            for _ in range(num_eco_rows):
                for col in eco_cols:
                    seats_data.append((aircraft_id, current_row, col, 'Economy'))
                current_row += 1
                
        # 3. Batch Insert
        try:
            conn = self.db.get_connection() # Use raw connection for speed
            cursor = conn.cursor()
            
            sql = "INSERT INTO seats (aircraft_id, `row_number`, column_number, class) VALUES (%s, %s, %s, %s)"
            cursor.executemany(sql, seats_data)
            conn.commit()
            print(f"Generated {len(seats_data)} seats for Aircraft {aircraft_id}")
            return True
            
        except Exception as e:
            print(f"Error generating seats: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if cursor: cursor.close()
            # Don't close conn if pooled? DBManager.get_connection might return pooled.
            # Assuming DBManager implementation handles pool, we just close cursor. 
            # If get_connection() returns a raw connection that shouldn't be closed manually if using a pool framework unless we know it's safe.
            # Safe logic: if DBManager.get_connection returns the pool's connection object, we shouldn't close it, just commit.
            pass 
