"""
File: run.py
Purpose: Application Entry Point. Configures Flask app and registers blueprints.
"""
from flask import Flask
from database.db_manager import DBManager
# Routes
from app.routes.auth_routes import routes
from app.routes.admin_routes import admin_bp
from app.routes.booking_routes import booking_bp
from app.models.daos.employee_dao import EmployeeDAO

app = Flask(__name__)
app.secret_key = 'flytau_secret_key' 

# Initialize Core Dependencies
db = DBManager()
app.employee_dao = EmployeeDAO(db)

# Register Blueprints
app.register_blueprint(routes) 
app.register_blueprint(admin_bp, url_prefix='/admin') 
app.register_blueprint(booking_bp) 

if __name__ == '__main__':
    # Using 5001 to avoid conflicts with default Flask port
    app.run(debug=True, port=5001)
