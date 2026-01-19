from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, flash
from database.db_manager import DBManager
from app.services.flight_service import FlightService
from app.services.auth_service import AuthService
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Initialize Services
db = DBManager()
flight_service = FlightService(db)
auth_service = AuthService(db)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_id = request.form.get('employee_id')
        password = request.form.get('password')

        # Use Service
        if auth_service.login_admin(emp_id, password):
            session['admin_logged_in'] = True
            session['admin_id'] = emp_id
            return redirect(url_for('admin.dashboard'))
        else:
            return render_template('admin/login.html', error="Access Denied")

    return render_template('admin/login.html')

@admin_bp.route('/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')

# --- Wizard Step 1: Route & Time ---
@admin_bp.route('/create_flight/step1', methods=['GET', 'POST'])
def create_flight_step1():
    if request.method == 'POST':
        session['wizard_data'] = {
            'origin': request.form.get('origin'),
            'destination': request.form.get('destination'),
            'departure_time': request.form.get('departure_time')
        }
        return redirect(url_for('admin.create_flight_step2'))

    locations = flight_service.get_all_locations()
    return render_template('admin/wizard/step1_route.html', locations=locations)

# --- Wizard Step 2: Aircraft Selection ---
@admin_bp.route('/create_flight/step2', methods=['GET', 'POST'])
def create_flight_step2():
    wizard_data = session.get('wizard_data', {})
    if not wizard_data: return redirect(url_for('admin.create_flight_step1'))

    if request.method == 'POST':
        wizard_data['aircraft_id'] = request.form.get('aircraft_id')
        session['wizard_data'] = wizard_data 
        return redirect(url_for('admin.create_flight_step3'))

    # Logic moved to Service (partially, some orchestration remains here or can be moved deeper)
    # Keeping route orchestration simple: call Service getters
    route_info = flight_service.get_route_details(wizard_data['origin'], wizard_data['destination'])
    if not route_info:
        flash("Invalid Route selected", "danger")
        return redirect(url_for('admin.create_flight_step1'))
    
    # Get available aircrafts
    available_aircrafts = flight_service.get_available_aircrafts(
        wizard_data['origin'], 
        wizard_data['destination'], 
        wizard_data['departure_time'], 
        route_info['flight_duration']
    )
    
    return render_template('admin/wizard/step2_aircraft.html', 
                           aircrafts=available_aircrafts,
                           route_info=route_info)

# --- Wizard Step 3: Crew Selection ---
@admin_bp.route('/create_flight/step3', methods=['GET', 'POST'])
def create_flight_step3():
    wizard_data = session.get('wizard_data', {})
    if not wizard_data: return redirect(url_for('admin.create_flight_step1'))

    req_pilots = 2
    req_attendants = 3  # Start with small defaults
    aircraft_size = 'Small'

    # Re-fetch aircraft info to determine constraints (could be cached in session, but safe to fetch)
    if wizard_data.get('aircraft_id'):
        # We need DAO access here or add method to service?
        # Service has access to AircraftDAO.
        aircraft = flight_service.aircraft_dao.get_aircraft_by_id(wizard_data.get('aircraft_id'))
        if aircraft and str(aircraft['size']).lower() == 'big':
            aircraft_size = 'Big'
            req_pilots = 3
            req_attendants = 6
    
    constraints = {
        'pilots': req_pilots,
        'attendants': req_attendants,
        'size': aircraft_size
    }

    if request.method == 'POST':
        pilot_ids = request.form.getlist('pilots')
        attendant_ids = request.form.getlist('attendants')
        
        # Validation
        if len(pilot_ids) != req_pilots:
            flash(f"Error: {aircraft_size} aircraft requires exactly {req_pilots} pilots.", "danger")
            return redirect(url_for('admin.create_flight_step3'))
            
        if len(attendant_ids) != req_attendants:
            flash(f"Error: {aircraft_size} aircraft requires exactly {req_attendants} attendants.", "danger")
            return redirect(url_for('admin.create_flight_step3'))

        # Prepare Final Data
        wizard_data['pilot_ids'] = pilot_ids
        wizard_data['attendant_ids'] = attendant_ids
        
        economy_price = request.form.get('economy_price')
        business_price = request.form.get('business_price')
        if aircraft_size != 'Big': business_price = 0
        
        wizard_data['economy_price'] = economy_price
        wizard_data['business_price'] = business_price
        
        # Execute Creation via Service
        result = flight_service.create_full_flight(wizard_data)

        if result.get('status') == 'success':
            flash(f"Flight {result['flight_id']} Scheduled Successfully!", "success")
            return redirect(url_for('admin.view_flights'))
        else:
             flash(f"Error creating flight: {result.get('message')}", "danger")
             return redirect(url_for('admin.create_flight_step1'))

    # GET: Show Candidates
    route_info = flight_service.get_route_details(wizard_data['origin'], wizard_data['destination'])
    
    pilots = flight_service.get_crew_candidates(
        wizard_data['origin'], 
        wizard_data['destination'], 
        wizard_data['departure_time'], 
        route_info['flight_duration'],
        'Pilot'
    )
    
    attendants = flight_service.get_crew_candidates(
        wizard_data['origin'], 
        wizard_data['destination'], 
        wizard_data['departure_time'], 
        route_info['flight_duration'],
        'Flight Attendant'
    )

    # Check for Shortages
    warnings = {}
    if len(pilots) < req_pilots:
        warnings['pilots'] = f"Warning: Found only {len(pilots)} pilots."
    if len(attendants) < req_attendants:
        warnings['attendants'] = f"Warning: Found only {len(attendants)} attendants."
    
    return render_template('admin/wizard/step3_crew.html', 
                           pilots=pilots, 
                           attendants=attendants,
                           constraints=constraints,
                           warnings=warnings) 

@admin_bp.route('/flights')
def view_flights():
    flight_id = request.args.get('flight_id')
    status = request.args.get('status')
    
    flights = flight_service.get_active_flights(flight_id, status)
    
    return render_template('admin/flights.html', 
                           flights=flights, 
                           current_id=flight_id, 
                           current_status=status)

@admin_bp.route('/cancel_flight/<int:flight_id>', methods=['POST'])
def cancel_flight(flight_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
        
    result = flight_service.cancel_flight(flight_id)
    
    if result['status'] == 'success':
        flash(result['message'], "success")
    else:
        flash(f"Error: {result['message']}", "danger")
        
    return redirect(url_for('admin.view_flights'))

@admin_bp.route('/add_crew', methods=['GET', 'POST'])
def add_crew():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
        
    if request.method == 'POST':
        # Extract form data
        id_number = request.form.get('id_number')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone_number = request.form.get('phone_number')
        city = request.form.get('city')
        street = request.form.get('street')
        house_no = request.form.get('house_no')
        start_date = request.form.get('start_date')
        role_type = request.form.get('role_id')
        password = request.form.get('password')
        long_haul = 1 if request.form.get('long_haul') else 0

        # Basic Validation
        if not all([id_number, first_name, last_name, role_type]):
            flash("Error: Missing required fields.", "danger")
            return redirect(url_for('admin.add_crew'))

        if role_type == 'Admin':
             flash("Error: Creating new Admin users is not allowed.", "danger")
             return redirect(url_for('admin.add_crew'))

        try:
            # Check existing
            existing = auth_service.employee_dao.get_employee_by_id(id_number)
            if existing:
                flash(f"Error: Employee with ID {id_number} already exists.", "danger")
                return redirect(url_for('admin.add_crew'))

            auth_service.employee_dao.add_employee(
                id_number, first_name, last_name, phone_number, 
                city, street, house_no, start_date, role_type, 
                password, long_haul
            )
            flash(f"Employee {first_name} {last_name} added successfully!", "success")
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            flash(f"Error adding employee: {str(e)}", "danger")
            return redirect(url_for('admin.add_crew'))

    return render_template('admin/add_crew.html', active_page='add_crew')

@admin_bp.route('/dashboard/reports')
def reports_hub():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    return render_template('admin/reports/hub.html')

@admin_bp.route('/dashboard/reports/occupancy')
def report_occupancy():
    if not session.get('admin_logged_in'): return redirect(url_for('admin.login'))
    
    # Kpi Occupancy
    kpi = flight_service.stats_dao.get_avg_fleet_occupancy()
    recent_data = flight_service.stats_dao.get_recent_flights_occupancy(limit=5)
    
    return render_template('admin/reports/occupancy.html', kpi_occupancy=kpi, recent_data=recent_data)

@admin_bp.route('/dashboard/reports/revenue')
def report_revenue():
    if not session.get('admin_logged_in'): return redirect(url_for('admin.login'))
    
    data = flight_service.stats_dao.get_revenue_by_manufacturer()
    return render_template('admin/reports/revenue.html', rev_by_manufacturer=data)

@admin_bp.route('/dashboard/reports/hours')
def report_hours():
    if not session.get('admin_logged_in'): return redirect(url_for('admin.login'))
    
    data = flight_service.stats_dao.get_employee_flight_hours()
    return render_template('admin/reports/hours.html', emp_hours=data)

@admin_bp.route('/dashboard/reports/cancellations')
def report_cancellations():
    if not session.get('admin_logged_in'): return redirect(url_for('admin.login'))
    
    data = flight_service.stats_dao.get_monthly_cancellation_rate()
    return render_template('admin/reports/cancellations.html', cancel_rates=data)

@admin_bp.route('/dashboard/reports/activity')
def report_activity():
    if not session.get('admin_logged_in'): return redirect(url_for('admin.login'))
    
    data = flight_service.stats_dao.get_aircraft_activity_30_days()
    return render_template('admin/reports/activity.html', aircraft_activity=data)

@admin_bp.route('/add_aircraft', methods=['GET', 'POST'])
def add_aircraft():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        try:
            manufacturer = request.form.get('manufacturer')
            size = request.form.get('size')
            
            # Use 'or 0' to handle empty strings safely
            economy_seats = int(request.form.get('economy_seats') or 0)
            business_seats = int(request.form.get('business_seats') or 0)
            
            # Purchase date
            purchase_date = request.form.get('purchase_date') 
            if not purchase_date: purchase_date = None

            if not manufacturer or not size:
                flash("Manufacturer and Size are required.", "danger")
                return redirect(url_for('admin.add_aircraft'))

            # Call Service
            res = flight_service.register_new_aircraft(manufacturer, size, economy_seats, business_seats, purchase_date)

            if res['status'] == 'success':
                flash(f"Aircraft added successfully! (ID: {res['aircraft_id']})", "success")
                return redirect(url_for('admin.dashboard'))
            elif res['status'] == 'warning':
                flash(f"{res['message']} (ID: {res['aircraft_id']})", "warning")
                return redirect(url_for('admin.dashboard'))
            else:
                flash(f"Error: {res['message']}", "danger")
                return redirect(url_for('admin.add_aircraft'))

        except ValueError:
            flash("Error: Seat counts must be valid numbers.", "danger")
            return redirect(url_for('admin.add_aircraft'))
        except Exception as e:
            flash(f"Unexpected error: {str(e)}", "danger")
            return redirect(url_for('admin.add_aircraft'))

    return render_template('admin/add_aircraft.html', active_page='add_aircraft')

