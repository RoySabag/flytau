from app.models.daos.flight_dao import FlightDAO
from app.models.daos.order_dao import OrderDAO
from app.models.daos.user_dao import UserDAO
from app.models.entities.user import Guest

class BookingService:
    """
    Service Layer for Booking Operations.
    """
    def __init__(self, db_manager):
        # Initialize DAOs
        self.flight_dao = FlightDAO(db_manager)
        self.order_dao = OrderDAO(db_manager)
        self.user_dao = UserDAO(db_manager)

    # --- Booking Flow ---
    def get_flight_for_booking(self, flight_id):
        return self.flight_dao.get_flight_by_id(flight_id)

    def init_booking_process(self, flight_id, guest_email):
        """Ensures guest exists if email provided."""
        if guest_email:
            self.user_dao.ensure_guest_exists(guest_email)
        return True

    def get_seat_map(self, flight_id):
        """Returns structured seat map."""
        seats = self.flight_dao.get_flight_seats(flight_id)
        seats_by_row = {}
        if seats:
            for seat in seats:
                r = seat['row_number']
                if r not in seats_by_row:
                    seats_by_row[r] = []
                seats_by_row[r].append(seat)
        
        for r in seats_by_row:
            seats_by_row[r].sort(key=lambda s: s['column_number'])
            
        return seats_by_row

    def process_seat_selection(self, flight_id, selected_seat_ids):
        """Calculates price and details for selected seats."""
        all_seats = self.flight_dao.get_flight_seats(flight_id)
        seat_map = {str(s['seat_id']): s for s in all_seats}
        
        details = []
        total_price = 0
        
        for sid in selected_seat_ids:
            if str(sid) in seat_map:
                seat = seat_map[str(sid)]
                details.append(seat)
                total_price += seat['price']
                
        return details, total_price

    def finalize_booking(self, flight_id, customer_email, guest_email, total_price, seat_ids):
        """Creates the order in DB."""
        return self.order_dao.create_order(
            flight_id=flight_id,
            customer_email=customer_email,
            guest_email=guest_email,
            total_price=total_price,
            seat_ids=seat_ids
        )

    def get_order_confirmation(self, code):
        """Fetches order for confirmation page."""
        order = self.order_dao.get_order_details(code)
        return order

    # --- Manage Booking ---
    def verify_booking_access(self, order_code, email):
        """Verifies if email matches the order for management access."""
        order = self.order_dao.get_order_details(order_code)
        if not order:
            return None
        
        # Check against guest OR customer email
        if (order.get('guest_email') and order['guest_email'].lower() == email.lower()) or \
           (order.get('customer_email') and order['customer_email'].lower() == email.lower()):
            return order
            
        return None

    def cancel_booking(self, order_code):
        return self.order_dao.cancel_order(order_code)

    def get_customer_history(self, email, status_filter=None):
        return self.order_dao.get_customer_orders(email, status_filter)
