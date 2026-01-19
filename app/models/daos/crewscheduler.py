from datetime import timedelta, datetime

class CrewScheduler:
    """
    Logic Controller for Crew Management & Assignment.

    This class handles the complexity of assigning Pilots and Flight Attendants to flights.
    
    **Key Logistics handled:**
    1.  **Certification**: Ensuring 'Long Haul' flights get certified crew.
    2.  **Location Tracking**: Prioritizing crew currently at the origin airport.
    3.  **Deadheading (Transfer)**: If no local crew is available, finding crew that can arrive via another flight.
    4.  **Matching Logic**: Scoring candidates based on location match and certification efficiency.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def get_flight_details(self, flight_id):
        """
        Helper: Fetches operational details needed for crew assignment (Time, Origin, Duration, Aircraft Size).
        """
        query = """
        SELECT 
            rt.origin_airport, 
            rt.destination_airport, 
            f.departure_time, 
            ADDTIME(f.departure_time, rt.flight_duration) as calculated_end_time,
            rt.route_type, -- Short / Long
            a.size as aircraft_size
        FROM flights f
        JOIN routes rt ON f.route_id = rt.route_id
        JOIN aircraft a ON f.aircraft_id = a.aircraft_id
        WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    def get_candidates_for_wizard(self, origin, destination, departure_time, flight_duration, role_name, limit):
        """
        Retrieves candidates for a hypothetical flight (used in the 'Create Flight' Wizard).
        Calculates `route_type` on the fly since the flight record doesn't exist yet.
        """
        # Determine Route Type (Long Haul > 6 Hours)
        is_long_haul = flight_duration > timedelta(hours=6)
        route_type = 'Long' if is_long_haul else 'Short'

        return self._fetch_candidates_logic(origin, destination, departure_time, flight_duration, route_type, role_name, limit)

    def get_candidates(self, flight_id, role_name, limit):
        """
        Retrieves candidates for an existing flight.
        Fetches context from DB and delegates to the core logic.
        """
        flight = self.get_flight_details(flight_id)
        if not flight: return []

        # Convert duration string to timedelta if necessary
        duration = flight['flight_duration']
        # The query above usually returns timedelta for 'flight_duration' (from time column in MySQL),
        # but db connector might return str depending on settings. Check specific to environment.
        # In this specific query setup, it comes from routes table which is usually TIME col.
        
        # Note: We rely on _fetch_candidates_logic to handle the specific SQL parameters
        return self._fetch_candidates_logic(
            flight['origin_airport'], 
            flight['destination_airport'], 
            flight['departure_time'], 
            duration, 
            flight['route_type'], 
            role_name, 
            limit
        )

    def _fetch_candidates_logic(self, origin, destination, departure_time, flight_duration, route_type, role_name, limit):
        """
        Core SQL Logic for finding suitable crew members.
        
        **Scoring Strategy (ORDER BY):**
        1.  **Needs Transfer**: Locals (0) are preferred over Transfers (1).
        2.  **Efficiency**: Prefer 'Standard Match' over 'Overqualified' (using Long Haul crew for Short flights).
        """
        query = """
        SELECT 
            s.employee_id as id_number,
            s.first_name,
            s.last_name,
            cm.current_location,
            cm.long_haul_certified,
            
            CASE 
                WHEN cm.current_location = %s THEN 0 
                ELSE 1 
            END AS needs_transfer,

            CASE
                WHEN %s = 'Short' AND cm.long_haul_certified = 1 THEN 'Overqualified (Reserve for Long)'
                WHEN %s = 'Long' AND cm.long_haul_certified = 1 THEN 'Perfect Match'
                ELSE 'Standard Match' 
            END AS match_quality,

            (
                SELECT f_in.flight_id
                FROM flights f_in
                JOIN routes rt_in ON f_in.route_id = rt_in.route_id
                WHERE 
                    rt_in.origin_airport = cm.current_location 
                    AND rt_in.destination_airport = %s
                    -- Flight arrives at least 2 hours before departure (Buffer)
                    AND ADDTIME(f_in.departure_time, rt_in.flight_duration) <= %s - INTERVAL 2 HOUR
                ORDER BY f_in.departure_time DESC
                LIMIT 1
            ) as transfer_flight_id

        FROM staff s
        JOIN crew_members cm ON s.employee_id = cm.employee_id
        
        WHERE 
          -- 1. Role Filter
          cm.role_type = %s 
          
          -- 2. Location Filter (Local or valid transfer available)
          AND (
              cm.current_location = %s
              OR 
              EXISTS (
                  SELECT 1
                  FROM flights f_in
                  JOIN routes rt_in ON f_in.route_id = rt_in.route_id
                  WHERE 
                      rt_in.origin_airport = cm.current_location 
                      AND rt_in.destination_airport = %s
                      AND ADDTIME(f_in.departure_time, rt_in.flight_duration) <= %s - INTERVAL 2 HOUR
              )
          )

          -- 3. Certification Filter
          AND (
              (%s = 'Short') -- Everyone passes short haul requirements
              OR 
              (cm.long_haul_certified = 1) -- Only certified crew for long haul
          )

        ORDER BY 
            needs_transfer ASC, 
            CASE 
                WHEN %s = 'Short' AND cm.long_haul_certified = 1 THEN 1 
                ELSE 0 
            END ASC,
            s.last_name ASC
            
        LIMIT %s;
        """
        
        params = (
            origin, 
            route_type, route_type, 
            origin, departure_time, 
            role_name, 
            origin, 
            origin, departure_time, 
            route_type, 
            route_type, 
            int(limit)
        )

        return self.db.fetch_all(query, params)

    def assign_crew_for_flight(self, flight_id):
        """
        Orchestrates the crew selection process for the UI.
        Determines how many Pilots/Attendants are needed based on Aircraft Size.
        """
        # 1. Get flight data
        flight_data = self.get_flight_details(flight_id)
        if not flight_data:
            return {"error": "Flight not found"}

        aircraft_size = flight_data['aircraft_size']
        
        # 2. Determine Quotas
        # Logic: Big planes need more crew.
        if str(aircraft_size).lower() == 'big':
            pilots_needed = 3
            attendants_needed = 6
        else: # Small
            pilots_needed = 2
            attendants_needed = 3

        # 3. Fetch Candidates Pool
        # We fetch slightly more than needed to offer the user a choice.
        pilots_pool = self.get_candidates(flight_id, 'Pilot', pilots_needed + 5)
        attendants_pool = self.get_candidates(flight_id, 'Flight Attendant', attendants_needed + 5)

        # 4. Construct Response
        return {
            "flight_id": flight_id,
            "requirements": {
                "pilots": pilots_needed,
                "attendants": attendants_needed
            },
            "candidates": {
                "pilots": pilots_pool,
                "attendants": attendants_pool
            },
            "status": "Ready for Selection" if (len(pilots_pool) >= pilots_needed and len(attendants_pool) >= attendants_needed) else "Warning: Shortage"
        }
        
    def assign_selected_crew(self, flight_id, pilot_ids, attendant_ids):
        """
        Persists the final crew selection to the database.
        """
        try:
            # 1. Prepare Data
            assignments_to_insert = []
            
            for p_id in pilot_ids:
                assignments_to_insert.append((flight_id, p_id))
            
            for a_id in attendant_ids:
                assignments_to_insert.append((flight_id, a_id))

            # 2. Execute Transaction
            # Clear existing assignments for this flight first (Replacement logic)
            delete_query = "DELETE FROM crew_assignments WHERE flight_id = %s"
            self.db.execute_query(delete_query, (flight_id,))

            insert_query = """
                INSERT INTO crew_assignments (flight_id, employee_id)
                VALUES (%s, %s)
            """
            
            for assignment in assignments_to_insert:
                self.db.execute_query(insert_query, assignment)

            return {"status": "success", "message": "Crew assigned successfully"}

        except Exception as e:
            print(f"Error assigning crew: {e}")
            return {"status": "error", "message": str(e)}