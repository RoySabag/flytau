import random
from datetime import datetime

class OrderDAO:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_order(self, flight_id, customer_email, guest_email, total_price, seat_ids):
        """
        Creates an order and associated order lines in a single transaction.
        """
        # 1. Generate Unique Order Code (Numeric, 6 digits) because DB column is Integer
        order_code = random.randint(100000, 999999)
        
        conn = self.db.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor()
        try:
            # Start Transaction
            # (In MySQL Connector/Python, starting a transaction is implicit with cursor, but we need to control commit)
            
            # 2. Insert Order
            # Table: Orders
            
            query_order = """
                INSERT INTO orders 
                (unique_order_code, order_date, order_status, flight_id, total_price, customer_email, guest_email)
                VALUES (%s, NOW(), 'Paid', %s, %s, %s, %s)
            """
            # Handle empty strings as None/NULL for database
            c_email = customer_email if customer_email else None
            g_email = guest_email if guest_email else None
            
            cursor.execute(query_order, (order_code, flight_id, total_price, c_email, g_email))
            
            # Using lastrowid for the auto-increment PK (order_id)
            order_id = cursor.lastrowid
            
            # 3. Insert Order Lines
            # Table: Order_Lines
            query_line = "INSERT INTO order_lines (order_id, seat_id, flight_id) VALUES (%s, %s, %s)"
            
            lines_data = [(order_id, seat_id, flight_id) for seat_id in seat_ids]
            cursor.executemany(query_line, lines_data)
            
            conn.commit()
            return {"status": "success", "order_code": order_code, "order_id": order_id}

        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating order: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
            conn.close()

    def get_order_details(self, order_code):
        """
        Fetches order details for the confirmation page.
        """
        query = """
            SELECT o.*, f.departure_time, r.origin_airport, r.destination_airport
            FROM orders o
            JOIN flights f ON o.flight_id = f.flight_id
            JOIN routes r ON f.route_id = r.route_id
            WHERE o.unique_order_code = %s
        """
        return self.db.fetch_one(query, (order_code,))

    def get_customer_orders(self, email):
        """
        Fetches all orders for a specific customer email, including flight details.
        """
        query = """
            SELECT 
                o.unique_order_code as order_id, o.unique_order_code, o.order_date, o.order_status, o.total_price,
                f.departure_time, r.origin_airport, r.destination_airport,
                a.manufacturer
            FROM orders o
            JOIN flights f ON o.flight_id = f.flight_id
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            WHERE o.customer_email = %s
            ORDER BY o.order_date DESC
        """
        return self.db.fetch_all(query, (email,))

    def cancel_order(self, order_id):
        """
        Cancels an order.
        Logic:
         - If (flight_time - now) < 36 hours: Fine = 5% of Total Price.
         - Else: No Fine (Full Refund).
        Updates order status to 'Cancelled'.
        Returns dictionary with refund details.
        """
        # 1. Fetch Order and Flight Details
        query_info = """
            SELECT o.total_price, o.order_status, f.departure_time 
            FROM orders o
            JOIN flights f ON o.flight_id = f.flight_id
            WHERE o.unique_order_code = %s
        """
        order = self.db.fetch_one(query_info, (order_id,))
        
        if not order:
            return {"status": "error", "message": "Order not found"}
        
        if order['order_status'] == 'Cancelled':
            return {"status": "error", "message": "Order is already cancelled"}

        # 2. Calculate Time Difference
        flight_time = order['departure_time']
        if isinstance(flight_time, str):
            flight_time = datetime.strptime(flight_time, '%Y-%m-%d %H:%M:%S') # Adjust format if needed

        now = datetime.now()
        time_diff = flight_time - now
        hours_diff = time_diff.total_seconds() / 3600

        total_price = float(order['total_price'])
        fine = 0.0
        
        # 3. Apply Fine Logic
        if hours_diff < 36:
            fine = total_price * 0.05
        
        refund_amount = total_price - fine

        # 4. Update Database
        query_update = "UPDATE orders SET order_status = 'Cancelled' WHERE unique_order_code = %s"
        try:
            self.db.execute_query(query_update, (order_id,))
            return {
                "status": "success",
                "refund_amount": round(refund_amount, 2),
                "fine": round(fine, 2),
                "message": "Order cancelled successfully"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
