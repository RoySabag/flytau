class EmployeeDAO:
    def __init__(self, db_manager):
        # We expect the DBManager instance here
        self.db = db_manager

    def get_employee_by_id(self, employee_id):
        """
        Retrieves a specific employee record from the database by their ID.
        """
        query = "SELECT * FROM employees WHERE id_number = %s"
        # Using the fetch_one method from your DBManager
        result = self.db.fetch_one(query, (employee_id,))
        return result

    def is_admin(self, employee_id):
        """
        Verifies if a specific employee has administrative privileges
        by checking if their role_id corresponds to 'Admin'.
        """
        employee = self.get_employee_by_id(employee_id)

        # Checking if employee exists and if role_id is 1 (Standard Admin ID)
        if employee and employee.get('role_id') == 1:
            return True

        return False

    def verify_admin_access(self, employee_id):
        """
        A service-level check to strictly verify admin presence before sensitive operations.
        """
        if not self.is_admin(employee_id):
            print(f"Access Denied: Employee {employee_id} does not have Admin privileges.")
            return False
        return True

    def add_employee(self, id_number, first_name, last_name, phone_number, city, street, house_no, start_date, role_id, password, long_haul=0):
        """
        Inserts a new employee into the database.
        """
        query = """
            INSERT INTO Employees 
            (ID_Number, First_name, Last_name, Phone_Number, City, Street, House_No, Employment_Start_Date, Role_id, Login_Password, Long_Haul_Certified)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (id_number, first_name, last_name, phone_number, city, street, house_no, start_date, role_id, password, long_haul)
        return self.db.execute_query(query, params)
        