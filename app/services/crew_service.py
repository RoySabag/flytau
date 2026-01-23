"""
File: crew_service.py
Purpose: Service Layer for Crew Operations (Scoring, Logic, Quotas).
"""
from datetime import timedelta
from app.models.daos.crew_dao import CrewDAO

class CrewService:
    """
    Manages crew assignment logic, including certification matching and quotas.
    """

    def __init__(self, db_manager):
        self.crew_dao = CrewDAO(db_manager)

    def get_candidates_for_wizard(self, origin, destination, departure_time, flight_duration, role_name, limit):
        """Retrieves suitable crew candidates for a potential flight (Wizard flow)."""
        is_long_haul = flight_duration > timedelta(hours=6)
        route_type = 'Long' if is_long_haul else 'Short'

        return self._fetch_candidates_logic(origin, destination, departure_time, flight_duration, route_type, role_name, limit)

    def get_candidates(self, flight_id, role_name, limit):
        """Retrieves suitable crew candidates for an existing flight."""
        flight = self.crew_dao.fetch_flight_details_for_crew(flight_id)
        if not flight: return []

        duration = flight['flight_duration']
        
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
        """Orchestrates the parameters for the complex DAO query."""
        params = (
            origin, 
            route_type, route_type, 
            origin, departure_time, 
            role_name, 
            origin, 
            origin, departure_time, 
            route_type, 
            departure_time, flight_duration, departure_time,
            route_type,
            int(limit)
        )
        return self.crew_dao.fetch_candidates(params)

    def assign_crew_for_flight(self, flight_id):
        """Determines crew quotas and fetches available candidates for selection."""
        # 1. Get flight data
        flight_data = self.crew_dao.fetch_flight_details_for_crew(flight_id)
        if not flight_data:
            return {"error": "Flight not found"}

        aircraft_size = flight_data['aircraft_size']
        
        # 2. Determine Quotas
        if str(aircraft_size).lower() == 'big':
            pilots_needed = 3
            attendants_needed = 6
        else: # Small
            pilots_needed = 2
            attendants_needed = 3

        # 3. Fetch Candidates Pool
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
        """Validates and persists the final crew list, checking for conflicts."""
        try:
            # 1. Prepare Data
            assignments_to_insert = []
            for p_id in pilot_ids:
                assignments_to_insert.append((flight_id, p_id))
            for a_id in attendant_ids:
                assignments_to_insert.append((flight_id, a_id))

            # 2. Validation: Check for concurrent assignments
            flight_details = self.crew_dao.fetch_flight_details_for_crew(flight_id)
            flight_start = flight_details['departure_time']
            flight_end = flight_details['calculated_end_time']

            all_ids = pilot_ids + attendant_ids
            if all_ids:
                conflict = self.crew_dao.check_assignment_conflict(all_ids, flight_id, flight_start, flight_end)
                if conflict:
                    raise Exception(f"Concurrent assignment detected for {conflict['first_name']} {conflict['last_name']}")

            # 3. Execute Transaction
            # Clear existing assignments for this flight first (Replacement logic)
            self.crew_dao.clear_assignments(flight_id)
            
            for assignment in assignments_to_insert:
                # assignment is (flight_id, employee_id)
                self.crew_dao.insert_assignment(assignment[0], assignment[1])

            return {"status": "success", "message": "Crew assigned successfully"}

        except Exception as e:
            print(f"Error assigning crew: {e}")
            return {"status": "error", "message": str(e)}
