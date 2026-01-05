from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.classes.user import Customer, Guest  # שים לב: user באות קטנה

# --- הנה השורה שהייתה חסרה או לא נכונה ---
routes = Blueprint('routes', __name__) 
# ----------------------------------------

# --- דף הבית ---
@routes.route('/')
def home():
    return render_template('base.html')

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