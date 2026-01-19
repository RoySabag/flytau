class Flight:
    """
    Data Transfer Object for Flight Entity.
    """
    def __init__(self, flight_id=None, route_id=None, aircraft_id=None, departure_time=None, status='Scheduled'):
        self.flight_id = flight_id
        self.route_id = route_id
        self.aircraft_id = aircraft_id
        self.departure_time = departure_time
        self.status = status
