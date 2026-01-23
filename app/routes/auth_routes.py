"""
File: auth_routes.py
Purpose: Routes for User Authentication (Login, Register, Logout) and Homepage.
"""
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
    """Landing page: Search form and Active Flight Board."""
    # Restrict Admins from Search Page
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    locations = flight_service.get_all_locations()
    
    # Filters
    flight_id_filter = request.args.get('flight_id')
    status_filter = request.args.get('status')
    
    flights = flight_service.get_active_flights(flight_id=flight_id_filter, status=status_filter)
    return render_template('index.html', locations=locations, flights=flights)

# --- Profile ---
@routes.route('/profile')
def profile():
    """Customer Profile: Shows personal info and active order history."""
    if 'user_email' not in session:
        flash("Please login to view your profile.", "warning")
        return redirect(url_for('routes.login'))
    
    email = session['user_email']
    status_filter = request.args.get('status')
    
    # Use Services
    user = auth_service.user_dao.get_customer_by_email(email) 
    orders = booking_service.get_customer_history(email, status_filter)
    
    return render_template('profile.html', orders=orders, user=user, current_filter=status_filter)

# --- Register ---
@routes.route('/register', methods=['GET', 'POST'])
def register():
    """Customer Registration Page."""
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
    """Customer Login Page."""
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
    """Ends the session."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))
