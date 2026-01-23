"""
File: flight_service.py
Purpose: Service Layer for Flight Operations (Admin Management & User Search).
"""
from datetime import datetime
from app.models.daos.flight_dao import FlightDAO
from app.services.aircraft_service import AircraftService
from app.services.crew_service import CrewService
from app.models.daos.statistics_dao import StatisticsDAO

class FlightService:
    """
    Central service for Flight Search, Creation Wizard, and Fleet Management.
    """
    def __init__(self, db_manager):
        self.flight_dao = FlightDAO(db_manager)
        self.aircraft_service = AircraftService(db_manager)
        self.crew_service = CrewService(db_manager)
        self.stats_dao = StatisticsDAO(db_manager)

    # --- Search ---
    def search_flights(self, origin, destination, date):
        """Executes a flight search for the homepage."""
        return self.flight_dao.search_flights(origin, destination, date)
    
    def get_all_locations(self):
        """Retrieves list of cities for dropdowns."""
        return self.flight_dao.get_all_locations()
        
    def get_active_flights(self, flight_id=None, status=None):
        """Fetches active flights for the admin dashboard."""
        return self.flight_dao.get_all_active_flights(flight_id, status)

    # --- Admin Wizard Logic ---
    def get_route_details(self, origin, destination):
        """Fetches route metadata."""
        return self.flight_dao.get_route_details_by_airports(origin, destination)
    
    def get_available_aircrafts(self, origin, destination, dep_time_str, flight_duration):
        """Finds aircraft candidates for the wizard."""
        dep_time = datetime.strptime(dep_time_str, '%Y-%m-%dT%H:%M')
        return self.aircraft_service.get_available_aircrafts_for_wizard(origin, destination, dep_time, flight_duration)

    def get_crew_candidates(self, origin, destination, dep_time_str, duration, role, limit=50):
        """Finds crew candidates for the wizard."""
        dep_time = datetime.strptime(dep_time_str, '%Y-%m-%dT%H:%M')
        return self.crew_service.get_candidates_for_wizard(
            origin, destination, dep_time, duration, role, limit
        )

    def create_full_flight(self, wizard_data):
        """
        Orchestrates Flight Creation, Aircraft Assignment, and Crew Assignment.
        """
        # 1. Create Flight Record
        res = self.flight_dao.create_flight(
            wizard_data['origin'], 
            wizard_data['destination'], 
            wizard_data['departure_time'], 
            wizard_data['economy_price'], 
            wizard_data['business_price']
        )
        
        # Guard Clause: Negative Prices
        if float(wizard_data['economy_price']) < 0 or float(wizard_data['business_price']) < 0:
             return {"status": "error", "message": "you can not create a flight with negative price"}

        # Guard Clause: Past Dates
        try:
            dep_time = datetime.strptime(wizard_data['departure_time'], '%Y-%m-%dT%H:%M')
            if dep_time < datetime.now():
                return {"status": "error", "message": "Departure time cannot be in the past."}
        except ValueError:
             return {"status": "error", "message": "Invalid date format."}
        
        if res.get('status') != 'success':
            return res # Fail

        flight_id = res['flight_id']

        # 2. Assign Aircraft
        if wizard_data.get('aircraft_id'):
            self.aircraft_service.assign_aircraft_to_flight(flight_id, wizard_data['aircraft_id'])

        # 3. Assign Crew
        self.crew_service.assign_selected_crew(
            flight_id, 
            wizard_data['pilot_ids'], 
            wizard_data['attendant_ids']
        )
        
        return {"status": "success", "flight_id": flight_id}

    def cancel_flight(self, flight_id):
        """Processes an admin-initiated flight cancellation."""
        return self.flight_dao.cancel_flight_transaction(flight_id)

    # --- Dashboard Stats ---
    def get_admin_dashboard_stats(self):
        """Aggregates all KPIs for the admin dashboard."""
        return {
            'kpi_occupancy': self.stats_dao.get_avg_fleet_occupancy(),
            'rev_by_manufacturer': self.stats_dao.get_revenue_by_manufacturer(),
            'emp_hours': self.stats_dao.get_employee_flight_hours(),
            'cancel_rates': self.stats_dao.get_monthly_cancellation_rate(),
            'aircraft_activity': self.stats_dao.get_aircraft_activity_30_days() # Updated to new method
        }

    # --- Fleet Management ---
    def register_new_aircraft(self, manufacturer, size, economy_seats, business_seats, purchase_date=None):
        """Creates a new aircraft and seeds its seat configuration configuration."""
        # 1. Add Aircraft
        aircraft_id = self.aircraft_service.register_new_aircraft(manufacturer, size, purchase_date)
        if not aircraft_id:
            return {"status": "error", "message": "Failed to insert aircraft record."}
            
        # 2. Seed Seats
        from app.services.seat_service import SeatService 
        seat_service = SeatService(self.flight_dao.db) 
        
        success = seat_service.generate_seats(aircraft_id, business_seats, economy_seats)
        
        if success:
            return {"status": "success", "aircraft_id": aircraft_id}
        else:
            return {"status": "warning", "message": "Aircraft created but seat generation failed.", "aircraft_id": aircraft_id}
