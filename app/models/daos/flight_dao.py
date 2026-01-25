"""
File: flight_dao.py
Purpose: Data Access Object for Flight Operations (Creation, Retrieval, Status Updates).
"""
from datetime import datetime, timedelta

class FlightDAO:
    """
    Central hub for managing flight data, status updates, and capacity checks.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def get_all_locations(self):
        """Retrieves a list of all unique cities/airports available in the system."""
        query = """
            SELECT DISTINCT origin_airport as location FROM routes
            UNION
            SELECT DISTINCT destination_airport as location FROM routes
        """
        results = self.db.fetch_all(query)
        return [row['location'] for row in results]

    def get_route_details_by_airports(self, origin, destination):
        """Fetches route ID and duration for a given origin-destination pair."""
        query = """
            SELECT route_id, flight_duration, route_type 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """
        result = self.db.fetch_one(query, (origin, destination))
        
        if result:
            duration = result['flight_duration']
            if isinstance(duration, str):
                t = datetime.strptime(duration, "%H:%M:%S")
                result['flight_duration'] = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        
        return result

    def create_flight(self, origin, destination, departure_time, economy_price, business_price):
        """Creates a new flight record in the database with status 'Scheduled'."""
        route_info = self.get_route_details_by_airports(origin, destination)
        if not route_info:
            return {"status": "error", "message": f"No route found from {origin} to {destination}"}
        
        route_id = route_info['route_id']

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

    def get_all_active_flights(self, flight_id=None, status_filter=None):
        """Retrieves flights and dynamically updates their status based on current time."""
        # 1. Fetch Flights with Joins for Readability
        query = """
            SELECT 
                f.flight_id,
                f.departure_time,
                f.flight_status,
                f.economy_price,
                f.business_price,
                r.origin_airport,
                r.destination_airport,
                r.flight_duration,
                f.aircraft_id,
                a.manufacturer AS aircraft_model,
                a.size AS aircraft_size,
                ADDTIME(f.departure_time, r.flight_duration) as arrival_time

            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
        """
        
        params = []
        if flight_id:
            query += " WHERE f.flight_id = %s"
            params.append(flight_id)
            
        query += " ORDER BY f.departure_time DESC"
        
        flights = self.db.fetch_all(query, tuple(params))
        if not flights:
            return []

        now = datetime.now()
        filtered_flights = []

        for flight in flights:
            current_status = flight['flight_status']
            
            # Skip logic for Cancelled flights
            if current_status not in ['Cancelled', 'System Cancelled']:
                try:
                    # --- Time-Based Status Update ---
                    dep = flight['departure_time']
                    if isinstance(dep, str):
                        try:
                            dep = datetime.strptime(dep, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                             print(f"Warning: Invalid date format for flight {flight['flight_id']}")
                             filtered_flights.append(flight)
                             continue
    
                    duration = flight['flight_duration']
                    if isinstance(duration, str):
                         try:
                             t = datetime.strptime(duration, "%H:%M:%S")
                             duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                         except ValueError:
                             duration = timedelta(hours=0)
    
                    arrival = dep + duration
                    
                    new_status = 'Scheduled'
                    if now > arrival:
                        new_status = 'Landed'
                    elif now >= dep:
                        new_status = 'On air'
                    
                    if new_status != current_status and current_status != 'Fully Booked': 
                        if current_status == 'Fully Booked' and new_status == 'Scheduled':
                             pass 
                        else:
                            self.update_flight_status(flight['flight_id'], new_status)
                            flight['flight_status'] = new_status
                    
                    # --- Capacity Check ---
                    if flight['flight_status'] in ['Scheduled', 'Fully Booked']:
                        is_full = self._is_flight_full(flight['flight_id'])
                        
                        final_status = 'Fully Booked' if is_full else 'Scheduled'
                        
                        if final_status != flight['flight_status']:
                            self.update_flight_status(flight['flight_id'], final_status)
                            flight['flight_status'] = final_status

                    flight['arrival_time'] = arrival
                    
                except Exception as e:
                    print(f"Error processing status for flight {flight.get('flight_id')}: {e}")

            # --- Apply Filter ---
            if status_filter and status_filter != 'All':
                if flight['flight_status'] != status_filter:
                    continue 
            
            filtered_flights.append(flight)

        return filtered_flights

    def _is_flight_full(self, flight_id):
        """Internal Helper: Returns True if occupied seats >= total capacity."""
        # 1. Get Total Capacity (Dynamic Calculation)
        query_capacity = """
            SELECT SUM((row_end - row_start + 1) * CHAR_LENGTH(columns)) as total
            FROM aircraft_classes ac
            JOIN flights f ON ac.aircraft_id = f.aircraft_id
            WHERE f.flight_id = %s
        """
        res_cap = self.db.fetch_one(query_capacity, (flight_id,))
        total = res_cap['total'] if res_cap and res_cap['total'] else 0
        
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
        """Retrieves a single flight's comprehensive details."""
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

    def update_flight_status(self, flight_id, new_status):
        """Directly updates the status column in the database."""
        try:
            query = "UPDATE flights SET flight_status = %s WHERE flight_id = %s"
            self.db.execute_query(query, (new_status, flight_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cancel_flight_transaction(self, flight_id):
        """Cancels a flight, refunds all active orders, and updates statuses (Transactional)."""
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

            # 2. Validate Time Window
            dep_time = flight['departure_time']
            if isinstance(dep_time, str):
                dep_time = datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')

            time_diff = dep_time - datetime.now()
            hours_diff = time_diff.total_seconds() / 3600
            
            # Warn if cancelling very close to departure
            status_code = "success"
            msg_prefix = ""
            if hours_diff < 24:
                status_code = "warning"
                msg_prefix = f"Warning: Flight cancelled less than {round(hours_diff, 1)}h before departure. "

            # 3. Cancel Flight
            cursor.execute("UPDATE flights SET flight_status = 'Cancelled' WHERE flight_id = %s", (flight_id,))
            
            # 4. Process Refunds
            cursor.execute("SELECT unique_order_code FROM orders WHERE flight_id = %s AND order_status != 'Cancelled'", (flight_id,))
            active_orders = cursor.fetchall()
            
            if active_orders:
                cursor.execute("""
                    UPDATE orders 
                    SET order_status = 'system_cancelled', total_price = 0 
                    WHERE flight_id = %s AND order_status = 'active'
                """, (flight_id,))
            
            conn.commit()
            return {"status": status_code, "message": f"{msg_prefix}Flight cancelled. {len(active_orders)} orders refunded."}

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

    def get_flight_seats(self, flight_id):
        """Generates a dynamic 'Seat Map' from Aircraft Configuration."""
        # 1. Fetch Flight Context
        flight = self.get_flight_by_id(flight_id)
        if not flight: return None
            
        aircraft_id = flight['aircraft_id']
        economy_price = flight['economy_price']
        business_price = flight['business_price']

        if not aircraft_id: return []

        # 2. Fetch Configuration
        query_config = "SELECT * FROM aircraft_classes WHERE aircraft_id = %s ORDER BY row_start"
        configs = self.db.fetch_all(query_config, (aircraft_id,))
        
        if not configs:
            return []

        # 3. Fetch Occupied Seats
        query_occupied = """
            SELECT ol.row_number, ol.column_number
            FROM order_lines ol
            JOIN orders o ON ol.unique_order_code = o.unique_order_code
            WHERE ol.flight_id = %s AND o.order_status != 'Cancelled'
        """
        occupied_results = self.db.fetch_all(query_occupied, (flight_id,))
        occupied_set = {f"{row['row_number']}-{row['column_number']}" for row in occupied_results}

        # 4. Generate Seat Map
        final_seats = []
        
        for cfg in configs:
            cls_name = cfg['class_name']
            columns = list(cfg['columns'])
            price = business_price if cls_name == 'Business' else economy_price
            
            for r in range(cfg['row_start'], cfg['row_end'] + 1):
                for c in columns:
                    unique_id = f"{r}-{c}"
                    is_occupied = unique_id in occupied_set
                    
                    seat_obj = {
                        'seat_id': unique_id, 
                        'row_number': r,
                        'column_number': c,
                        'class': cls_name,
                        'price': price,
                        'is_occupied': is_occupied
                    }
                    final_seats.append(seat_obj)

        return final_seats

    def search_flights(self, origin, destination, date):
        """Executes a flight search based on origin, destination, and date."""
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
                ORDER BY f.departure_time DESC
            """
            
            return self.db.fetch_all(query, (origin, destination, date))

        except Exception as e:
            print(f"Error searching flights: {e}")
            return []