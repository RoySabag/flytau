from app.classes.db_connector import DB
from datetime import datetime

# --- מחלקה לטיפול בלקוחות רשומים (Customers) ---
class Customer:
    def __init__(self, email, first_name, last_name, dob, passport, reg_date, password):
        self.email = email                      # customer_email (PK)
        self.first_name = first_name            
        self.last_name = last_name              
        self.date_of_birth = dob                
        self.passport_number = passport         
        self.registration_date = reg_date       
        self.password = password                

    @staticmethod
    def get_customer_by_email(email):
        """בדיקה האם לקוח רשום קיים (עבור Login או מניעת כפילות)"""
        query = "SELECT * FROM customers WHERE customer_email = %s"
        params = (email,)
        
        try:
            result = DB.execute_query(query, params)
            if result and len(result) > 0:
                row = result[0]
                return Customer(
                    email=row['customer_email'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    dob=row['date_of_birth'],
                    passport=row['passport_number'],
                    reg_date=row['registration_date'],
                    password=row['login_password']
                )
            return None
        except Exception as e:
            print(f"❌ Error fetching customer: {e}")
            return None

    @staticmethod
    def insert_customer(email, password, first_name, last_name, passport, dob):
        """רישום לקוח חדש לטבלת customers"""
        if Customer.get_customer_by_email(email):
            print(f"⚠️ Registration failed: Email {email} already exists.")
            return False

        query = """
            INSERT INTO customers 
            (customer_email, first_name, last_name, date_of_birth, passport_number, registration_date, login_password)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        """
        params = (email, first_name, last_name, dob, passport, password)
        
        try:
            DB.execute_query(query, params)
            print(f"✅ Customer {first_name} {last_name} registered successfully!")
            return True
        except Exception as e:
            print(f"❌ Error inserting customer: {e}")
            return False


# --- מחלקה חדשה לטיפול באורחים (Guests) ---
class Guest:
    def __init__(self, email):
        self.email = email

    @staticmethod
    def get_guest(email):
        """בודק אם האורח כבר קיים בטבלת guests"""
        query = "SELECT * FROM guests WHERE guest_email = %s"
        params = (email,)
        result = DB.execute_query(query, params)
        
        if result and len(result) > 0:
            return Guest(email=result[0]['guest_email'])
        return None

    @staticmethod
    def ensure_guest_exists(email):
        """
        פונקציה קריטית להזמנות!
        אם המייל קיים ב-guests -> לא עושה כלום.
        אם המייל לא קיים -> יוצרת אותו.
        כך לא ניכשל ב-Foreign Key כשנבצע הזמנה.
        """
        if Guest.get_guest(email):
            return True # האורח כבר קיים, הכל טוב

        query = "INSERT INTO guests (guest_email) VALUES (%s)"
        params = (email,)
        
        try:
            DB.execute_query(query, params)
            print(f"✅ Guest {email} added to database.")
            return True
        except Exception as e:
            print(f"❌ Error adding guest: {e}")
            return False