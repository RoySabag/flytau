class Aircraft:
    """
    Data Transfer Object for Aircraft Entity.
    """
    def __init__(self, aircraft_id, manufacturer, size, current_location, status='Active'):
        self.aircraft_id = aircraft_id
        self.manufacturer = manufacturer
        self.size = size
        self.current_location = current_location
        self.status = status
