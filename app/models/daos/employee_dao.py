class EmployeeDAO:
    """
    Data Access Object for Employee Management.

    Handles the hierarchical data structure of staff members:
    - **Base Table (staff)**: Personal info for everyone (Name, ID, Address).
    - **Sub Tables**:
        - **admins**: Authentication details for managerial access.
        - **crew_members**: Operational details for Pilots/Attendants (Location, Capabilities).
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def get_employee_by_id(self, employee_id):
        """
        Retrieves a composite employee record.
        Joins the base 'staff' data with either 'admins' or 'crew_members' details.
        
        Returns:
            dict: The merged employee object, including a synthetic 'role_type' field.
        """
        # 1. Check Admin Table first
        query_admin = "SELECT * FROM admins WHERE employee_id = %s"
        admin = self.db.fetch_one(query_admin, (employee_id,))
        if admin:
             # Fetch basic staff info and merge
             staff = self.db.fetch_one("SELECT * FROM staff WHERE employee_id = %s", (employee_id,))
             if staff:
                staff['role_type'] = 'Admin'
                staff.update(admin)
                return staff
             return None # Should not happen unless DB integrity is broken

        # 2. Check Crew Table
        query_crew = "SELECT * FROM crew_members WHERE employee_id = %s"
        crew = self.db.fetch_one(query_crew, (employee_id,))
        if crew:
             staff = self.db.fetch_one("SELECT * FROM staff WHERE employee_id = %s", (employee_id,))
             if staff:
                staff.update(crew) # role_type is already in crew_members table
                return staff
             return None

        return None

    def is_admin(self, employee_id):
        """Checks existence in the admins table."""
        query = "SELECT 1 FROM admins WHERE employee_id = %s"
        result = self.db.fetch_one(query, (employee_id,))
        return True if result else False

    def verify_admin_access(self, employee_id):
        """
        Verification helper for restricted routes.
        Prints a console warning if access is denied.
        """
        if not self.is_admin(employee_id):
            print(f"Access Denied: Employee {employee_id} does not have Admin privileges.")
            return False
        return True

    def add_employee(self, id_number, first_name, last_name, phone_number, city, street, house_no, start_date, role_type, password=None, long_haul=0):
        """
        Transactional Insert: Adds a new employee to the system.
        
        Steps:
        1. Insert into base `staff` table.
        2. Insert into appropriate role-specific table (`admins` or `crew_members`).
        """
        try:
            # 1. Insert into Staff
            query_staff = """
                INSERT INTO staff 
                (employee_id, first_name, last_name, phone_number, city, street, house_no, employment_start_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_staff = (id_number, first_name, last_name, phone_number, city, street, house_no, start_date)
            self.db.execute_query(query_staff, params_staff)

            # 2. Insert into Role Table
            if role_type == 'Admin':
                 if not password:
                     raise ValueError("Password is required for Admin role")
                 
                 query_admin = "INSERT INTO admins (employee_id, login_password) VALUES (%s, %s)"
                 self.db.execute_query(query_admin, (id_number, password))
            
            elif role_type in ['Pilot', 'Flight Attendant']:
                 query_crew = "INSERT INTO crew_members (employee_id, role_type, long_haul_certified) VALUES (%s, %s, %s)"
                 self.db.execute_query(query_crew, (id_number, role_type, long_haul))
            
            else:
                print(f"Unknown role type: {role_type}")
                return False

            return True

        except Exception as e:
            print(f"Error adding employee: {e}")
            raise e        