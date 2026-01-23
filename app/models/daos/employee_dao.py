"""
File: employee_dao.py
Purpose: Data Access Object for Employee Management (Admins, Pilots, Flight Attendants).
"""

class EmployeeDAO:
    """
    Handles access to staff data, joining hierarchical tables (admins, crew_members) as needed.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def get_employee_by_id(self, employee_id):
        """Retrieves a composite employee record merged with their specific role details."""
        # 1. Check Admin Table first
        query_admin = "SELECT * FROM admins WHERE employee_id = %s"
        admin = self.db.fetch_one(query_admin, (employee_id,))
        if admin:
             staff = self.db.fetch_one("SELECT * FROM staff WHERE employee_id = %s", (employee_id,))
             if staff:
                staff['role_type'] = 'Admin'
                staff.update(admin)
                return staff
             return None

        # 2. Check Crew Table
        query_crew = "SELECT * FROM crew_members WHERE employee_id = %s"
        crew = self.db.fetch_one(query_crew, (employee_id,))
        if crew:
             staff = self.db.fetch_one("SELECT * FROM staff WHERE employee_id = %s", (employee_id,))
             if staff:
                staff['role_type'] = staff.get('role') 
                staff.update(crew) 
                return staff
             return None

        return None

    def is_admin(self, employee_id):
        """Boolean check for admin privileges."""
        query = "SELECT role FROM staff WHERE employee_id = %s"
        result = self.db.fetch_one(query, (employee_id,))
        if result and result['role'] == 'Admin':
            return True
        return False

    def verify_admin_access(self, employee_id):
        """Logs a warning and returns False if the employee is not an Admin."""
        if not self.is_admin(employee_id):
            print(f"Access Denied: Employee {employee_id} does not have Admin privileges.")
            return False
        return True

    def add_employee(self, id_number, first_name, last_name, phone_number, city, street, house_no, start_date, role_type, password=None, long_haul=0):
        """Transactionality adds a new employee and their role-specific data."""
        try:
            # 1. Insert into Staff
            query_staff = """
                INSERT INTO staff 
                (employee_id, first_name, last_name, phone_number, city, street, house_no, employment_start_date, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_staff = (id_number, first_name, last_name, phone_number, city, street, house_no, start_date, role_type)
            self.db.execute_query(query_staff, params_staff)

            # 2. Insert into Role Table
            if role_type == 'Admin':
                 if not password:
                     raise ValueError("Password is required for Admin role")
                 
                 query_admin = "INSERT INTO admins (employee_id, login_password) VALUES (%s, %s)"
                 self.db.execute_query(query_admin, (id_number, password))
            
            elif role_type in ['Pilot', 'Flight Attendant']:
                 query_crew = "INSERT INTO crew_members (employee_id, long_haul_certified) VALUES (%s, %s)"
                 self.db.execute_query(query_crew, (id_number, long_haul))
            
            else:
                print(f"Unknown role type: {role_type}")
                return False

            return True

        except Exception as e:
            print(f"Error adding employee: {e}")
            raise e        