from datetime import datetime, timedelta

class FlightDAO:
    def __init__(self, db_manager):
        self.db = db_manager

    # =================================================================
    # חלק א': יצירת טיסה חדשה (לוגיקה מעודכנת - ערים ומחירים)
    # =================================================================

    def get_all_locations(self):
        """
        מחזיר רשימה של כל הערים הקיימות במערכת (עבור Dropdown ב-UI).
        """
        query = """
            SELECT DISTINCT origin_airport as location FROM routes
            UNION
            SELECT DISTINCT destination_airport as location FROM routes
        """
        results = self.db.fetch_all(query)
        return [row['location'] for row in results]

    def get_route_details_by_airports(self, origin, destination):
        """
        מחזיר את פרטי המסלול (ID ומשך זמן) לפי מוצא ויעד.
        משמש לחישוב זמן נחיתה בזמן אמת ב-UI.
        """
        query = """
            SELECT route_id, flight_duration, route_type 
            FROM routes 
            WHERE origin_airport = %s AND destination_airport = %s
        """
        result = self.db.fetch_one(query, (origin, destination))
        
        if result:
            # המרת משך הטיסה לאובייקט נוח אם צריך
            duration = result['flight_duration']
            if isinstance(duration, str):
                t = datetime.strptime(duration, "%H:%M:%S")
                result['flight_duration'] = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        
        return result

    def create_flight(self, origin, destination, departure_time, economy_price, business_price):
        """
        יוצר טיסה חדשה ב-DB.
        מקבל שמות ערים (שהמנהל בחר), מוצא את ה-route_id לבד, ומכניס את המחירים.
        """
        # 1. מציאת ה-ID של הנתיב
        route_info = self.get_route_details_by_airports(origin, destination)
        if not route_info:
            return {"status": "error", "message": f"No route found from {origin} to {destination}"}
        
        route_id = route_info['route_id']

        # 2. שמירה ב-DB
        try:
            # המרה ל-datetime במידת הצורך
            if isinstance(departure_time, str):
                departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M') 

            query = """
                INSERT INTO flights 
                (route_id, aircraft_id, departure_time, economy_price, business_price, flight_status)
                VALUES (%s, NULL, %s, %s, %s, 'Scheduled')
            """
            # aircraft_id הוא NULL בהתחלה - המנהל ישבץ אותו בנפרד
            params = (route_id, departure_time, economy_price, business_price)
            res = self.db.execute_query(query, params)
            
            # Check for dictionary result (from our DBManager update)
            if isinstance(res, dict) and 'lastrowid' in res:
                return {"status": "success", "message": "Flight created successfully", "flight_id": res['lastrowid']}
            
            return {"status": "success", "message": "Flight created successfully (ID unknown)"}
        
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =================================================================
    # חלק ב': צפייה בטיסות (עבור הדשבורד)
    # =================================================================

    def get_all_active_flights(self):
        """
        שולף את כל הטיסות להצגה בטבלה למנהל.
        כולל עדכון דינמי של הסטטוסים (Scheduled, On air, Landed) לפי הזמן הנוכחי.
        """
        # 1. Fetch ALL flights (including Cancelled)
        query = """
            SELECT 
                f.flight_id,
                f.departure_time,
                f.flight_status,
                f.economy_price,
                f.business_price,
                
                -- פרטי נתיב
                r.origin_airport,
                r.destination_airport,
                r.flight_duration,
                
                -- פרטי מטוס (אם שובץ)
                f.aircraft_id,
                a.manufacturer AS aircraft_model,
                a.size AS aircraft_size,
                
                -- חישוב זמן נחיתה
                ADDTIME(f.departure_time, r.flight_duration) as arrival_time

            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            
            ORDER BY f.departure_time ASC
        """
        flights = self.db.fetch_all(query)
        if not flights:
            return []

        now = datetime.now()
        updated_flights = []

        for flight in flights:
            current_status = flight['flight_status']
            
            # If manually cancelled, we don't touch it based on time
            if current_status == 'Cancelled':
                updated_flights.append(flight)
                continue

            # Calculate proper time-based status
            # flight['departure_time'] is likely datetime, confirm type in logic if needed
            # flight['flight_duration'] is likely timedelta
            
            dep = flight['departure_time']
            if isinstance(dep, str): # Safety conversion
                 dep = datetime.strptime(dep, '%Y-%m-%d %H:%M:%S')

            duration = flight['flight_duration']
            if isinstance(duration, str):
                 t = datetime.strptime(duration, "%H:%M:%S")
                 duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

            arrival = dep + duration
            
            new_status = 'Scheduled'
            if now > arrival:
                new_status = 'Landed'
            elif now >= dep:
                new_status = 'On air'
            
            if new_status != current_status:
                try:
                    # Update DB
                    self.update_flight_status(flight['flight_id'], new_status)
                    flight['flight_status'] = new_status
                except Exception as e:
                    print(f"Error updating status for flight {flight['flight_id']}: {e}")
            
            flight['arrival_time'] = arrival # Ensure valid datetime object for template
            updated_flights.append(flight)

        return updated_flights

    def get_flight_by_id(self, flight_id):
        """
        שליפת טיסה בודדת (למשל לדף 'פרטי טיסה' או לשיבוץ צוות).
        """
        query = """
            SELECT f.*, 
                   r.origin_airport, r.destination_airport, r.flight_duration, r.route_type,
                   a.size as aircraft_size
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    # =================================================================
    # חלק ג': עדכונים ופעולות ניהול
    # =================================================================

    def update_flight_status(self, flight_id, new_status):
        """
        עדכון סטטוס (למשל: ביטול טיסה, המראה, נחיתה).
        """
        try:
            query = "UPDATE flights SET flight_status = %s WHERE flight_id = %s"
            self.db.execute_query(query, (new_status, flight_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cancel_flight_transaction(self, flight_id):
        """
        Cancels a flight and refunds all associated orders IF departure is > 72 hours away.
        Performs atomic updates.
        """
        conn = self.db.get_connection()
        if not conn:
            return {"status": "error", "message": "DB connection failed"}
            
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Check Flight Exists & Time Constraint
            # We lock the row for update to prevent race conditions
            cursor.execute("SELECT departure_time, flight_status FROM flights WHERE flight_id = %s FOR UPDATE", (flight_id,))
            flight = cursor.fetchone()
            
            if not flight:
                conn.rollback()
                return {"status": "error", "message": "Flight not found"}
                
            if flight['flight_status'] == 'Cancelled':
                conn.rollback()
                return {"status": "error", "message": "Flight is already cancelled"}

            dep_time = flight['departure_time']
            if isinstance(dep_time, str):
                dep_time = datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')

            time_diff = dep_time - datetime.now()
            hours_diff = time_diff.total_seconds() / 3600
            
            if hours_diff < 72:
                conn.rollback()
                return {"status": "error", "message": "Cannot cancel flight less than 72 hours before departure."}

            # 2. Update Flight Status
            cursor.execute("UPDATE flights SET flight_status = 'Cancelled' WHERE flight_id = %s", (flight_id,))
            
            # 3. Update Associated Orders (Cancel & Refund)
            # Find all active orders for this flight
            cursor.execute("SELECT unique_order_code FROM orders WHERE flight_id = %s AND order_status != 'Cancelled'", (flight_id,))
            active_orders = cursor.fetchall()
            
            if active_orders:
                # Update status to Cancelled and Price to 0 (Full Refund)
                cursor.execute("""
                    UPDATE orders 
                    SET order_status = 'Cancelled', total_price = 0 
                    WHERE flight_id = %s AND order_status != 'Cancelled'
                """, (flight_id,))
            
            conn.commit()
            return {"status": "success", "message": f"Flight cancelled. {len(active_orders)} orders refunded."}

        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
            conn.close()
            
    def update_prices(self, flight_id, eco_price, bus_price):
        """
        עדכון מחירים לטיסה קיימת.
        """
        try:
            query = "UPDATE flights SET economy_price = %s, business_price = %s WHERE flight_id = %s"
            self.db.execute_query(query, (eco_price, bus_price, flight_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =================================================================
    # חלק ד': בחירת מושבים (Booking)
    # =================================================================

    def get_flight_seats(self, flight_id):
        """
        מחזיר את מפת המושבים לטיסה ספציפית.
        מחזיר רשימה של מושבים עם סטטוס (is_occupied) ומחיר (לפי סוג המחלקה).
        """
        # 1. שליפת פרטי הטיסה כדי לדעת איזה מטוס זה ומה המחירים
        flight = self.get_flight_by_id(flight_id)
        if not flight:
            return None
            
        aircraft_id = flight['aircraft_id']
        economy_price = flight['economy_price']
        business_price = flight['business_price'] # אולי נרצה להציג מחיר לכל מושב

        if not aircraft_id:
            # מקרה קצה: הטיסה קיימת אך טרם שובץ מטוס
            return []

        # 2. שליפת כל המושבים של המטוס
        # טבלה: seats (seat_id, aircraft_id, row_number, column_number, class)
        query_seats = "SELECT * FROM seats WHERE aircraft_id = %s ORDER BY `row_number`, column_number"
        all_seats = self.db.fetch_all(query_seats, (aircraft_id,))

        # 3. שליפת המושבים התפוסים לטיסה זו
        # טבלה: order_lines (flight_id, seat_id, ...)
        # עדכון: מתעלמים מהזמנות שבוטלו (JOIN with orders)
        # 3. שליפת המושבים התפוסים לטיסה זו
        # טבלה: order_lines (flight_id, seat_id, ...)
        # עדכון: מתעלמים מהזמנות שבוטלו (JOIN with orders)
        query_occupied = """
            SELECT ol.seat_id 
            FROM order_lines ol
            JOIN orders o ON ol.order_id = o.unique_order_code
            WHERE ol.flight_id = %s AND o.order_status != 'Cancelled'
        """
        occupied_results = self.db.fetch_all(query_occupied, (flight_id,))
        
        # המרה ל-Set לחיפוש מהיר
        occupied_ids = {row['seat_id'] for row in occupied_results}

        # 4. מיזוג הנתונים
        final_seats = []
        for seat in all_seats:
            seat_id = seat['seat_id']
            is_occupied = seat_id in occupied_ids
            
            # הוספת שדות נוחים ל-UI
            seat['is_occupied'] = is_occupied
            seat['price'] = business_price if seat['class'] == 'Business' else economy_price
            
            final_seats.append(seat)

        return final_seats

    # =================================================================
    # חלק ה': חיפוש טיסות (Search)
    # =================================================================

    def search_flights(self, origin, destination, date):
        """
        חיפוש טיסות לפי מוצא, יעד ותאריך.
        מחזיר רשימה של טיסות מתאימות מה-DB.
        """
        try:
            # השאילתה מבצעת JOIN כדי לקבל את כל המידע הדרוש לתוצאות החיפוש
            # כולל בדיקה שהטיסה לא מבוטלת והתאריך תואם
            query = """
                SELECT 
                    f.flight_id,
                    f.departure_time,
                    f.economy_price,
                    f.business_price,
                    f.flight_status,
                    r.origin_airport,
                    r.destination_airport,
                    r.flight_duration,
                    a.manufacturer,
                    a.size
                FROM flights f
                JOIN routes r ON f.route_id = r.route_id
                LEFT JOIN aircraft a ON f.aircraft_id = a.aircraft_id
                WHERE r.origin_airport = %s
                  AND r.destination_airport = %s
                  AND DATE(f.departure_time) = %s
                  AND f.flight_status = 'Scheduled'
                ORDER BY f.departure_time ASC
            """
            
            # אם התאריך מגיע כמחרוזת, לוודא שהוא בפורמט YYYY-MM-DD
            # (בדרך כלל ה-HTML input type="date" שולח כך)
            
            return self.db.fetch_all(query, (origin, destination, date))

        except Exception as e:
            print(f"❌ Error searching flights: {e}")
            return []