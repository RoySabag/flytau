"""
File: booking_service.py
Purpose: Service Layer for Booking Operations (Selection, Payment, History).
"""
from app.models.daos.flight_dao import FlightDAO
from app.models.daos.order_dao import OrderDAO
from app.models.daos.user_dao import UserDAO

class BookingService:
    """
    Orchestrates the booking flow from seat selection to order finalization.
    """
    def __init__(self, db_manager):
        self.flight_dao = FlightDAO(db_manager)
        self.order_dao = OrderDAO(db_manager)
        self.user_dao = UserDAO(db_manager)

    # --- Booking Flow ---
    def get_flight_for_booking(self, flight_id):
        """Retrieves flight details context for the booking wizard."""
        return self.flight_dao.get_flight_by_id(flight_id)

    def init_booking_process(self, flight_id, guest_email):
        """Ensures transient guest records exist before order creation."""
        if guest_email:
            self.user_dao.ensure_guest_exists(guest_email)
        return True

    def get_seat_map(self, flight_id):
        """Returns a structured dictionary of seats grouped by row for UI rendering."""
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
        """Calculates total price and retrieves text details for selected seat IDs."""
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
        """Persists the final order and associated tickets."""
        return self.order_dao.create_order(
            flight_id=flight_id,
            customer_email=customer_email,
            guest_email=guest_email,
            total_price=total_price,
            seat_ids=seat_ids
        )

    def get_order_confirmation(self, code):
        """Fetches complete order details for the confirmation page."""
        order = self.order_dao.get_order_details(code)
        return order

    # --- Manage Booking ---
    def verify_booking_access(self, order_code, email):
        """Verifies if the provided email matches the order (Security Check)."""
        order = self.order_dao.get_order_details(order_code)
        if not order:
            return None
        
        if (order.get('guest_email') and order['guest_email'].lower() == email.lower()) or \
           (order.get('customer_email') and order['customer_email'].lower() == email.lower()):
            return order
            
        return None

    def cancel_booking(self, order_code):
        """Cancels an existing order (delegates to OrderDAO)."""
        return self.order_dao.cancel_order(order_code)

    def get_customer_history(self, email, status_filter=None):
        """Retrieves order history for a logged-in customer."""
        return self.order_dao.get_customer_orders(email, status_filter)
