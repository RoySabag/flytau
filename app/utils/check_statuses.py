
import sys
import os

# Add parent directory to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db_manager import DBManager
from app.models.daos.statistics_dao import StatisticsDAO

def check_statuses():
    db = DBManager()
    query = "DESCRIBE orders"
    results = db.fetch_all(query)
    for r in results:
        print(r['Field'])
    result = db.fetch_one(query)
    print(result)

if __name__ == "__main__":
    check_statuses()
