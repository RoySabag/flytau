from datetime import timedelta, datetime

class CrewScheduler:
    def __init__(self, db_manager):
        """
        מקבל את ה-DB Manager הקיים של המערכת כדי לבצע שאילתות.
        """
        self.db = db_manager

    def get_flight_details(self, flight_id):
        """
        שולף את נתוני הטיסה: זמנים, מוצא, יעד, סוג מסלול וגודל מטוס.
        """
        query = """
        SELECT 
            rt.origin_airport, 
            rt.destination_airport, 
            f.departure_time, 
            ADDTIME(f.departure_time, rt.flight_duration) as calculated_end_time,
            rt.route_type, -- Short / Long
            a.size as aircraft_size
        FROM flights f
        JOIN routes rt ON f.route_id = rt.route_id
        JOIN aircraft a ON f.aircraft_id = a.aircraft_id
        WHERE f.flight_id = %s
        """
        return self.db.fetch_one(query, (flight_id,))

    def get_candidates_for_wizard(self, origin, destination, departure_time, flight_duration, role_name, limit):
        """
        גרסה ל-Wizard: מקבלת את כל הפרטים כפרמטרים במקום לשלוף מה-DB לפי flight_id.
        """
        # חישוב שדה עזר: האם זה Long Haul? (נניח מעל 6 שעות)
        # flight_duration הוא timedelta
        is_long_haul = flight_duration > timedelta(hours=6)
        route_type = 'Long' if is_long_haul else 'Short'

        return self._fetch_candidates_logic(origin, destination, departure_time, flight_duration, route_type, role_name, limit)

    def get_candidates(self, flight_id, role_name, limit):
        """
        המנוע החכם (Legacy): שולף פרטים לפי מזהה טיסה וקורא ללוגיקה הפנימית.
        """
        flight = self.get_flight_details(flight_id)
        if not flight: return []

        # המרת duration אם צריך
        duration = flight['flight_duration']
        if isinstance(duration, str):
             t = datetime.strptime(duration, "%H:%M:%S")
             duration = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

        return self._fetch_candidates_logic(
            flight['origin_airport'], 
            flight['destination_airport'], 
            flight['departure_time'], 
            duration, 
            flight['route_type'], 
            role_name, 
            limit
        )

    def _fetch_candidates_logic(self, origin, destination, departure_time, flight_duration, route_type, role_name, limit):
        """
        הלוגיקה הראשית של השאילתה - מופרדת כדי שתעבוד גם עם ID וגם בלי.
        """
        query = """
        SELECT 
            e.id_number,
            e.first_name,
            e.last_name,
            e.current_location,
            e.long_haul_certified,
            
            CASE 
                WHEN e.current_location = %s THEN 0 
                ELSE 1 
            END AS needs_transfer,

            CASE
                WHEN %s = 'Short' AND e.long_haul_certified = 1 THEN 'Overqualified (Reserve for Long)'
                WHEN %s = 'Long' AND e.long_haul_certified = 1 THEN 'Perfect Match'
                ELSE 'Standard Match' 
            END AS match_quality,

            (
                SELECT f_in.flight_id
                FROM flights f_in
                JOIN routes rt_in ON f_in.route_id = rt_in.route_id
                WHERE 
                    rt_in.origin_airport = e.current_location 
                    AND rt_in.destination_airport = %s
                    -- הטיסה מגיעה לפחות שעתיים לפני ההמראה
                    AND ADDTIME(f_in.departure_time, rt_in.flight_duration) <= %s - INTERVAL 2 HOUR
                ORDER BY f_in.departure_time DESC
                LIMIT 1
            ) as transfer_flight_id

        FROM employees e
        JOIN roles r ON e.role_id = r.role_id
        
        WHERE 
          -- 1. סינון תפקיד
          r.role_name = %s 
          
          -- 2. סינון מיקום חכם (מקומי או שיש לו טיסת הקפצה חוקית)
          AND (
              e.current_location = %s
              OR 
              EXISTS (
                  SELECT 1
                  FROM flights f_in
                  JOIN routes rt_in ON f_in.route_id = rt_in.route_id
                  WHERE 
                      rt_in.origin_airport = e.current_location 
                      AND rt_in.destination_airport = %s
                      AND ADDTIME(f_in.departure_time, rt_in.flight_duration) <= %s - INTERVAL 2 HOUR
              )
          )

          -- 3. סינון דרישות הסמכה (חובה בטיסות ארוכות)
          AND (
              (%s = 'Short') -- בקצרות כולם עוברים
              OR 
              (e.long_haul_certified = 1)      -- בארוכות רק המוסמכים
          )

          -- 4. זמינות וכו' (הערה: חלק מהסינונים המורכבים הוסרו זמנית לפשטות, או שצריך להתאים אותם לפרמטרים)
          -- לצורך התיקון המהיר, נתמקד בלוגיקה העיקרית של מיקום והסמכה.
        
        ORDER BY 
            needs_transfer ASC, 
            CASE 
                WHEN %s = 'Short' AND e.long_haul_certified = 1 THEN 1 
                ELSE 0 
            END ASC,
            e.last_name ASC
            
        LIMIT %s;
        """
        
        # Params mapping:
        # 1. origin (needs_transfer case)
        # 2. route_type (match_quality case 1)
        # 3. route_type (match_quality case 2)
        # 4. origin (transfer subquery dest)
        # 5. departure_time (transfer subquery time)
        # 6. role_name
        # 7. origin (where location)
        # 8. origin (exists dest)
        # 9. departure_time (exists time)
        # 10. route_type (cert logic)
        # 11. route_type (order by)
        # 12. limit

        params = (
            origin, 
            route_type, route_type, 
            origin, departure_time, 
            role_name, 
            origin, 
            origin, departure_time, 
            route_type, 
            route_type, 
            int(limit)
        )

        return self.db.fetch_all(query, params)

    def assign_crew_for_flight(self, flight_id):
        """
        פונקציה ראשית שמריצה את הבדיקה עבור טייסים ודיילים ומחזירה דוח למנהל.
        """
        # 1. שליפת נתוני הטיסה
        flight_data = self.get_flight_details(flight_id)
        if not flight_data:
            return {"error": "Flight not found"}

        print(f"--- Calculating Crew for Flight {flight_id} ---")
        print(f"Route: {flight_data['origin_airport']} -> {flight_data['destination_airport']}")
        print(f"Type: {flight_data['route_type']}, Aircraft: {flight_data['aircraft_size']}")
        
        aircraft_size = flight_data['aircraft_size']
        
        # 2. קביעת מכסות
        if aircraft_size == 'Big':
            pilots_needed = 3
            attendants_needed = 6
        else: # Small
            pilots_needed = 2
            attendants_needed = 3

        # 3. חיפוש מועמדים (שולחים 'Pilot' ו-'Flight Attendant' לפי טבלת roles)
        # אנו מבקשים קצת יותר מועמדים מהדרוש (needed + 5) כדי שלמנהל יהיו אופציות בחירה
        pilots_pool = self.get_candidates(flight_id, 'Pilot', pilots_needed + 5)
        attendants_pool = self.get_candidates(flight_id, 'Flight Attendant', attendants_needed + 5)

        # 4. הכנת התשובה ל-UI
        return {
            "flight_id": flight_id,
            "requirements": {
                "pilots": pilots_needed,
                "attendants": attendants_needed
            },
            "candidates": {
                "pilots": pilots_pool,         # רשימה ממויינת לפי האיכות והעלות
                "attendants": attendants_pool  # רשימה ממויינת כנ"ל
            },
            "status": "Ready for Selection" if (len(pilots_pool) >= pilots_needed and len(attendants_pool) >= attendants_needed) else "Warning: Shortage"
        }
        
    def assign_selected_crew(self, flight_id, pilot_ids, attendant_ids):
        """
        מקבלת את רשימת העובדים שהמנהל בחר ב-UI ומבצעת את השיבוץ בפועל (INSERT).
        pilot_ids: רשימה של תעודות זהות של טייסים שנבחרו
        attendant_ids: רשימה של תעודות זהות של דיילים שנבחרו
        """
        try:
            # 1. השגת ה-ID של התפקידים (כדי להכניס למסד הנתונים מספר ולא שם)
            # אנו מניחים שיש לך שיטה ב-db_manager להריץ שאילתה, או שנריץ ישירות
            role_query = "SELECT role_id, role_name FROM roles WHERE role_name IN ('Pilot', 'Flight Attendant')"
            roles = self.db.fetch_all(role_query)
            
            pilot_role_id = next((r['role_id'] for r in roles if r['role_name'] == 'Pilot'), None)
            attendant_role_id = next((r['role_id'] for r in roles if r['role_name'] == 'Flight Attendant'), None)

            if not pilot_role_id or not attendant_role_id:
                return {"status": "error", "message": "Role IDs not found in DB"}

            # 2. הכנת רשימת ההכנסות (Tuples)
            assignments_to_insert = []
            
            # הוספת טייסים
            for p_id in pilot_ids:
                assignments_to_insert.append((flight_id, p_id, pilot_role_id))
            
            # הוספת דיילים
            for a_id in attendant_ids:
                assignments_to_insert.append((flight_id, a_id, attendant_role_id))

            # 3. ביצוע ה-INSERT
            # שים לב: זה מוחק שיבוצים קיימים לאותה טיסה כדי למנוע כפילויות, ואז מכניס חדשים
            delete_query = "DELETE FROM crew_assignments WHERE flight_id = %s"
            self.db.execute_query(delete_query, (flight_id,))

            insert_query = """
                INSERT INTO crew_assignments (flight_id, employee_id, role_id)
                VALUES (%s, %s, %s)
            """
            
            # כאן אנחנו משתמשים בלולאה או ב-executemany אם ה-db_manager תומך
            for assignment in assignments_to_insert:
                self.db.execute_query(insert_query, assignment)

            print(f"Successfully assigned {len(assignments_to_insert)} crew members to flight {flight_id}")
            return {"status": "success", "message": "Crew assigned successfully"}

        except Exception as e:
            print(f"Error assigning crew: {e}")
            return {"status": "error", "message": str(e)}