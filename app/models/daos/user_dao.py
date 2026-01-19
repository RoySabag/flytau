from app.models.entities.user import Customer, Guest

class UserDAO:
    """
    Data Access Object for User Management (Customers and Guests).
    """
    def __init__(self, db_manager):
        self.db = db_manager

    def get_customer_by_email(self, email):
        """Checks if a registered customer exists."""
        query = "SELECT * FROM customers WHERE customer_email = %s"
        try:
            result = self.db.fetch_all(query, (email,))
            if result and len(result) > 0:
                row = result[0]
                # Fetch phone numbers
                query_phones = "SELECT phone_number FROM customer_phone_numbers WHERE customer_email = %s"
                phone_results = self.db.fetch_all(query_phones, (email,))
                phone_numbers = [p['phone_number'] for p in phone_results] if phone_results else []

                return Customer(
                    email=row['customer_email'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    dob=row['date_of_birth'],
                    passport=row['passport_number'],
                    reg_date=row['registration_date'],
                    password=row['login_password'],
                    phone_numbers=phone_numbers
                )
            return None
        except Exception as e:
            print(f"Error fetching customer: {e}")
            return None

    def insert_customer(self, email, password, first_name, last_name, passport, dob, phone_number, additional_phone_number=None):
        """Registers a new customer."""
        if self.get_customer_by_email(email):
            print(f"Registration failed: Email {email} already exists.")
            return False

        # 1. Insert into customers table
        query_customer = """
            INSERT INTO customers 
            (customer_email, first_name, last_name, date_of_birth, passport_number, registration_date, login_password)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        """
        params_customer = (email, first_name, last_name, dob, passport, password)
        
        try:
            self.db.execute_query(query_customer, params_customer)
            
            # 2. Insert primary phone number
            query_phone = "INSERT INTO customer_phone_numbers (customer_email, phone_number) VALUES (%s, %s)"
            self.db.execute_query(query_phone, (email, phone_number))

            # 3. Insert additional phone number if provided
            if additional_phone_number:
                 self.db.execute_query(query_phone, (email, additional_phone_number))

            return True
        except Exception as e:
            print(f"Error inserting customer: {e}")
            return False

    def get_guest(self, email):
        """Checks if guest exists."""
        query = "SELECT * FROM guests WHERE guest_email = %s"
        result = self.db.fetch_all(query, (email,))
        
        if result and len(result) > 0:
            return Guest(email=result[0]['guest_email'])
        return None

    def ensure_guest_exists(self, email):
        """
        Ensures a guest record exists to satisfy foreign keys.
        """
        if self.get_guest(email):
            return True 

        query = "INSERT INTO guests (guest_email) VALUES (%s)"
        try:
            self.db.execute_query(query, (email,))
            return True
        except Exception as e:
            print(f"Error adding guest: {e}")
            return False
