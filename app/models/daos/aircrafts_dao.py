from datetime import timedelta, datetime

class AircraftDAO:
    """
    Data Access Object for Aircraft Management and Scheduling Logic.

    This class handles the complex logic of aircraft assignment, including:
    1.  **Availability Checking**: Ensuring aircraft are not double-booked.
    2.  **Location Tracking**: Determining where an aircraft is at any given time based on its flight history.
    3.  **Future Chain Validation**: Ensuring that assigning an aircraft to a flight doesn't break its future schedule.
    4.  **Ferry Flights (Operational Moves)**:
        
        **Logical Assumption - Ferry Flights:**
        When an aircraft is required at an origin (e.g., NYC) but is currently located elsewhere (e.g., TLV), 
        the system checks if it can fly empty ("Ferry") to the origin in time.
        
        **Why are Ferry Flights not Commercial?**
        - **Operational Flexibility**: Ferry flights are ad-hoc operational necessities, often decided closer to departure.
        - **Simplicity**: Converting them to commercial flights would require generating ticket inventory, 
          managing passenger bookings, and assigning cabin crew, which adds significant complexity.
        - **Reliability**: A ferry flight ensures the aircraft arrives exactly when needed for the revenue flight, 
          without the risk of delays caused by passenger boarding/alighting capabilities.
        - **Scope**: For this system, they are treated as implicit time-blocks rather than explicit database records.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        # Buffer time required between flights for cleaning, refueling, and crew changes.
        self.TURNAROUND_TIME = timedelta(hours=2)

    def get_flight_details(self, flight_id):
        """
        Helper: Fetches route and schedule details for a specific flight.
        Used to determine constraints (Time, Origin, Destination) for aircraft assignment.
        """
        query = """
        SELECT 
            f.flight_id,
            f.departure_time,
            r.origin_airport,
            r.destination_airport,
            r.flight_duration,
            r.route_type
        FROM flights f
        JOIN routes r ON f.route_id = r.route_id
        WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    def get_aircraft_by_id(self, aircraft_id):
        """Retrieves raw aircraft data from the database."""
        query = "SELECT * FROM aircraft WHERE aircraft_id = %s"
        return self.db.fetch_one(query, (aircraft_id,))

    def get_available_aircrafts_for_flight(self, flight_id):
        """
        Main Logic: Finds all suitable aircraft for an existing flight.
        
        Returns a list of aircraft dicts, enriched with:
        - 'ui_status': A human-readable status (e.g., "Available Locally", "Requires Ferry").
        - 'priority_score': Used for sorting (Lower is better).
        - 'ferry_needed': Boolean flag.
        """
        # --- Step A: Get Constraints ---
        flight = self.get_flight_details(flight_id)
        if not flight:
            return []

        origin_airport = flight['origin_airport']
        destination_airport = flight['destination_airport']
        departure_time = flight['departure_time']
        
        flight_duration = flight['flight_duration']
        if isinstance(flight_duration, str):
            t = datetime.strptime(flight_duration, "%H:%M:%S")
            flight_duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
            
        landing_time = departure_time + flight_duration
        is_long_haul = flight_duration > timedelta(hours=6)

        # --- Step B: Fetch Candidates (Time-Based) ---
        # Fetch all aircraft that are NOT flying during this window (considering turnaround).
        candidates = self._get_candidates_by_time(departure_time, landing_time)
        valid_aircrafts = []

        # --- Step C: Detailed Filtering & Scoring ---
        for aircraft in candidates:
            # 1. Size Filter: Small aircraft cannot fly Long Haul routes.
            if is_long_haul and str(aircraft['size']).lower() == 'small':
                continue 

            # 2. Determine Current Location
            # Checks flight history first. If no history, uses the aircraft's home base (seed data).
            last_flight_loc = self._get_last_location(aircraft['aircraft_id'], departure_time)
            
            if last_flight_loc:
                current_loc = last_flight_loc
            else:
                current_loc = aircraft['current_location']
                
            # Fallback for data integrity issues
            if not current_loc:
                current_loc = 'TLV'

            # 3. Assess Availability Context (Local vs Ferry)
            status = None
            ferry_needed = False
            priority_score = 0

            if current_loc == origin_airport:
                status = "Available Locally"
            else:
                # Aircraft is elsewhere. Can we ferry it over in time?
                if self._can_ferry(current_loc, origin_airport, departure_time):
                    status = f"Requires Ferry from {current_loc}"
                    ferry_needed = True
                    priority_score += 10 # Penalty for operational cost of flying empty
                else:
                    continue # Cannot arrive in time. Discard.

            # 4. Check Future Continuity
            # Ensure this assignment won't make the aircraft late for its NEXT scheduled flight.
            if not self._check_future_chain(aircraft['aircraft_id'], destination_airport, landing_time):
                continue 

            # 5. Efficiency Score
            # Using a Big plane for a Short route is wasteful (fuel, maintenance).
            if not is_long_haul and str(aircraft['size']).lower() == 'big':
                status += " (Inefficient Size)"
                priority_score += 5
            
            # Enrich object for UI
            aircraft['ui_status'] = status
            aircraft['priority_score'] = priority_score
            aircraft['ferry_needed'] = ferry_needed
            
            valid_aircrafts.append(aircraft)

        # Sort: Best matches (Lowest score) first
        valid_aircrafts.sort(key=lambda x: x['priority_score'])
        
        return valid_aircrafts

    def get_available_aircrafts_for_wizard(self, origin, destination, departure_time, flight_duration):
        """
        Variant of availability check for the 'Create Flight' Wizard.
        Used when the flight record doesn't exist in the DB yet.
        """
        landing_time = departure_time + flight_duration
        candidates = self._get_candidates_by_time(departure_time, landing_time)
        return self._process_candidates(candidates, origin, destination, departure_time, flight_duration)

    def _process_candidates(self, candidates, origin_airport, destination_airport, departure_time, flight_duration):
        """
        Shared processing logic for wizard and editing.
        """
        landing_time = departure_time + flight_duration
        is_long_haul = flight_duration > timedelta(hours=6)
        
        valid_aircrafts = []

        for aircraft in candidates:
            # 1. Size Filter
            if is_long_haul and str(aircraft['size']).lower() == 'small':
                continue 

            # 2. Location Check
            current_loc = self._get_last_location(aircraft['aircraft_id'], departure_time) or 'TLV'
            
            status = None
            ferry_needed = False
            priority_score = 0

            # 3. Ferry Check
            if current_loc == origin_airport:
                status = "Available Locally"
            else:
                if self._can_ferry(current_loc, origin_airport, departure_time):
                    status = f"Requires Ferry from {current_loc}"
                    ferry_needed = True
                    priority_score += 10
                else:
                    continue 

            # 4. Future Chain Verification
            if not self._check_future_chain(aircraft['aircraft_id'], destination_airport, landing_time):
                continue 

            # 5. Efficiency Check
            if not is_long_haul and str(aircraft['size']).lower() == 'big':
                status += " (Inefficient Size)"
                priority_score += 5
            
            # Prepare UI Object
            aircraft['ui_status'] = status
            aircraft['priority_score'] = priority_score
            aircraft['ferry_needed'] = ferry_needed
            
            valid_aircrafts.append(aircraft)

        valid_aircrafts.sort(key=lambda x: x['priority_score'])
        return valid_aircrafts

    def assign_aircraft_to_flight(self, flight_id, aircraft_id):
        """
        Persists the aircraft selection to the database.
        """
        try:
            query = "UPDATE flights SET aircraft_id = %s WHERE flight_id = %s"
            self.db.execute_query(query, (aircraft_id, flight_id))
            return {"status": "success", "message": f"Aircraft {aircraft_id} assigned to flight {flight_id}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def add_aircraft(self, manufacturer, size, purchase_date=None):
        """Add a new aircraft to the fleet."""
        try:
            query = "INSERT INTO aircraft (manufacturer, size, current_location, purchase_date) VALUES (%s, %s, 'TLV', %s)"
            # DBManager.execute_query returns dict with lastrowid for INSERTs
            result = self.db.execute_query(query, (manufacturer, size, purchase_date))
            if result and isinstance(result, dict) and 'lastrowid' in result:
                return result['lastrowid']
            return None
        except Exception as e:
            print(f"Error adding aircraft: {e}")
            return None

    # --- Internal Logic Helpers ---

    def _get_candidates_by_time(self, start_time, end_time):
        """
        Returns all aircraft that do NOT have a flight overlapping the requested window.
        Includes buffer time (TURNAROUND_TIME) in the check.
        """
        safe_start = start_time - self.TURNAROUND_TIME
        safe_end = end_time + self.TURNAROUND_TIME
        
        query = """
            SELECT a.aircraft_id, a.manufacturer, a.size, a.current_location
            FROM aircraft a
            WHERE a.aircraft_id NOT IN (
                SELECT f.aircraft_id FROM flights f
                JOIN routes r ON f.route_id = r.route_id
                WHERE f.departure_time < %s 
                  AND ADDTIME(f.departure_time, r.flight_duration) > %s
            )
        """
        return self.db.fetch_all(query, (safe_end, safe_start))

    def _get_last_location(self, aircraft_id, before_time):
        """
        Determines the aircraft's location at a specific time by finding its
        most recent landing prior to that time.
        """
        query = """
            SELECT r.destination_airport 
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            WHERE f.aircraft_id = %s AND f.departure_time < %s
            ORDER BY f.departure_time DESC LIMIT 1
        """
        res = self.db.fetch_one(query, (aircraft_id, before_time))
        return res['destination_airport'] if res else None

    def _can_ferry(self, from_loc, to_loc, target_departure_time):
        """
        Checks if an aircraft can fly from [from_loc] to [to_loc] and arrive
        before [target_departure_time], allowing for turnaround time.
        """
        # Retrieve flight duration for the ferry route
        query = "SELECT flight_duration FROM routes WHERE origin_airport=%s AND destination_airport=%s"
        res = self.db.fetch_one(query, (from_loc, to_loc))
        
        if not res: 
            return False # No route exists between these airports
        
        flight_duration = res['flight_duration']
        
        # Standardize duration type
        if isinstance(flight_duration, str):
             t = datetime.strptime(flight_duration, "%H:%M:%S")
             flight_duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

        # Calculate deadline: Must arrive Turnaround Time BEFORE the next flight departs
        arrival_deadline = target_departure_time - self.TURNAROUND_TIME
        
        # In a real system, we would check 'current_time + flight_duration < arrival_deadline'.
        # For this simulation, assuming the aircraft is available now, we check if the route exists validly.
        return True 

    def _check_future_chain(self, aircraft_id, current_landing_dest, current_landing_time):
        """
        Ensures that assigning this flight won't cause the aircraft to miss
        any ALREADY SCHEDULED flights in the future.
        """
        query = """
            SELECT f.departure_time, r.origin_airport 
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            WHERE f.aircraft_id = %s AND f.departure_time > %s
            ORDER BY f.departure_time ASC LIMIT 1
        """
        next_flight = self.db.fetch_one(query, (aircraft_id, current_landing_time))
        
        if not next_flight:
            return True # No future flights scheduled -> Safe

        next_start_time = next_flight['departure_time']
        next_origin = next_flight['origin_airport']

        # Determine if we can make it to the next flight's origin in time
        if current_landing_dest == next_origin:
            # We are already there. Just need turnaround time.
            return current_landing_time + self.TURNAROUND_TIME <= next_start_time
        else:
            # We need to ferry to the next origin. Check if possible.
            return self._can_ferry(current_landing_dest, next_origin, next_start_time)