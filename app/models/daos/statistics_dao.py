class StatisticsDAO:
    """
    Data Access Object for Analytics & Reporting.

    Aggregates data to power the Admin Dashboard Charts:
    1.  **Fleet Occupancy**: Efficiency metric (Seats sold vs. Capacity).
    2.  **Revenue Analysis**: Financial performance by aircraft type.
    3.  **Crew Workload**: Tracking flight hours for Pilots vs. Attendants.
    4.  **Operational Reliability**: Cancellation rates and aircraft utilization.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def get_avg_fleet_occupancy(self):
        """
        KPI: Average Fleet Occupancy.
        Calculates the percentage of occupied seats for all 'Landed' flights.
        Used to assess route popularity and fleet efficiency.
        """
        query = """
            SELECT AVG(occupancy_rate) as avg_occupancy FROM (
                SELECT 
                    f.flight_id, 
                    (COUNT(ol.seat_id) * 100.0 / (SELECT COUNT(*) FROM seats s WHERE s.aircraft_id = f.aircraft_id)) as occupancy_rate
                FROM flights f 
                LEFT JOIN order_lines ol ON f.flight_id = ol.flight_id
                -- Join with orders to ensure we count only confirmed/paid orders
                JOIN orders o ON ol.unique_order_code = o.unique_order_code
                WHERE f.flight_status = 'Landed' 
                AND o.order_status != 'Cancelled'
                GROUP BY f.flight_id
            ) subquery
        """
        result = self.db.fetch_one(query)
        # Handle case where result is None or no flights
        val = result['avg_occupancy'] if result else 0
        return round(float(val), 1) if val else 0

    def get_recent_flights_occupancy(self, limit=5):
        """
        Chart Data: Occupancy per individual flight (Last N landed flights).
        """
        query = """
            SELECT 
                f.flight_id,
                r.origin_airport, 
                r.destination_airport,
                f.departure_time,
                ROUND(
                    (COUNT(ol.seat_id) * 100.0 / (SELECT COUNT(*) FROM seats s WHERE s.aircraft_id = f.aircraft_id)),
                    2
                ) as occupancy_rate
            FROM flights f
            JOIN routes r ON f.route_id = r.route_id
            LEFT JOIN order_lines ol ON f.flight_id = ol.flight_id
            LEFT JOIN orders o ON ol.unique_order_code = o.unique_order_code
            WHERE f.flight_status = 'Landed'
            AND (o.order_status != 'Cancelled' OR o.order_status IS NULL)
            GROUP BY f.flight_id
            ORDER BY f.departure_time DESC
            LIMIT %s
        """
        return self.db.fetch_all(query, (limit,))

    def get_revenue_by_manufacturer(self):
        """
        Chart: Revenue by Aircraft Manufacturer & Class.
        
        Returns data for a Stacked Bar Chart:
        - X-Axis: Aircraft Manufacturer (Boeing, Airbus)
        - Y-Axis: Total Revenue
        - Stack: Cabin Class (Economy vs Business)
        """
        # Note: Revenue is calculated by summing the price of individual tickets sold.
        # Logic: Join OrderLines -> Flights -> Aircraft -> Seats (for Class info)
        query = """
            SELECT 
                CONCAT(a.size, ' / ', a.manufacturer, ' / ', s.class) as label,
                a.manufacturer,
                SUM(
                    CASE 
                        WHEN s.class = 'Economy' THEN f.economy_price 
                        WHEN s.class = 'Business' THEN f.business_price 
                        ELSE 0 
                    END
                ) AS total_revenue
            FROM order_lines ol
            JOIN orders o ON ol.unique_order_code = o.unique_order_code
            JOIN flights f ON ol.flight_id = f.flight_id
            JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            JOIN seats s ON ol.seat_id = s.seat_id
            WHERE o.order_status != 'Cancelled'
            GROUP BY a.size, a.manufacturer, s.class
            ORDER BY total_revenue DESC
        """
        return self.db.fetch_all(query)

    def get_employee_flight_hours(self):
        """
        Chart: Employee Flight Hours Distribution.
        Compares 'Short Haul' vs 'Long Haul' work hours for Pilots and Attendants.
        """
        # Updated to use correct schema: crew_assignments -> crew_members (role_type)
        # Note: Duration is in 'routes' table.
        query = """
            SELECT 
                CONCAT(cm.first_name, ' ', cm.last_name, ' (', cm.role_type, ')') as label,
                ROUND(SUM(CASE WHEN rt.route_type = 'Short' THEN TIME_TO_SEC(rt.flight_duration)/3600 ELSE 0 END), 2) AS short_flight_hours,
                ROUND(SUM(CASE WHEN rt.route_type = 'Long' THEN TIME_TO_SEC(rt.flight_duration)/3600 ELSE 0 END), 2) AS long_flight_hours,
                ROUND(SUM(TIME_TO_SEC(rt.flight_duration)/3600), 2) as total_hours
            FROM crew_assignments ca
            JOIN crew_members cm ON ca.employee_id = cm.employee_id
            JOIN flights f ON ca.flight_id = f.flight_id
            JOIN routes rt ON f.route_id = rt.route_id
            WHERE f.flight_status = 'Landed'
            GROUP BY cm.employee_id, cm.first_name, cm.last_name, cm.role_type
            ORDER BY total_hours DESC
            LIMIT 20
        """
        return self.db.fetch_all(query)

    def get_monthly_cancellation_rate(self):
        """
        Chart: Monthly Cancellation Rate Trend.
        Shows the percentage of total orders that were cancelled (Customer + System) per month.
        """
        query = """
            SELECT 
                DATE_FORMAT(order_date, '%Y-%m') AS month,
                ROUND((SUM(CASE WHEN order_status = 'customer_cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1) AS cancellation_rate
            FROM orders 
            GROUP BY month 
            ORDER BY month DESC
            LIMIT 6
        """
        # Return reversed list to show chronological order in chart
        results = self.db.fetch_all(query)
        return results[::-1] if results else []

    def get_aircraft_activity_30_days(self):
        """
        Chart: Aircraft Activity (Last 30 Days).
        Combo Chart Data:
        - Bars: Number of Flights (Landed)
        - Line: Utilization %
        """
        # Note: Using a simplified calculation for utilization (Hours Flown / 720 hours)
        query = """
            SELECT 
                CONCAT('Plane ', a.aircraft_id, ' (', a.manufacturer, ')') as label,
                COUNT(CASE WHEN f.flight_status = 'Landed' THEN 1 END) as flights_count,
                ROUND((SUM(CASE WHEN f.flight_status = 'Landed' THEN TIME_TO_SEC(rt.flight_duration)/3600 ELSE 0 END) / 720) * 100, 1) as utilization,
                (
                    SELECT CONCAT(r2.origin_airport, '-', r2.destination_airport) 
                    FROM flights f2 
                    JOIN routes r2 ON f2.route_id = r2.route_id
                    WHERE f2.aircraft_id = a.aircraft_id 
                    AND f2.flight_status = 'Landed'
                    AND f2.departure_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY r2.origin_airport, r2.destination_airport 
                    ORDER BY COUNT(*) DESC LIMIT 1
                ) as dominant_route
            FROM aircraft a
            LEFT JOIN flights f ON a.aircraft_id = f.aircraft_id 
                AND f.departure_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            LEFT JOIN routes rt ON f.route_id = rt.route_id
            GROUP BY a.aircraft_id, a.manufacturer
            ORDER BY flights_count DESC
        """
        return self.db.fetch_all(query)
