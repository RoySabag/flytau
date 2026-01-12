from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.classes.user import Customer, Guest  # שים לב: user באות קטנה

from app.classes.db_manager import DBManager
from app.models.daos.flight_dao import FlightDAO
from app.models.daos.order_dao import OrderDAO

# --- הנה השורה שהייתה חסרה או לא נכונה ---
routes = Blueprint('routes', __name__) 
# ----------------------------------------

# אתחול DAO
db = DBManager()
flight_dao = FlightDAO(db)
order_dao = OrderDAO(db)

# --- דף הבית ---
@routes.route('/')
def home():
    # שליפת כל המיקומים (ערים) כדי לאכלס את ה-Select Box
    locations = flight_dao.get_all_locations()
    return render_template('index.html', locations=locations)

# --- פרופיל משתמש ---
@routes.route('/profile')
def profile():
    if 'user_email' not in session:
        flash("Please login to view your profile.", "warning")
        return redirect(url_for('routes.login'))
    
    email = session['user_email']
    orders = order_dao.get_customer_orders(email)
    return render_template('profile.html', orders=orders)

@routes.route('/order/cancel/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'user_email' not in session:
        return redirect(url_for('routes.login'))
        
    result = order_dao.cancel_order(order_id)
    
    if result['status'] == 'success':
        msg = f"Order Cancelled. Refund: ${result['refund_amount']}"
        if result['fine'] > 0:
            msg += f" (Fine: ${result['fine']} applied due to <36h notice)"
        flash(msg, "info")
    else:
        flash(result['message'], "danger")
        
    return redirect(url_for('routes.profile'))

# --- דף הרשמה (Register) ---
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        passport = request.form['passport']
        dob = request.form['dob']

        if Customer.insert_customer(email, password, first_name, last_name, passport, dob):
            flash('Registration Successful! Please Login.', 'success')
            return redirect(url_for('routes.login'))
        else:
            flash('Error: Email already exists or invalid data.', 'danger')
    
    return render_template('register.html')

# --- דף התחברות (Login) ---
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = Customer.get_customer_by_email(email)
        
        if user and user.password == password:
            session['user_email'] = user.email
            session['user_name'] = user.first_name
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(url_for('routes.home'))
        else:
            flash('Login Failed: Invalid email or password.', 'danger')

    return render_template('login.html')

# --- התנתקות (Logout) ---
@routes.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))