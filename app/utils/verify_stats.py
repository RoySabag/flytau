
import sys
import os

# Add parent directory to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db_manager import DBManager
from app.models.daos.statistics_dao import StatisticsDAO

def verify_stats():
    print("[INFO] Starting Statistics Verification...")
    
    try:
        db = DBManager()
        stats_dao = StatisticsDAO(db)

        # 1. Test Avg Fleet Occupancy
        print("\n[TEST] get_avg_fleet_occupancy()")
        avg_occupancy = stats_dao.get_avg_fleet_occupancy()
        print(f"[RESULT] Average Occupancy: {avg_occupancy}%")
        
        # 2. Test Recent Flights Occupancy
        print("\n[TEST] get_recent_flights_occupancy(limit=5)")
        recent = stats_dao.get_recent_flights_occupancy(limit=5)
        if recent:
            for flight in recent:
                print(f" - Flight {flight['flight_id']} ({flight['origin_airport']}->{flight['destination_airport']}): {flight['occupancy_rate']}%")
        else:
            print("[INFO] No recent landed flights found.")

        # 3. Test Revenue by Manufacturer
        print("\n[TEST] get_revenue_by_manufacturer()")
        revenue = stats_dao.get_revenue_by_manufacturer()
        if revenue:
            for item in revenue:
                print(f" - {item['label']}: ${item['total_revenue']}")
        else:
            print("[INFO] No revenue data found.")

        # 4. Test Monthly Cancellation Rate (NEW)
        print("\n[TEST] get_monthly_cancellation_rate()")
        cancellation_rates = stats_dao.get_monthly_cancellation_rate()
        if cancellation_rates:
            for rate in cancellation_rates:
                print(f" - {rate['month']}: {rate['cancellation_rate']}%")
        else:
            print("[INFO] No cancellation data found.")

        print("\n[SUCCESS] All queries executed without SQL errors.")

    except Exception as e:
        print(f"\n[FAIL] An error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verify_stats()
