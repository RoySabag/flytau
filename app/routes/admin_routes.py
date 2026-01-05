from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, flash
from app.classes.db_manager import DB
from app.models.daos.flight_dao import FlightDAO
from app.models.daos.aircrafts_dao import AircraftDAO
from app.models.daos.crewscheduler import CrewScheduler
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Initialize DAOs
flight_dao = FlightDAO(DB)
aircraft_dao = AircraftDAO(DB)
crew_scheduler = CrewScheduler(DB)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # גישה ל-DAO דרך האפליקציה הנוכחית (עוקף את המעגל)
    employee_dao = current_app.employee_dao

    if request.method == 'POST':
        emp_id = request.form.get('employee_id')
        password = request.form.get('password')  # בעתיד נוסיף בדיקת סיסמה

        # שימוש ב-DAO ובדיקת Admin
        if employee_dao.get_employee_by_id(emp_id) and employee_dao.is_admin(emp_id):
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
            'departure_time': request.form.get('departure_time'),
            'economy_price': request.form.get('economy_price'),
            'business_price': request.form.get('business_price')
        }
        return redirect(url_for('admin.create_flight_step2'))

    locations = flight_dao.get_all_locations()
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

    # Calculate flight details to find available aircrafts
    route_info = flight_dao.get_route_details_by_airports(wizard_data['origin'], wizard_data['destination'])
    if not route_info:
        flash("Invalid Route selected", "danger")
        return redirect(url_for('admin.create_flight_step1'))
    
    # Calculate Landing Time
    dep_time = datetime.strptime(wizard_data['departure_time'], '%Y-%m-%dT%H:%M')
    flight_duration = route_info['flight_duration']
    
    # Get available aircrafts using the new WIZARD method (fixes logic bug)
    available_aircrafts = aircraft_dao.get_available_aircrafts_for_wizard(
        wizard_data['origin'], 
        wizard_data['destination'], 
        dep_time, 
        flight_duration
    )
    
    return render_template('admin/wizard/step2_aircraft.html', 
                           aircrafts=available_aircrafts,
                           route_info=route_info)

# --- Wizard Step 3: Crew Selection ---
@admin_bp.route('/create_flight/step3', methods=['GET', 'POST'])
def create_flight_step3():
    wizard_data = session.get('wizard_data', {})
    if not wizard_data: return redirect(url_for('admin.create_flight_step1'))

    # Determine Constraints based on Aircraft
    aircraft_id = wizard_data.get('aircraft_id')
    req_pilots = 2
    req_attendants = 3
    aircraft_size = 'Small'

    if aircraft_id:
        aircraft = aircraft_dao.get_aircraft_by_id(aircraft_id)
        if aircraft and aircraft['size'] == 'Big':
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
        
        # --- Strict Validation Block ---
        if len(pilot_ids) != req_pilots:
            flash(f"Error: {aircraft_size} aircraft requires exactly {req_pilots} pilots. You selected {len(pilot_ids)}.", "danger")
            return redirect(url_for('admin.create_flight_step3'))
            
        if len(attendant_ids) != req_attendants:
            flash(f"Error: {aircraft_size} aircraft requires exactly {req_attendants} attendants. You selected {len(attendant_ids)}.", "danger")
            return redirect(url_for('admin.create_flight_step3'))
        # -------------------------------

        wizard_data['pilot_ids'] = pilot_ids
        wizard_data['attendant_ids'] = attendant_ids
        session['wizard_data'] = wizard_data
        
        # 1. Create Flight
        res = flight_dao.create_flight(
            wizard_data['origin'], 
            wizard_data['destination'], 
            wizard_data['departure_time'], 
            wizard_data['economy_price'], 
            wizard_data['business_price']
        )
        
        flight_id = res.get('flight_id')
        if not flight_id:
             flash(f"Error creating flight: {res.get('message', 'Unknown Error')}", "danger")
             return redirect(url_for('admin.create_flight_step1'))

        # 2. Assign Aircraft
        if wizard_data.get('aircraft_id'):
            aircraft_dao.assign_aircraft_to_flight(flight_id, wizard_data['aircraft_id'])

        # 3. Assign Crew
        crew_scheduler.assign_selected_crew(
            flight_id, 
            pilot_ids, 
            attendant_ids
        )

        flash(f"Flight {flight_id} Scheduled Successfully with Crew & Aircraft! ✈️", "success")
        return redirect(url_for('admin.view_flights'))

    # GET: Show Candidates (Stateless - No Draft Flight!)
    # Need route details again
    route_info = flight_dao.get_route_details_by_airports(wizard_data['origin'], wizard_data['destination'])
    dep_time = datetime.strptime(wizard_data['departure_time'], '%Y-%m-%dT%H:%M')
    
    pilots = crew_scheduler.get_candidates_for_wizard(
        wizard_data['origin'], 
        wizard_data['destination'], 
        dep_time, 
        route_info['flight_duration'],
        'Pilot', 
        50
    )
    
    attendants = crew_scheduler.get_candidates_for_wizard(
        wizard_data['origin'], 
        wizard_data['destination'], 
        dep_time, 
        route_info['flight_duration'],
        'Flight Attendant', 
        50
    )

    # Check for Shortages
    warnings = {}
    if len(pilots) < req_pilots:
        warnings['pilots'] = f"Warning: Found only {len(pilots)} pilots. You need {req_pilots}."
    
    if len(attendants) < req_attendants:
        warnings['attendants'] = f"Warning: Found only {len(attendants)} attendants. You need {req_attendants}."
    
    return render_template('admin/wizard/step3_crew.html', 
                           pilots=pilots, 
                           attendants=attendants,
                           constraints=constraints,
                           warnings=warnings) 

@admin_bp.route('/flights')
def view_flights():
    flights = flight_dao.get_all_active_flights()
    return render_template('admin/flights.html', flights=flights)
