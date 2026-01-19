from datetime import datetime, timedelta

class FlightDAO:
    """
    Data Access Object for Flight Operations.

    This class serves as the central hub for managing flight data, including:
    1.  **Flight Creation**: Assigning routes, times, and initial pricing.
    2.  **Status Management**: Automatically updating statuses based on real-time checks (Scheduled -> On Air -> Landed).
    3.  **Booking Logic**: Handling seat availability and "Fully Booked" states.
    4.  **Admin Operations**: Initializing cancellations and refunds.
    5.  **Search**: Complex filtering for user flight discovery.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    # =================================================================
    # Part A: Flight Creation & Initialization
    # =================================================================

    def get_all_locations(self):
        """
        Retrieves a list of all unique cities/airports available in the system.
        Used to populate dropdown menus in the Search and Create Flight forms.
        """
        query = """
            SELECT DISTINCT origin_airport as location FROM routes
            UNION
            SELECT DISTINCT destination_airport as location FROM routes
        """
        results = self.db.fetch_all(query)
        return [row['location'] for row in results]

    def get_route_details_by_airports(self, origin, destination):
        """
        Fetches route specifications (ID, Duration) for a given origin-destination pair.
        Used for calculating arrival times and validating flight creation.
        """
        query = """
            SELECT route_id, flight_duration, route_type 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """
        result = self.db.fetch_one(query, (origin, destination))
        
        if result:
            # Convert string duration to timedelta object for calculations
            duration = result['flight_duration']
            if isinstance(duration, str):
                t = datetime.strptime(duration, "%H:%M:%S")
                result['flight_duration'] = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        
        return result

    def create_flight(self, origin, destination, departure_time, economy_price, business_price):
        """
        Creates a new flight record in the database.
        
        Logic:
        1.  Resolves the `route_id` automatically based on origin/destination.
        2.  Sets the initial status to 'Scheduled'.
        3.  Note: Aircraft assignment happens in a separate step by the admin.
        """
        # 1. Resolve Route ID
        route_info = self.get_route_details_by_airports(origin, destination)
        if not route_info:
            return {"status": "error", "message": f"No route found from {origin} to {destination}"}
        
        route_id = route_info['route_id']

        # 2. Insert into DB
        try:
            if isinstance(departure_time, str):
                departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M') 

            query = """
                INSERT INTO flights 
                (route_id, aircraft_id, departure_time, economy_price, business_price, flight_status)
                VALUES (%s, NULL, %s, %s, %s, 'Scheduled')
            """
            
            params = (route_id, departure_time, economy_price, business_price)
            res = self.db.execute_query(query, params)
            
            if isinstance(res, dict) and 'lastrowid' in res:
                return {"status": "success", "message": "Flight created successfully", "flight_id": res['lastrowid']}
            
            return {"status": "success", "message": "Flight created successfully (ID unknown)"}
        
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =================================================================
    # Part B: Flight Retrieval & Status Updates
    # =================================================================

    def get_all_active_flights(self, flight_id=None, status_filter=None):
        """
        Retrieves flights, typically for the Admin Dashboard or Main Schedule.
        
        **Dynamic Status Logic**:
        This method automatically updates flight statuses based on the current time:
        - Now < Departure: 'Scheduled'
        - Departure <= Now <= Arrival: 'On Air'
        - Now > Arrival: 'Landed'
        - Checks for 'Fully Booked' capacity only for Scheduled flights.
        """
        # 1. Fetch Flights with Joins for Readability
        query = """
            SELECT 
                f.flight_id,
                f.departure_time,
                f.flight_status,
                f.economy_price,
                f.business_price,
                
                -- Route Details
                r.origin_airport,
                r.destination_airport,
                r.flight_duration,
                
                -- Aircraft Details
                f.aircraft_id,
                a.manufacturer AS aircraft_model,
                a.size AS aircraft_size,
                
                -- Calculated Arrival (SQL side baseline)
                ADDTIME(f.departure_time, r.flight_duration) as arrival_time

            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
        """
        
        params = []
        if flight_id:
            query += " WHERE f.flight_id = %s"
            params.append(flight_id)
            
        query += " ORDER BY f.departure_time ASC"
        
        flights = self.db.fetch_all(query, tuple(params))
        if not flights:
            return []

        now = datetime.now()
        filtered_flights = []

        for flight in flights:
            current_status = flight['flight_status']
            
            # Skip logic for Cancelled flights - they are finalized.
            if current_status not in ['Cancelled', 'System Cancelled']:
                
                # --- Time-Based Status Update ---
                dep = flight['departure_time']
                if isinstance(dep, str):
                     dep = datetime.strptime(dep, '%Y-%m-%d %H:%M:%S')
    
                duration = flight['flight_duration']
                if isinstance(duration, str):
                     t = datetime.strptime(duration, "%H:%M:%S")
                     duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    
                arrival = dep + duration
                
                new_status = 'Scheduled'
                if now > arrival:
                    new_status = 'Landed'
                elif now >= dep:
                    new_status = 'On air'
                
                if new_status != current_status and current_status != 'Fully Booked': 
                    # Note: We let the Fully Booked check below handle overrides if needed, 
                    # but generally time status takes precedence over capacity if flight has started.
                    if current_status == 'Fully Booked' and new_status == 'Scheduled':
                         pass # Keep Fully Booked if it hasn't taken off yet
                    else:
                        try:
                            self.update_flight_status(flight['flight_id'], new_status)
                            flight['flight_status'] = new_status
                        except Exception as e:
                            print(f"Error updating status: {e}")
                
                # --- Capacity Check (Fully Booked) ---
                # Only runs if flight is pre-departure.
                if flight['flight_status'] in ['Scheduled', 'Fully Booked']:
                    is_full = self._is_flight_full(flight['flight_id'])
                    
                    final_status = 'Fully Booked' if is_full else 'Scheduled'
                    
                    if final_status != flight['flight_status']:
                        self.update_flight_status(flight['flight_id'], final_status)
                        flight['flight_status'] = final_status

                flight['arrival_time'] = arrival

            # --- Apply Filter ---
            if status_filter and status_filter != 'All':
                if flight['flight_status'] != status_filter:
                    continue 
            
            filtered_flights.append(flight)

        return filtered_flights

    def _is_flight_full(self, flight_id):
        """
        Internal Helper: Checks if specific flight is at 100% capacity.
        Compares Total Seats (from Aircraft) vs. Sold Tickets (from Active Orders).
        """
        # 1. Get Total Capacity
        query_capacity = """
            SELECT COUNT(*) as total 
            FROM seats s
            JOIN flights f ON s.aircraft_id = f.aircraft_id
            WHERE f.flight_id = %s
        """
        res_cap = self.db.fetch_one(query_capacity, (flight_id,))
        total = res_cap['total'] if res_cap else 0
        
        if total == 0: return False 

        # 2. Get Occupied Count
        query_occupied = """
            SELECT COUNT(*) as occupied
            FROM order_lines ol
            JOIN orders o ON ol.unique_order_code = o.unique_order_code
            WHERE ol.flight_id = %s AND o.order_status IN ('active', 'completed')
        """
        res_occ = self.db.fetch_one(query_occupied, (flight_id,))
        occupied = res_occ['occupied'] if res_occ else 0
        
        return occupied >= total

    def get_flight_by_id(self, flight_id):
        """
        Retrieves a single flight's comprehensive details.
        """
        query = """
            SELECT f.*, 
                   r.origin_airport, r.destination_airport, r.flight_duration, r.route_type,
                   a.size as aircraft_size
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    # =================================================================
    # Part C: Admin Actions (Updates & Cancellations)
    # =================================================================

    def update_flight_status(self, flight_id, new_status):
        """Directly updates the status column in the database."""
        try:
            query = "UPDATE flights SET flight_status = %s WHERE flight_id = %s"
            self.db.execute_query(query, (new_status, flight_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cancel_flight_transaction(self, flight_id):
        """
        Executes a Company Cancellation logic (Admin cancels flight).
        
        **Rules:**
        1.  Must be > 72 hours before departure.
        2.  Updates flight status to 'Cancelled'.
        3.  Refunding:
            - Finds all active orders.
            - Updates them to 'system_cancelled'.
            - Sets their price to 0 (Full Refund).
        """
        conn = self.db.get_connection()
        if not conn:
            return {"status": "error", "message": "DB connection failed"}
            
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Lock and Fetch Flight Step
            cursor.execute("SELECT departure_time, flight_status FROM flights WHERE flight_id = %s FOR UPDATE", (flight_id,))
            flight = cursor.fetchone()
            
            if not flight:
                conn.rollback()
                return {"status": "error", "message": "Flight not found"}
                
            if flight['flight_status'] == 'Cancelled':
                conn.rollback()
                return {"status": "error", "message": "Flight is already cancelled"}

            # 2. Validate Time Window (72 Hours)
            dep_time = flight['departure_time']
            if isinstance(dep_time, str):
                dep_time = datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')

            time_diff = dep_time - datetime.now()
            hours_diff = time_diff.total_seconds() / 3600
            
            if hours_diff < 72:
                conn.rollback()
                return {"status": "error", "message": "Cannot cancel flight less than 72 hours before departure."}

            # 3. Cancel Flight
            cursor.execute("UPDATE flights SET flight_status = 'Cancelled' WHERE flight_id = %s", (flight_id,))
            
            # 4. Process Refunds
            cursor.execute("SELECT unique_order_code FROM orders WHERE flight_id = %s AND order_status != 'Cancelled'", (flight_id,))
            active_orders = cursor.fetchall()
            
            if active_orders:
                # Update status to system_cancelled and Price to 0 to indicate full refund
                cursor.execute("""
                    UPDATE orders 
                    SET order_status = 'system_cancelled', total_price = 0 
                    WHERE flight_id = %s AND order_status = 'active'
                """, (flight_id,))
            
            conn.commit()
            return {"status": "success", "message": f"Flight cancelled. {len(active_orders)} orders refunded."}

        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
            conn.close()
            
    def update_prices(self, flight_id, eco_price, bus_price):
        """Updates ticket prices for an existing flight."""
        try:
            query = "UPDATE flights SET economy_price = %s, business_price = %s WHERE flight_id = %s"
            self.db.execute_query(query, (eco_price, bus_price, flight_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =================================================================
    # Part D: Seat Management & Booking
    # =================================================================

    def get_flight_seats(self, flight_id):
        """
        Generates a "Seat Map" for the UI.
        Combinations static aircraft seat configuration with dynamic booking data.
        
        Returns a list of seats with:
        - Position (Row/Col)
        - Class (Economy/Business)
        - Price (Resolved from flight settings)
        - `is_occupied` flag.
        """
        # 1. Fetch Flight Context
        flight = self.get_flight_by_id(flight_id)
        if not flight:
            return None
            
        aircraft_id = flight['aircraft_id']
        economy_price = flight['economy_price']
        business_price = flight['business_price']

        if not aircraft_id:
            # Setup incomplete
            return []

        # 2. Fetch All Seats in Aircraft Configuration
        query_seats = "SELECT * FROM seats WHERE aircraft_id = %s ORDER BY `row_number`, column_number"
        all_seats = self.db.fetch_all(query_seats, (aircraft_id,))

        # 3. Identify Occupied Seats
        # Excludes cancelled orders from occupancy check.
        query_occupied = """
            SELECT ol.seat_id 
            FROM order_lines ol
            JOIN orders o ON ol.unique_order_code = o.unique_order_code
            WHERE ol.flight_id = %s AND o.order_status != 'Cancelled'
        """
        occupied_results = self.db.fetch_all(query_occupied, (flight_id,))
        occupied_ids = {row['seat_id'] for row in occupied_results}

        # 4. Merge and Format
        final_seats = []
        for seat in all_seats:
            seat_id = seat['seat_id']
            is_occupied = seat_id in occupied_ids
            
            seat['is_occupied'] = is_occupied
            seat['price'] = business_price if seat['class'] == 'Business' else economy_price
            
            final_seats.append(seat)

        return final_seats

    # =================================================================
    # Part E: User Search
    # =================================================================

    def search_flights(self, origin, destination, date):
        """
        Executes a flight search based on user criteria.
        Returns detailed flight info including aircraft and pricing.
        """
        try:
            query = """
                SELECT 
                    f.flight_id,
                    f.departure_time,
                    f.economy_price,
                    f.business_price,
                    f.flight_status,
                    r.origin_airport,
                    r.destination_airport,
                    r.flight_duration,
                    a.manufacturer,
                    a.size
                FROM flights f
                JOIN routes r ON f.route_id = r.route_id
                LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
                WHERE r.origin_airport = %s
                  AND r.destination_airport = %s
                  AND DATE(f.departure_time) = %s
                  AND f.flight_status = 'Scheduled'
                ORDER BY f.departure_time ASC
            """
            
            return self.db.fetch_all(query, (origin, destination, date))

        except Exception as e:
            print(f"Error searching flights: {e}")
            return []