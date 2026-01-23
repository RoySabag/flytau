"""
File: order_dao.py
Purpose: Data Access Object for Booking Lifecycle (Creation, Cancellation, Retrieval).
"""
import random
from datetime import datetime

class OrderDAO:
    """
    Manages order data, including transaction creation, cancellation logic, and ticket retrieval.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def _get_seat_class_map(self, flight_id):
        """Resolves row ranges to class names (Economy/Business) for a given flight."""
        query = """
            SELECT ac.row_start, ac.row_end, ac.class_name
            FROM flights f
            JOIN aircraft_classes ac ON f.aircraft_id = ac.aircraft_id
            WHERE f.flight_id = %s
            ORDER BY ac.row_start
        """
        return [(r['row_start'], r['row_end'], r['class_name']) for r in self.db.fetch_all(query, (flight_id,))]

    # =================================================================
    # Part A: Order Creation
    # =================================================================

    def create_order(self, flight_id, customer_email, guest_email, total_price, seat_ids):
        """Generates a new order and inserts ticket lines transactionally."""
        # 1. Generate Unique Order Code (Numeric, 6 digits)
        order_code = random.randint(100000, 999999)
        
        conn = self.db.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor()
        try:
            query_order = """
                INSERT INTO orders 
                (unique_order_code, order_date, order_status, flight_id, total_price, customer_email, guest_email)
                VALUES (%s, NOW(), 'active', %s, %s, %s, %s)
            """
            
            c_email = customer_email if customer_email else None
            g_email = guest_email if guest_email else None
            
            cursor.execute(query_order, (order_code, flight_id, total_price, c_email, g_email))
            
            # Resolve classes for lines
            class_map = self._get_seat_class_map(flight_id)
            
            query_line = """
                INSERT INTO order_lines 
                (unique_order_code, flight_id, `row_number`, `column_number`, `class`) 
                VALUES (%s, %s, %s, %s, %s)
            """
            
            lines_data = []
            for seat_str in seat_ids:
                try:
                    r_str, c_str = seat_str.split('-')
                    row = int(r_str)
                    col = c_str
                    
                    seat_class = 'Economy' 
                    for (r_start, r_end, c_name) in class_map:
                        if r_start <= row <= r_end:
                            seat_class = c_name
                            break
                    
                    lines_data.append((order_code, flight_id, row, col, seat_class))
                except ValueError:
                    print(f"Invalid seat format: {seat_str}")
                    continue

            cursor.executemany(query_line, lines_data)
            
            conn.commit()
            return {"status": "success", "order_code": order_code, "order_id": order_code}

        except Exception as e:
            conn.rollback()
            print(f"Error creating order: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
            conn.close()

    # =================================================================
    # Part B: Order Retrieval
    # =================================================================

    def get_order_details(self, order_code):
        """Fetches full order context including flight details and specific tickets."""
        # 1. Fetch Order & Flight Info
        query = """
            SELECT 
                o.*, 
                f.departure_time, r.origin_airport, r.destination_airport,
                a.manufacturer
            FROM orders o
            JOIN flights f ON o.flight_id = f.flight_id
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            WHERE o.unique_order_code = %s
        """
        order = self.db.fetch_one(query, (order_code,))
        
        if order:
            q_tickets = """
                SELECT `row_number`, `column_number`, `class`
                FROM order_lines
                WHERE unique_order_code = %s
                ORDER BY `row_number`, `column_number`
            """
            order['tickets'] = self.db.fetch_all(q_tickets, (order_code,))
            
        return order

    def get_customer_orders(self, email, status_filter=None):
        """Retrieves and filters the complete order history for a registered customer."""
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
        """
        params = [email]
        
        if status_filter:
            query += " AND o.order_status = %s"
            params.append(status_filter)
            
        query += " ORDER BY o.order_date DESC"
        
        orders = self.db.fetch_all(query, tuple(params))
        
        if not orders:
            return []
            
        for order in orders:
            q_tickets = """
                SELECT row_number, column_number, class
                FROM order_lines
                WHERE unique_order_code = %s
                ORDER BY row_number, column_number
            """
            tickets = self.db.fetch_all(q_tickets, (order['unique_order_code'],))
            order['tickets'] = tickets
            
        return orders

    # =================================================================
    # Part C: Cancellation Logic
    # =================================================================

    def cancel_order(self, order_id):
        """
        Processes a customer cancellation (36h rule, 5% penalty).
        """
        order_id_str = str(order_id)

        # 1. Get Flight Info to validate time
        query_check = """
            SELECT f.departure_time, o.total_price, o.order_status
            FROM orders o
            JOIN flights f ON o.flight_id = f.flight_id
            WHERE o.unique_order_code = %s
        """
        order = self.db.fetch_one(query_check, (order_id_str,))
        
        if not order:
            return {"status": "error", "message": "Order not found"}
            
        if order['order_status'] in ['customer_cancelled', 'system_cancelled']:
            return {"status": "error", "message": "Order is already cancelled"}
            
        departure_time = order['departure_time']
        if isinstance(departure_time, str):
            departure_time = datetime.strptime(departure_time, '%Y-%m-%d %H:%M:%S')
            
        # 2. Calculate Time Difference
        time_diff = departure_time - datetime.now()
        hours_diff = time_diff.total_seconds() / 3600
        
        total_price = float(order['total_price'])
        
        # 3. Validate Time Window
        if hours_diff < 36:
             return {
                 "status": "error", 
                 "message": f"Cancellation rejected. Flight departs in {round(hours_diff, 1)} hours (Minimum 36h notice required)."
             }

        # 4. Calculate Financials (5% Penalty)
        fine = total_price * 0.05
        refund_amount = total_price - fine

        # 5. Update Database
        query_update = "UPDATE orders SET order_status = 'customer_cancelled', total_price = %s WHERE unique_order_code = %s"
        try:
            rounded_fine = round(fine, 2)
            res = self.db.execute_query(query_update, (rounded_fine, order_id_str))
            
            if res is None:
                return {"status": "error", "message": "Database update failed (Query Error). Check server logs."}
            
            return {
                "status": "success",
                "refund_amount": round(refund_amount, 2),
                "fine": rounded_fine,
                "message": "Order cancelled successfully"
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
