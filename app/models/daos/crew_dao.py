"""
File: crew_dao.py
Purpose: Data Access Object for Crew operations (Candidates, Assignments).
"""

class CrewDAO:
    """
    Handles database operations for crew management.
    """
    def __init__(self, db_manager):
        self.db = db_manager

    def fetch_flight_details_for_crew(self, flight_id):
        """Fetches operational details (Time, Origin, Aircraft Size) needed for assignment."""
        query = """
        SELECT 
            rt.origin_airport, 
            rt.destination_airport, 
            f.departure_time, 
            rt.flight_duration,
            ADDTIME(f.departure_time, rt.flight_duration) as calculated_end_time,
            rt.route_type, -- Short / Long
            a.size as aircraft_size
        FROM flights f
        JOIN routes rt ON f.route_id = rt.route_id
        JOIN aircraft a ON f.aircraft_id = a.aircraft_id
        WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    def fetch_candidates(self, params):
        """Core SQL query to find, score, and sort crew members based on location and compatibility."""
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
          s.role = %s 
          
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

          -- 4. Availability Filter (No overlapping flights)
          AND NOT EXISTS (
              SELECT 1
              FROM crew_assignments ca_busy
              JOIN flights f_busy ON ca_busy.flight_id = f_busy.flight_id
              JOIN routes r_busy ON f_busy.route_id = r_busy.route_id
              WHERE ca_busy.employee_id = s.employee_id
              AND f_busy.flight_status != 'Cancelled'
              AND (
                  f_busy.departure_time < ADDTIME(%s, %s) -- Existing Start < New End
                  AND 
                  ADDTIME(f_busy.departure_time, r_busy.flight_duration) > %s -- Existing End > New Start
              )
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
        return self.db.fetch_all(query, params)

    def check_assignment_conflict(self, employee_ids_list, flight_id, flight_start, flight_end):
        """Checks if any of the employees have overlapping flights."""
        if not employee_ids_list:
            return None
            
        format_strings = ','.join(['%s'] * len(employee_ids_list))
        check_query = f"""
            SELECT s.first_name, s.last_name 
            FROM crew_assignments ca
            JOIN flights f ON ca.flight_id = f.flight_id
            JOIN routes r ON f.route_id = r.route_id
            JOIN staff s ON ca.employee_id = s.employee_id
            WHERE ca.employee_id IN ({format_strings})
            AND f.flight_id != %s -- Exclude self if re-assigning
            AND f.flight_status != 'Cancelled'
            AND (
                f.departure_time < %s
                AND ADDTIME(f.departure_time, r.flight_duration) > %s
            )
            LIMIT 1
        """
        # Note: Caller is responsible for prepping params correctly
        # But to be safe, we can construct them here if we passed individual args
        # For now, assuming caller handles param construction or we adhere to DAO pattern
        # Let's adjust slightly for cleaner usage
        
        params = list(employee_ids_list) + [flight_id, flight_end, flight_start]
        return self.db.fetch_one(check_query, tuple(params))

    def clear_assignments(self, flight_id):
        """Removes existing assignments for a flight."""
        delete_query = "DELETE FROM crew_assignments WHERE flight_id = %s"
        return self.db.execute_query(delete_query, (flight_id,))

    def insert_assignment(self, flight_id, employee_id):
        """Inserts a single crew assignment."""
        insert_query = """
            INSERT INTO crew_assignments (flight_id, employee_id)
            VALUES (%s, %s)
        """
        return self.db.execute_query(insert_query, (flight_id, employee_id))
