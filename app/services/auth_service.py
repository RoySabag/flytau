from datetime import datetime
from app.models.daos.user_dao import UserDAO
from app.models.daos.employee_dao import EmployeeDAO

class AuthService:
    """
    Service Layer for Authentication (Customer & Employee).
    """
    def __init__(self, db_manager):
        self.user_dao = UserDAO(db_manager)
        self.employee_dao = EmployeeDAO(db_manager)

    def login_customer(self, email, password):
        """Authenticates a customer."""
        customer = self.user_dao.get_customer_by_email(email)
        if customer and customer.password == password:
            return customer
        return None

    def register_customer(self, form_data):
        """
        Registers a new customer.
        Expected keys: email, password, first_name, last_name, passport, dob, phone_number, additional_phone_number
        """
        return self.user_dao.insert_customer(
            email=form_data['email'],
            password=form_data['password'],
            first_name=form_data['first_name'],
            last_name=form_data['last_name'],
            passport=form_data['passport'],
            dob=form_data['dob'],
            phone_number=form_data['phone_number'],
            additional_phone_number=form_data.get('additional_phone_number')
        )

    def login_admin(self, employee_id, password):
        """Authenticates an admin employee."""
        # For now, password check might be simple or missing in DAO, 
        # but the route checked existence + is_admin.
        # Ideally DAO should verify password too.
        # Based on route logic:
        employee = self.employee_dao.get_employee_by_id(employee_id)
        if employee and self.employee_dao.is_admin(employee_id):
            # Verify password against database record
            # Note: In a production app, verify_hash(password, employee['login_password'])
            if employee.get('login_password') == password:
                return employee
        return None
