from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db_manager import DBManager
# Services
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
from app.services.flight_service import FlightService

routes = Blueprint('routes', __name__)

# Initialize Services
db = DBManager()
auth_service = AuthService(db)
booking_service = BookingService(db)
flight_service = FlightService(db)

# --- Home Page ---
@routes.route('/')
def home():
    # Restrict Admins from Search Page
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    locations = flight_service.get_all_locations()
    flights = flight_service.get_active_flights()
    return render_template('index.html', locations=locations, flights=flights)

# --- Profile ---
@routes.route('/profile')
def profile():
    if 'user_email' not in session:
        flash("Please login to view your profile.", "warning")
        return redirect(url_for('routes.login'))
    
    email = session['user_email']
    status_filter = request.args.get('status')
    
    # Use Services
    user = auth_service.user_dao.get_customer_by_email(email) # Accessing DAO via service for now or add getter in Service
    orders = booking_service.get_customer_history(email, status_filter)
    
    return render_template('profile.html', orders=orders, user=user, current_filter=status_filter)

@routes.route('/order/cancel/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'user_email' not in session:
        return redirect(url_for('routes.login'))
        
    result = booking_service.cancel_booking(order_id)
    
    if result['status'] == 'success':
        msg = f"Order Cancelled. Refund: ${result['refund_amount']}"
        if result['fine'] > 0:
            msg += f" (Fine: ${result['fine']} applied due to <36h notice)"
        flash(msg, "info")
    else:
        flash(result['message'], "danger")
        
    return redirect(url_for('routes.profile'))

# --- Register ---
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Prepare Data
        form_data = {
            'email': request.form['email'],
            'password': request.form['password'],
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'passport': request.form['passport'],
            'dob': request.form['dob'],
            'phone_number': request.form['phone_number'],
            'additional_phone_number': request.form.get('additional_phone_number')
        }

        if auth_service.register_customer(form_data):
            flash('Registration Successful! Please Login.', 'success')
            return redirect(url_for('routes.login'))
        else:
            flash('Error: Email already exists or invalid data.', 'danger')
    
    return render_template('register.html')

# --- Login ---
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = auth_service.login_customer(email, password)
        
        if user:
            session['user_email'] = user.email
            session['user_name'] = user.first_name
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(url_for('routes.home'))
        else:
            flash('Login Failed: Invalid email or password.', 'danger')

    return render_template('login.html')

# --- Logout ---
@routes.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))
