from flask import Flask
from database.db_manager import DBManager
# From main branch
from app.routes.auth_routes import routes
# From fix-login-system branch
from app.models.daos.employee_dao import EmployeeDAO
from app.routes.admin_routes import admin_bp
from app.routes.booking_routes import booking_bp

app = Flask(__name__)
app.secret_key = 'flytau_secret_key' # Using key from main

# Initialize DB (fix-login-system)
db = DBManager()
app.employee_dao = EmployeeDAO(db)

# Register Blueprints
app.register_blueprint(routes) # Main routes
app.register_blueprint(admin_bp, url_prefix='/admin') # Admin routes from fix-login-system
app.register_blueprint(booking_bp) # New Booking routes

if __name__ == '__main__':
    # Using 5001 to avoid conflicts
    app.run(debug=True, port=5001)
