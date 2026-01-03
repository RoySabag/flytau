from app.classes.db_connector import DB


class EmployeeDAO:
    def get_employee_by_id(self, employee_id):
        """
        Get employee details by ID number.
        This is used for the Login process.
        """
        # SQL query to find employee by ID
        sql = "SELECT * FROM Employees WHERE ID_Number = %s"

        result = DB.execute_query(sql, (employee_id,))
        if result and len(result) > 0:
            return result[0]

        return None