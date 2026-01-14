class StatisticsDAO:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_avg_fleet_occupancy(self):
        """
        KPI A: Average Fleet Occupancy
        Calculating occupancy rate for 'Landed' flights.
        """
        query = """
            SELECT AVG(occupancy_rate) as avg_occupancy FROM (
                SELECT 
                    f.flight_id, 
                    (COUNT(ol.seat_id) * 100.0 / (SELECT COUNT(*) FROM seats s WHERE s.aircraft_id = f.aircraft_id)) as occupancy_rate
                FROM flights f 
                LEFT JOIN order_lines ol ON f.flight_id = ol.flight_id
                -- Join with orders to ensure we count only confirmed/paid orders
                JOIN orders o ON ol.order_id = o.unique_order_code
                WHERE f.flight_status = 'Landed' 
                AND o.order_status != 'Cancelled'
                GROUP BY f.flight_id
            ) subquery
        """
        result = self.db.fetch_one(query)
        # Handle case where result is None or no flights
        val = result['avg_occupancy'] if result else 0
        return round(float(val), 1) if val else 0

    def get_revenue_by_manufacturer(self):
        """
        Chart B: Revenue by Aircraft Size & Manufacturer
        Stacked Bar Chart (X: Manufacturer, Y: Revenue, Stack: Class).
        """
        # Note: price is in 'flights' table (economy_price, business_price) or 'orders' (total_price).
        # We need sum by seat class.
        # Seats have 'class' ('Economy', 'Business').
        # Flights have 'economy_price' and 'business_price'.
        query = """
            SELECT 
                a.size, 
                a.manufacturer, 
                s.class as seat_class, 
                SUM(
                    CASE 
                        WHEN s.class = 'Economy' THEN f.economy_price 
                        WHEN s.class = 'Business' THEN f.business_price 
                        ELSE 0 
                    END
                ) AS total_revenue
            FROM order_lines ol
            JOIN orders o ON ol.order_id = o.unique_order_code
            JOIN flights f ON ol.flight_id = f.flight_id
            JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            JOIN seats s ON ol.seat_id = s.seat_id
            WHERE o.order_status != 'Cancelled'
            GROUP BY a.size, a.manufacturer, s.class
        """
        return self.db.fetch_all(query)

    def get_employee_flight_hours(self):
        """
        Chart C: Employee Flight Hours
        Bar Chart (Comparison of Short vs Long haul hours per employee role).
        """
        # Using crew_assignments table
        # flight_duration is in routes table
        query = """
            SELECT 
                r.role_name as role,
                ROUND(SUM(CASE WHEN rt.route_type = 'Short' THEN TIME_TO_SEC(rt.flight_duration)/3600 ELSE 0 END), 2) AS short_flight_hours,
                ROUND(SUM(CASE WHEN rt.route_type = 'Long' THEN TIME_TO_SEC(rt.flight_duration)/3600 ELSE 0 END), 2) AS long_flight_hours
            FROM employees e
            JOIN crew_assignments c ON e.id_number = c.employee_id
            JOIN roles r ON e.role_id = r.role_id
            JOIN flights f ON c.flight_id = f.flight_id
            JOIN routes rt ON f.route_id = rt.route_id
            WHERE f.flight_status = 'Landed'
            GROUP BY r.role_name
        """
        return self.db.fetch_all(query)

    def get_monthly_cancellation_rate(self):
        """
        Chart D: Monthly Cancellation Rate
        Line Chart (Trend over time).
        """
        # Using orders table 'order_date' and 'order_status'
        query = """
            SELECT 
                DATE_FORMAT(order_date, '%Y-%m') AS month,
                ROUND((SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) AS cancellation_rate
            FROM orders 
            GROUP BY month 
            ORDER BY month
        """
        return self.db.fetch_all(query)

    def get_monthly_aircraft_activity(self):
        """
        Chart E: Monthly Aircraft Activity Report
        Table Columns: Aircraft ID, Month, Flights, Cancelled, Utilization %, Dominant Route.
        """
        query = """
            SELECT 
                a.aircraft_id, 
                DATE_FORMAT(f.departure_time, '%Y-%m') AS month,
                SUM(CASE WHEN f.flight_status = 'Landed' THEN 1 ELSE 0 END) AS flights_executed,
                SUM(CASE WHEN f.flight_status = 'Cancelled' THEN 1 ELSE 0 END) AS flights_cancelled,
                ROUND((SUM(CASE WHEN f.flight_status = 'Landed' THEN TIME_TO_SEC(rt.flight_duration)/3600 ELSE 0 END) / (30 * 24)) * 100, 2) AS utilization_percent,
                (
                    SELECT CONCAT(r2.origin_airport, '-', r2.destination_airport) 
                    FROM flights f2 
                    JOIN routes r2 ON f2.route_id = r2.route_id
                    WHERE f2.aircraft_id = a.aircraft_id 
                    AND DATE_FORMAT(f2.departure_time, '%Y-%m') = DATE_FORMAT(f.departure_time, '%Y-%m') 
                    AND f2.flight_status = 'Landed' 
                    GROUP BY r2.origin_airport, r2.destination_airport 
                    ORDER BY COUNT(*) DESC LIMIT 1
                ) AS dominant_route
            FROM aircraft a 
            JOIN flights f ON a.aircraft_id = f.aircraft_id
            JOIN routes rt ON f.route_id = rt.route_id
            GROUP BY a.aircraft_id, month 
            ORDER BY month DESC
        """
        return self.db.fetch_all(query)
