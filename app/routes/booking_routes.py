from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db_manager import DBManager
from app.services.booking_service import BookingService
from app.services.flight_service import FlightService

booking_bp = Blueprint('booking', __name__)

# Initialize Services
db = DBManager()
booking_service = BookingService(db)
flight_service = FlightService(db)

@booking_bp.route('/booking/<int:flight_id>', methods=['GET'])
def pre_book(flight_id):
    """Step 1: Quantity Selection Page"""
    flight = booking_service.get_flight_for_booking(flight_id)
    if not flight:
        flash("Flight not found", "danger")
        return redirect(url_for('routes.home'))
    return render_template('flights/pre_book.html', flight=flight)

@booking_bp.route('/booking/init', methods=['POST'])
def init_booking():
    """Step 1 Submit: process inputs and redirect to seats"""
    flight_id = request.form.get('flight_id')
    passengers = request.form.get('passengers')
    guest_email = request.form.get('guest_email')

    # Validation
    if not session.get('user_email') and not guest_email:
        flash("Please provide an email address.", "warning")
        return redirect(url_for('booking.pre_book', flight_id=flight_id))

    # Service Call
    booking_service.init_booking_process(flight_id, guest_email)

    return redirect(url_for('booking.select_seats', flight_id=flight_id, qty=passengers, guest_email=guest_email))

@booking_bp.route('/booking/<int:flight_id>/seats', methods=['GET'])
def select_seats(flight_id):
    """Step 2: Seat Selection Page"""
    quantity = int(request.args.get('qty', 1))
    guest_email = request.args.get('guest_email')
    
    flight = booking_service.get_flight_for_booking(flight_id)
    seats_by_row = booking_service.get_seat_map(flight_id)

    return render_template('flights/seats.html', 
                           flight=flight, 
                           seats_by_row=seats_by_row, 
                           quantity=quantity, 
                           guest_email=guest_email)

@booking_bp.route('/booking/summary', methods=['POST'])
def review_order():
    """Step 3: Review Order (Intermediate Step)"""
    flight_id = request.form.get('flight_id')
    guest_email = request.form.get('guest_email')
    selected_seats = request.form.getlist('selected_seats') # List of IDs
    
    if not selected_seats:
        flash("No seats selected. Please try again.", "warning")
        return redirect(url_for('booking.select_seats', flight_id=flight_id))

    # Service Call
    flight = booking_service.get_flight_for_booking(flight_id)
    seat_details, total_price = booking_service.process_seat_selection(flight_id, selected_seats)
            
    # Store Draft in Session
    session['draft_order'] = {
        'flight_id': flight_id,
        'guest_email': guest_email,
        'seat_ids': selected_seats,
        'total_price': float(total_price),
        'seat_details_view': [(s['row_number'], s['column_number'], s['class'], float(s['price'])) for s in seat_details]
    }
    
    return render_template('flights/summary.html', 
                           flight=flight, 
                           seat_details=seat_details, 
                           total_price=total_price,
                           guest_email=guest_email)

@booking_bp.route('/booking/confirm', methods=['POST'])
def confirm_booking():
    """Step 4: Finalize Order from Draft"""
    draft = session.get('draft_order')
    if not draft:
        flash("Session expired or invalid. Please start over.", "danger")
        return redirect(url_for('routes.home'))
        
    # Get Data from Draft
    flight_id = draft['flight_id']
    guest_email = draft['guest_email']
    total_price = draft['total_price']
    seat_ids = draft['seat_ids']
    customer_email = session.get('user_email')

    # Execute Booking via Service
    result = booking_service.finalize_booking(
        flight_id=flight_id,
        customer_email=customer_email,
        guest_email=guest_email,
        total_price=total_price,
        seat_ids=seat_ids
    )

    if result['status'] == 'success':
        session.pop('draft_order', None)
        return redirect(url_for('booking.confirmation', code=result['order_code']))
    else:
        flash(f"Booking Failed: {result['message']}", "danger")
        return redirect(url_for('booking.select_seats', flight_id=flight_id))

@booking_bp.route('/booking/confirmation/<code>')
def confirmation(code):
    """Step 4: Summary Page"""
    order = booking_service.get_order_confirmation(code.lower())
    if not order:
        order = booking_service.get_order_confirmation(code.upper())
        
    return render_template('flights/confirmation.html', order=order)

@booking_bp.route('/search', methods=['GET', 'POST'])
def search_flights():
    """Route to handle flight search."""
    origin = request.args.get('origin') or request.form.get('origin')
    destination = request.args.get('destination') or request.form.get('destination')
    date = request.args.get('date') or request.form.get('date')

    if not origin or not destination or not date:
        flash("Please provide Origin, Destination, and Date.", "warning")
        return redirect(url_for('routes.home'))

    # Use FlightService
    results = flight_service.search_flights(origin, destination, date)
    
    return render_template('flights/search_results.html', 
                           flights=results, 
                           search_params={'origin': origin, 'destination': destination, 'date': date})

# --- Guest Management ---

@booking_bp.route('/manage', methods=['GET', 'POST'])
def manage_login():
    """Login page for guest booking management"""
    if request.method == 'POST':
        order_code = request.form.get('order_code')
        email = request.form.get('email')
        
        if not order_code or not email:
            flash("Please provide both Booking Reference and Email.", "warning")
            return redirect(url_for('booking.manage_login'))
            
        # Verify via Service
        order = booking_service.verify_booking_access(order_code, email)
        
        if order:
            session['manage_order_code'] = order_code
            return redirect(url_for('booking.manage_dashboard'))
                
        flash("We could not find a booking matching those details.", "danger")
        return redirect(url_for('booking.manage_login'))
        
    return render_template('booking/manage_login.html')

@booking_bp.route('/manage/dashboard')
def manage_dashboard():
    """Dashboard for managing a specific booking"""
    order_code = session.get('manage_order_code')
    if not order_code:
        return redirect(url_for('booking.manage_login'))
        
    order = booking_service.get_order_confirmation(order_code)
    if not order:
        session.pop('manage_order_code', None)
        flash("Booking not found.", "danger")
        return redirect(url_for('booking.manage_login'))
        
    return render_template('booking/manage_dashboard.html', order=order)

@booking_bp.route('/manage/cancel', methods=['POST'])
def manage_cancel():
    """Cancel action from guest dashboard"""
    order_code = session.get('manage_order_code')
    if not order_code:
        return redirect(url_for('booking.manage_login'))
        
    result = booking_service.cancel_booking(order_code)
    
    if result['status'] == 'success':
        msg = f"Booking Cancelled. Refund: ${result['refund_amount']}"
        if result['fine'] > 0:
            msg += f" (Fine: ${result['fine']} applied)"
        flash(msg, "info")
    else:
        flash(result['message'], "danger")
        
    return redirect(url_for('booking.manage_dashboard'))

