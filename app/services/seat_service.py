import math
from database.db_manager import DBManager

class SeatService:
    def __init__(self, db_manager):
        self.db = db_manager

    def generate_seats(self, aircraft_id, business_seats, economy_seats):
        """
        Generates configuration records for `aircraft_classes`.
        """
        # Configuration Assumptions
        # Business: 4 seats per row (AC DF) -> 'ACDF'
        # Economy: 6 seats per row (ABC DEF) -> 'ABCDEF'
        
        biz_seats_per_row = 4
        eco_seats_per_row = 6
        
        biz_cols_str = 'ACDF'
        eco_cols_str = 'ABCDEF'
        
        current_row = 1
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 1. Business Class
            if business_seats > 0:
                num_biz_rows = math.ceil(business_seats / biz_seats_per_row)
                row_end = current_row + num_biz_rows - 1
                
                sql_biz = """
                    INSERT INTO aircraft_classes (aircraft_id, class_name, row_start, row_end, columns)
                    VALUES (%s, 'Business', %s, %s, %s)
                """
                cursor.execute(sql_biz, (aircraft_id, current_row, row_end, biz_cols_str))
                current_row = row_end + 1
                
            # 2. Economy Class
            if economy_seats > 0:
                num_eco_rows = math.ceil(economy_seats / eco_seats_per_row)
                row_end = current_row + num_eco_rows - 1
                
                sql_eco = """
                    INSERT INTO aircraft_classes (aircraft_id, class_name, row_start, row_end, columns)
                    VALUES (%s, 'Economy', %s, %s, %s)
                """
                cursor.execute(sql_eco, (aircraft_id, current_row, row_end, eco_cols_str))
                
            conn.commit()
            print(f"configured Aircraft {aircraft_id} successfully")
            return True
            
        except Exception as e:
            print(f"Error configuring aircraft: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close() 
