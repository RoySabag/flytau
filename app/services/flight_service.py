from datetime import datetime
from app.models.daos.flight_dao import FlightDAO
from app.models.daos.aircrafts_dao import AircraftDAO
from app.models.daos.crewscheduler import CrewScheduler
from app.models.daos.statistics_dao import StatisticsDAO

class FlightService:
    """
    Service Layer for Flight Operations (Admin & Search).
    """
    def __init__(self, db_manager):
        self.flight_dao = FlightDAO(db_manager)
        self.aircraft_dao = AircraftDAO(db_manager)
        self.crew_scheduler = CrewScheduler(db_manager)
        self.stats_dao = StatisticsDAO(db_manager)

    # --- Search ---
    def search_flights(self, origin, destination, date):
        return self.flight_dao.search_flights(origin, destination, date)
    
    def get_all_locations(self):
        return self.flight_dao.get_all_locations()
        
    def get_active_flights(self, flight_id=None, status=None):
        return self.flight_dao.get_all_active_flights(flight_id, status)

    # --- Admin Wizard Logic ---
    def get_route_details(self, origin, destination):
        return self.flight_dao.get_route_details_by_airports(origin, destination)
    
    def get_available_aircrafts(self, origin, destination, dep_time_str, flight_duration):
        dep_time = datetime.strptime(dep_time_str, '%Y-%m-%dT%H:%M')
        return self.aircraft_dao.get_available_aircrafts_for_wizard(origin, destination, dep_time, flight_duration)

    def get_crew_candidates(self, origin, destination, dep_time_str, duration, role, limit=50):
        dep_time = datetime.strptime(dep_time_str, '%Y-%m-%dT%H:%M')
        return self.crew_scheduler.get_candidates_for_wizard(
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
        
        if res.get('status') != 'success':
            return res # Fail

        flight_id = res['flight_id']

        # 2. Assign Aircraft
        if wizard_data.get('aircraft_id'):
            self.aircraft_dao.assign_aircraft_to_flight(flight_id, wizard_data['aircraft_id'])

        # 3. Assign Crew
        self.crew_scheduler.assign_selected_crew(
            flight_id, 
            wizard_data['pilot_ids'], 
            wizard_data['attendant_ids']
        )
        
        return {"status": "success", "flight_id": flight_id}

    def cancel_flight(self, flight_id):
        return self.flight_dao.cancel_flight_transaction(flight_id)

    # --- Dashboard Stats ---
    def get_admin_dashboard_stats(self):
        return {
            'kpi_occupancy': self.stats_dao.get_avg_fleet_occupancy(),
            'rev_by_manufacturer': self.stats_dao.get_revenue_by_manufacturer(),
            'emp_hours': self.stats_dao.get_employee_flight_hours(),
            'cancel_rates': self.stats_dao.get_monthly_cancellation_rate(),
            'aircraft_activity': self.stats_dao.get_aircraft_activity_30_days() # Updated to new method
        }

    # --- Fleet Management ---
    def register_new_aircraft(self, manufacturer, size, economy_seats, business_seats, purchase_date=None):
        """
        Creates a new aircraft and seeds its seats.
        """
        # 1. Add Aircraft
        aircraft_id = self.aircraft_dao.add_aircraft(manufacturer, size, purchase_date)
        if not aircraft_id:
            return {"status": "error", "message": "Failed to insert aircraft record."}
            
        # 2. Seed Seats
        # Using new SeatService dynamic generation
        from app.services.seat_service import SeatService # Import here to avoid circular dep if any, or just standard import
        seat_service = SeatService(self.flight_dao.db) # Reuse DB manager
        
        success = seat_service.generate_seats(aircraft_id, business_seats, economy_seats)
        
        if success:
            return {"status": "success", "aircraft_id": aircraft_id}
        else:
            return {"status": "warning", "message": "Aircraft created but seat generation failed.", "aircraft_id": aircraft_id}
