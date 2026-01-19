# --- Customer Entity ---
class Customer:
    def __init__(self, email, first_name, last_name, dob, passport, reg_date, password, phone_numbers=None):
        self.email = email                      # customer_email (PK)
        self.first_name = first_name            
        self.last_name = last_name              
        self.date_of_birth = dob                
        self.passport_number = passport         
        self.registration_date = reg_date       
        self.password = password                
        self.phone_numbers = phone_numbers if phone_numbers else []

# --- Guest Entity ---
class Guest:
    def __init__(self, email):
        self.email = email
