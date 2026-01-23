"""
File: aircrafts_dao.py
Purpose: Data Access Object for managing aircraft availability (Pure SQL).
"""
from datetime import datetime, timedelta

class AircraftDAO:
    """
    Handles aircraft data access, including availability checks and location tracking.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def get_flight_details(self, flight_id):
        """Fetches operational details (time, route) for a specific flight."""
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

    def assign_aircraft_to_flight(self, flight_id, aircraft_id):
        """Updates the flight record with the assigned aircraft ID."""
        try:
            query = "UPDATE flights SET aircraft_id = %s WHERE flight_id = %s"
            self.db.execute_query(query, (aircraft_id, flight_id))
            return {"status": "success", "message": f"Aircraft {aircraft_id} assigned to flight {flight_id}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def add_aircraft(self, manufacturer, size, purchase_date=None):
        """Registers a new aircraft in the database."""
        try:
            query = "INSERT INTO aircraft (manufacturer, size, current_location, purchase_date) VALUES (%s, %s, 'TLV', %s)"
            result = self.db.execute_query(query, (manufacturer, size, purchase_date))
            if result and isinstance(result, dict) and 'lastrowid' in result:
                return result['lastrowid']
            return None
        except Exception as e:
            print(f"Error adding aircraft: {e}")
            return None

    # --- Pure SQL Helpers (Exposed for Service) ---

    def fetch_candidates_by_window(self, start_time, end_time):
        """Returns aircraft available (not flying) during the specified window."""
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
        return self.db.fetch_all(query, (end_time, start_time))

    def fetch_last_location(self, aircraft_id, before_time):
        """Determines aircraft location based on its last flight arrival before a given time."""
        query = """
            SELECT r.destination_airport 
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            WHERE f.aircraft_id = %s AND f.departure_time < %s
            ORDER BY f.departure_time DESC LIMIT 1
        """
        res = self.db.fetch_one(query, (aircraft_id, before_time))
        return res['destination_airport'] if res else None

    def fetch_route_duration(self, origin, destination):
        """Fetches the duration of a route between two airports."""
        query = "SELECT flight_duration FROM routes WHERE origin_airport=%s AND destination_airport=%s"
        return self.db.fetch_one(query, (origin, destination))

    def fetch_next_scheduled_flight(self, aircraft_id, after_time):
        """Fetches the next scheduled flight for an aircraft after a given time."""
        query = """
            SELECT f.departure_time, r.origin_airport 
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            WHERE f.aircraft_id = %s AND f.departure_time > %s
            ORDER BY f.departure_time ASC LIMIT 1
        """
        return self.db.fetch_one(query, (aircraft_id, after_time))