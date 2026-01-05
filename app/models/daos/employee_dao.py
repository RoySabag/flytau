from app.classes.db_manager import DB


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