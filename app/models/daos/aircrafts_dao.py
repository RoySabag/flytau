from datetime import timedelta, datetime

class AircraftDAO:
    def __init__(self, db_manager):
        self.db = db_manager
        self.TURNAROUND_TIME = timedelta(hours=2) # זמן התארגנות בין טיסות

    def get_flight_details(self, flight_id):
        """
        פונקציית עזר לשליפת פרטי הטיסה עליה אנחנו עובדים
        """
        query = """
        SELECT 
            f.flight_id,
            f.departure_time,
            r.origin_airport,
            r.destination_airport,
            r.flight_duration,
            r.route_type
        FROM flights f
        JOIN routes r ON f.route_id = r.route_id
        WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    def get_available_aircrafts_for_flight(self, flight_id):
        # --- שלב א: הכנת נתונים (זהה לקודם) ---
        flight = self.get_flight_details(flight_id)
        if not flight:
            return []

        origin_airport = flight['origin_airport']
        destination_airport = flight['destination_airport']
        departure_time = flight['departure_time']
        
        flight_duration = flight['flight_duration']
        if isinstance(flight_duration, str):
            t = datetime.strptime(flight_duration, "%H:%M:%S")
            flight_duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
            
        landing_time = departure_time + flight_duration
        is_long_haul = flight_duration > timedelta(hours=6)

        # --- שלב ב: שליפת מועמדים ---
        candidates = self._get_candidates_by_time(departure_time, landing_time)
        valid_aircrafts = []

        # --- שלב ג: הלוגיקה המעודכנת ---
        for aircraft in candidates:
            # 1. סינון גודל (Small לא עושה Long)
            if is_long_haul and aircraft['size'] == 'Small':
                continue 

            # 2. קביעת מיקום נוכחי (השינוי הגדול!)
            # קודם בודקים: איפה הוא נחת בפעם האחרונה? (היסטוריה חיה)
            last_flight_loc = self._get_last_location(aircraft['aircraft_id'], departure_time)
            
            if last_flight_loc:
                # אם יש היסטוריה - זה המיקום הקובע
                current_loc = last_flight_loc
            else:
                # אם אין היסטוריה (מטוס חדש) - לוקחים מה-DB את המיקום ההתחלתי
                current_loc = aircraft['current_location']
                
            # Fallback למקרה קיצון שגם זה ריק
            if not current_loc:
                current_loc = 'TLV'

            # 3. חישוב סטטוס (מקומי / צריך הקפצה)
            status = None
            ferry_needed = False
            priority_score = 0

            if current_loc == origin_airport:
                status = "Available Locally"
            else:
                # האם אפשר להביא אותו בטיסת העברה (Ferry)?
                if self._can_ferry(current_loc, origin_airport, departure_time):
                    status = f"Requires Ferry from {current_loc}"
                    ferry_needed = True
                    priority_score += 10 # קנס על הצורך בהעברה
                else:
                    continue # אי אפשר להביא את המטוס בזמן -> נפסל

            # 4. בדיקת רציפות עתידית
            if not self._check_future_chain(aircraft['aircraft_id'], destination_airport, landing_time):
                continue 

            # 5. ניקוד יעילות (בזבוז מטוס גדול על טיסה קצרה)
            if not is_long_haul and aircraft['size'] == 'Big':
                status += " (Inefficient Size)"
                priority_score += 5
            
            # הוספה לרשימה
            aircraft['ui_status'] = status
            aircraft['priority_score'] = priority_score
            aircraft['ferry_needed'] = ferry_needed
            
            valid_aircrafts.append(aircraft)

        # מיון לפי הציון (הכי נמוך = הכי טוב)
        valid_aircrafts.sort(key=lambda x: x['priority_score'])
        
        return valid_aircrafts

    def get_available_aircrafts_for_wizard(self, origin, destination, departure_time, flight_duration):
        """
        גרסה עבור ה-Wizard שבה הטיסה עדיין לא קיימת ב-DB.
        """
        landing_time = departure_time + flight_duration
        candidates = self._get_candidates_by_time(departure_time, landing_time)
        return self._process_candidates(candidates, origin, destination, departure_time, flight_duration)

    def _process_candidates(self, candidates, origin_airport, destination_airport, departure_time, flight_duration):
        # בדיקה האם זו טיסה ארוכה (מעל 6 שעות)
        landing_time = departure_time + flight_duration
        is_long_haul = flight_duration > timedelta(hours=6)
        
        valid_aircrafts = []

        for aircraft in candidates:
            # === תיקון באג: שימוש בערכים המדויקים מה-DB ===
            # DB Values: 'Small', 'Big'
            
            # סינון גודל: מטוס קטן לא יכול לבצע טיסה ארוכה
            if is_long_haul and aircraft['size'] == 'Small':
                continue 

            # בדיקת מיקום נוכחי
            current_loc = self._get_last_location(aircraft['aircraft_id'], departure_time) or 'TLV' # הנחת מוצא TLV
            
            status = None
            ferry_needed = False
            priority_score = 0

            # בדיקת הגעה לנקודת ההתחלה
            if current_loc == origin_airport:
                status = "Available Locally"
            else:
                # האם אפשר להביא אותו בטיסת העברה (Ferry)?
                if self._can_ferry(current_loc, origin_airport, departure_time):
                    status = f"Requires Ferry from {current_loc}"
                    ferry_needed = True
                    # priority_score += 10 # קנס על הצורך בהעברה (הערה: נטרלתי זמנית כדי לא להעניש יותר מדי)
                    priority_score += 10
                else:
                    continue # אי אפשר להביא את המטוס בזמן -> נפסל

            # בדיקת רציפות עתידית (האם יספיק לטיסה הבאה שלו?)
            if not self._check_future_chain(aircraft['aircraft_id'], destination_airport, landing_time):
                continue 

            # === תיקון תעדוף: שימוש ב-'Big' ולא 'large' ===
            # אם הטיסה קצרה והמטוס גדול -> זה בזבוז (עונש בניקוד)
            if not is_long_haul and aircraft['size'] == 'Big':
                status += " (Inefficient Size)"
                priority_score += 5
            
            # הכנת האובייקט ל-UI
            aircraft['ui_status'] = status
            aircraft['priority_score'] = priority_score
            aircraft['ferry_needed'] = ferry_needed
            
            valid_aircrafts.append(aircraft)

        # מיון: קודם כל הציון הכי נמוך (הכי מתאים)
        valid_aircrafts.sort(key=lambda x: x['priority_score'])
        
        return valid_aircrafts

    def assign_aircraft_to_flight(self, flight_id, aircraft_id):
        """
        פונקציה ל-UI: שמירת הבחירה ב-DB
        """
        try:
            query = "UPDATE flights SET aircraft_id = %s WHERE flight_id = %s"
            self.db.execute_query(query, (aircraft_id, flight_id))
            return {"status": "success", "message": f"Aircraft {aircraft_id} assigned to flight {flight_id}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --- פונקציות עזר לוגיות (נשארו כמעט אותו דבר) ---

    def _get_candidates_by_time(self, start_time, end_time):
        safe_start = start_time - self.TURNAROUND_TIME
        safe_end = end_time + self.TURNAROUND_TIME
        
        # הוספנו כאן את a.current_location לרשימת השדות
        query = """
            SELECT a.aircraft_id, a.manufacturer, a.size, a.current_location
            FROM aircraft a
            WHERE a.aircraft_id NOT IN (
                SELECT f.aircraft_id FROM flights f
                JOIN routes r ON f.route_id = r.route_id
                WHERE f.departure_time < %s 
                  AND ADDTIME(f.departure_time, r.flight_duration) > %s
            )
        """
        return self.db.fetch_all(query, (safe_end, safe_start))

    def _get_last_location(self, aircraft_id, before_time):
        query = """
            SELECT r.destination_airport 
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            WHERE f.aircraft_id = %s AND f.departure_time < %s
            ORDER BY f.departure_time DESC LIMIT 1
        """
        res = self.db.fetch_one(query, (aircraft_id, before_time))
        return res['destination_airport'] if res else None

    def _can_ferry(self, from_loc, to_loc, target_departure_time):
        # בדיקה האם קיים נתיב בטבלת routes
        query = "SELECT flight_duration FROM routes WHERE origin_airport=%s AND destination_airport=%s"
        res = self.db.fetch_one(query, (from_loc, to_loc))
        
        if not res: return False 
        
        flight_duration = res['flight_duration']
        # טיפול בהמרת זמן אם ה-Driver מחזיר מחרוזת
        if isinstance(flight_duration, str):
             t = datetime.strptime(flight_duration, "%H:%M:%S")
             flight_duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

        arrival_deadline = target_departure_time - self.TURNAROUND_TIME
        # לצורך הפרויקט נניח שאם יש נתיב, אפשר לבצע אותו
        return True 

    def _check_future_chain(self, aircraft_id, current_landing_dest, current_landing_time):
        query = """
            SELECT f.departure_time, r.origin_airport 
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            WHERE f.aircraft_id = %s AND f.departure_time > %s
            ORDER BY f.departure_time ASC LIMIT 1
        """
        next_flight = self.db.fetch_one(query, (aircraft_id, current_landing_time))
        
        if not next_flight:
            return True # אין טיסות עתידיות -> חופשי

        next_start_time = next_flight['departure_time']
        next_origin = next_flight['origin_airport']

        if current_landing_dest == next_origin:
            return current_landing_time + self.TURNAROUND_TIME <= next_start_time
        else:
            return self._can_ferry(current_landing_dest, next_origin, next_start_time)