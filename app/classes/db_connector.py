import mysql.connector
from mysql.connector import pooling

class DBManager:
    _instance = None
    _connection_pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._initialize_pool()
        return cls._instance

    @classmethod
    def _initialize_pool(cls):
        if cls._connection_pool is None:
            try:
                db_config = {
                    "host": "localhost",
                    "user": "root",
                    "password": "root",
                    "database": "flytau",
                    "charset": "utf8mb4",
                    "collation": "utf8mb4_unicode_ci"
                }

                cls._connection_pool = pooling.MySQLConnectionPool(
                    pool_name="flytau_pool",
                    pool_size=5,
                    pool_reset_session=True,
                    **db_config
                )
                print("✅ Connection Pool Created Successfully")
            except Exception as e:
                print(f"❌ Failed to create connection pool: {e}")

    def get_connection(self):
        try:
            return self._connection_pool.get_connection()
        except Exception as e:
            print(f"❌ Error getting connection: {e}")
            return None

    def execute_query(self, query, params=None):
        connection = None
        cursor = None
        result = None
        
        try:
            connection = self.get_connection()
            if connection is None:
                return None
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.rowcount

        except Exception as e:
            print(f"❌ Query Error: {e}")
            if connection:
                connection.rollback()
        
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return result

# יצירת אובייקט נגיש
DB = DBManager()