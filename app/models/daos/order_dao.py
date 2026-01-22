import random
from datetime import datetime

class OrderDAO:
    """
    Data Access Object for Order Logic.

    This class manages the lifecycle of customer bookings, including:
    1.  **Creation**: Generating unique order codes and storing transaction details.
    2.  **Retrieval**: Fetching order history for profiles and administrative views.
    3.  **Cancellation Policy Enforcement**:
        - **Customer Cancellation**: Allowed > 36h before flight (5% Penalty).
        - **System Cancellation**: Occurs when a flight is cancelled by admin (> 72h).
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def _get_seat_class_map(self, flight_id):
        """
        Helper: Resolves row ranges to classes for a flight.
        Returns list of tuples: (row_start, row_end, class_name)
        """
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
        """
        Creates a new order and its associated ticket lines in a single transaction.
        
        **Process:**
        1.  Generates a random 6-digit `unique_order_code`.
        2.  Inserts the main order record.
        3.  Inserts individual `order_lines` for each selected seat.
        """
        # 1. Generate Unique Order Code (Numeric, 6 digits)
        order_code = random.randint(100000, 999999)
        
        conn = self.db.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor()
        try:
            # 2. Insert Order Header
            query_order = """
                INSERT INTO orders 
                (unique_order_code, order_date, order_status, flight_id, total_price, customer_email, guest_email)
                VALUES (%s, NOW(), 'active', %s, %s, %s, %s)
            """
            
            c_email = customer_email if customer_email else None
            g_email = guest_email if guest_email else None
            
            cursor.execute(query_order, (order_code, flight_id, total_price, c_email, g_email))
            
            # 3. Insert Order Lines (Tickets) with Resolved Class
            # First, fetch class mapping for this flight's aircraft
            # We assume flight_id is valid.
            class_map = self._get_seat_class_map(flight_id)
            
            query_line = """
                INSERT INTO order_lines 
                (unique_order_code, flight_id, `row_number`, `column_number`, `class`) 
                VALUES (%s, %s, %s, %s, %s)
            """
            
            lines_data = []
            for seat_str in seat_ids:
                # seat_str is "row-col" (e.g. "1-A")
                try:
                    r_str, c_str = seat_str.split('-')
                    row = int(r_str)
                    col = c_str
                    
                    # Resolve class
                    # heuristic: find which range the row falls into
                    seat_class = 'Economy' # fallback
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
        """
        Fetches full details for a single order, including flight and seat information.
        Used for the 'Confirmation' page and 'Manage Booking' guest login.
        """
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
            # 2. Fetch specific tickets/seats associated with this order
            # Refactored: Fetch directly from order_lines (No seats table)
            q_tickets = """
                SELECT `row_number`, `column_number`, `class`
                FROM order_lines
                WHERE unique_order_code = %s
                ORDER BY `row_number`, `column_number`
            """
            order['tickets'] = self.db.fetch_all(q_tickets, (order_code,))
            
        return order

    def get_customer_orders(self, email, status_filter=None):
        """
        Retrieves the complete order history for a registered customer.
        Supports filtering by status (Active, Cancelled, Completed).
        """
        # 1. Fetch Orders
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
            
        # 2. Populate Ticket Details for each Order
        # Note: N+1 queries used here for simplicity as user order history is typically small.
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
        Processes a Customer-initiated cancellation.
        
        **Policy Enforcement**:
        1.  **Time Limit**: Must be > 36 hours before departure.
        2.  **Penalty**: 5% of the total ticket price is retained as a fine.
        3.  **Refund**: The remaining 95% is refunded to the customer.
        
        **Database Action**:
        - Updates `order_status` to 'customer_cancelled'.
        - Updates `total_price` to the **fine amount** (representing retained revenue).
        """
        # Ensure order_id is string to avoid MySQL "Truncated incorrect DOUBLE value" 
        # when comparing against VARCHAR column containing non-numeric legacy data.
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
        # Use simple naive comparison (assuming DB is consistent with app server time)
        # Ideally both should be UTC.
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
        # The stored total_price is updated to the fine amount (Company Revenue).
        # Using exact ENUM value 'customer_cancelled'
        query_update = "UPDATE orders SET order_status = 'customer_cancelled', total_price = %s WHERE unique_order_code = %s"
        try:
            # Round fine to 2 decimal places ensuring compliance with DECIMAL(10,2)
            rounded_fine = round(fine, 2)
            res = self.db.execute_query(query_update, (rounded_fine, order_id_str))
            
            # execute_query returns None on error, rowcount (int) on success
            if res is None:
                return {"status": "error", "message": "Database update failed (Query Error). Check server logs."}
            
            # execute_query returns rowcount for updates if not SELECT/INSERT
            if res == 0:
                 # It might return 0 if values didn't change (unlikely) or ID not found (unlikely as we selected it)
                 # But let's verify.
                 pass
            
            return {
                "status": "success",
                "refund_amount": round(refund_amount, 2),
                "fine": rounded_fine,
                "message": "Order cancelled successfully"
            }
            return {
                "status": "success",
                "refund_amount": round(refund_amount, 2),
                "fine": round(fine, 2),
                "message": "Order cancelled successfully"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
