from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.classes.db_manager import DBManager
from app.models.daos.flight_dao import FlightDAO
from app.models.daos.order_dao import OrderDAO
from app.classes.user import Guest

booking_bp = Blueprint('booking', __name__)

# אתחול
db = DBManager()
flight_dao = FlightDAO(db)
order_dao = OrderDAO(db)

@booking_bp.route('/booking/<int:flight_id>', methods=['GET'])
def pre_book(flight_id):
    """Step 1: Quantity Selection Page"""
    flight = flight_dao.get_flight_by_id(flight_id)
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

    # אם המשתמש לא מחובר, הוא חייב לספק אימייל (או שזה אורח)
    if not session.get('user_email') and not guest_email:
        flash("Please provide an email address.", "warning")
        return redirect(url_for('booking.pre_book', flight_id=flight_id))

    # רישום אורח אם צריך
    if guest_email:
        Guest.ensure_guest_exists(guest_email)

    # העברה לדף המושבים עם הפרמטרים
    return redirect(url_for('booking.select_seats', flight_id=flight_id, qty=passengers, guest_email=guest_email))

@booking_bp.route('/booking/<int:flight_id>/seats', methods=['GET'])
def select_seats(flight_id):
    """Step 2: Seat Selection Page"""
    quantity = int(request.args.get('qty', 1))
    guest_email = request.args.get('guest_email')
    
    flight = flight_dao.get_flight_by_id(flight_id)
    seats = flight_dao.get_flight_seats(flight_id)
    
    # ארגון המושבים
    seats_by_row = {}
    if seats:
        for seat in seats:
            r = seat['row_number']
            if r not in seats_by_row:
                seats_by_row[r] = []
            seats_by_row[r].append(seat)

    for r in seats_by_row:
        seats_by_row[r].sort(key=lambda s: s['column_number'])

    return render_template('flights/seats.html', 
                           flight=flight, 
                           seats_by_row=seats_by_row, 
                           quantity=quantity, 
                           guest_email=guest_email)

@booking_bp.route('/booking/create', methods=['POST'])
def create_order():
    """Step 3: Create Order in DB"""
    flight_id = request.form.get('flight_id')
    guest_email = request.form.get('guest_email')
    selected_seats = request.form.getlist('selected_seats') # מקבל רשימה
    
    # שליפת פרטי הטיסה לחישוב מחיר
    flight = flight_dao.get_flight_by_id(flight_id)
    seats_info = flight_dao.get_flight_seats(flight_id) # לא הכי יעיל אבל בטוח
    
    # חישוב מחיר כולל
    total_price = 0
    seat_map = {s['seat_id']: s for s in seats_info}
    
    for seat_id in selected_seats:
        seat_id = int(seat_id)
        if seat_id in seat_map:
            total_price += seat_map[seat_id]['price']

    # זיהוי הלקוח
    customer_email = session.get('user_email')
    
    # יצירת ההזמנה
    result = order_dao.create_order(
        flight_id=flight_id,
        customer_email=customer_email,
        guest_email=guest_email,
        total_price=total_price,
        seat_ids=selected_seats
    )

    if result['status'] == 'success':
        return redirect(url_for('booking.confirmation', code=result['order_code']))
    else:
        flash(f"Booking Failed: {result['message']}", "danger")
        return redirect(url_for('routes.home'))

@booking_bp.route('/booking/confirmation/<code>')
def confirmation(code):
    """Step 4: Summary Page"""
    order = order_dao.get_order_details(code.lower()) # ב DB הסדר לא חשוב אבל נבדוק
    # או שנשתמש ב-UUID כמו שהוא
    if not order:
        order = order_dao.get_order_details(code.upper())
        
    return render_template('flights/confirmation.html', order=order)

@booking_bp.route('/search', methods=['GET', 'POST'])
def search_flights():
    """
    Route to handle flight search.
    Accepts query parameters (GET) or form data (POST).
    """
    # תמיכה גם ב-GET (אם מגיעים מקישור) וגם ב-POST (מהטופס)
    origin = request.args.get('origin') or request.form.get('origin')
    destination = request.args.get('destination') or request.form.get('destination')
    date = request.args.get('date') or request.form.get('date')

    if not origin or not destination or not date:
        flash("Please provide Origin, Destination, and Date.", "warning")
        return redirect(url_for('routes.home'))

    # ביצוע החיפוש דרך ה-DAO
    results = flight_dao.search_flights(origin, destination, date)
    
    # רינדור דף התוצאות
    return render_template('flights/search_results.html', 
                           flights=results, 
                           search_params={'origin': origin, 'destination': destination, 'date': date})


