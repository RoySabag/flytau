"""
File: db_manager.py
Purpose: Singleton class to manage the MySQL connection pool and execute queries.
"""
import mysql.connector
from mysql.connector import pooling

class DBManager:
    """
    Singleton class for handling database connections via a connection pool.
    """
    _instance = None
    _connection_pool = None

    def __new__(cls):
        """Ensures only one instance of the DBManager exists."""
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._initialize_pool()
        return cls._instance

    @classmethod
    def _initialize_pool(cls):
        """Initializes the connection pool with database configuration."""
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
                print("Connection Pool Created Successfully")
            except Exception as e:
                print(f"Error Failed to create connection pool: {e}")

    def get_connection(self):
        """Retrieves a connection from the pool."""
        try:
            return self._connection_pool.get_connection()
        except Exception as e:
            print(f"Error getting connection: {e}")
            return None

    def execute_query(self, query, params=None):
        """Executes INSERT, UPDATE, or DELETE queries and returns the result/rowcount."""
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
                # If it was an INSERT, return the ID
                if query.strip().upper().startswith("INSERT"):
                     result = {'rowcount': cursor.rowcount, 'lastrowid': cursor.lastrowid}
                else:
                     result = cursor.rowcount

        except Exception as e:
            print(f"Error Query Error: {e}")
            if connection:
                connection.rollback()
        
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return result


    def fetch_all(self, query, params=None):
        """Executes a SELECT query and returns all rows as a list of dictionaries."""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def fetch_one(self, query, params=None):
        """Executes a SELECT query and returns a single row."""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True) 
        try:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

        return result

    def execute_sql_script(self, file_path):
        """Parsed and executes a multi-statement SQL script file."""
        connection = None
        cursor = None
        try:
            print(f"Reading SQL script: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            connection = self.get_connection()
            if not connection: return False
            
            cursor = connection.cursor()
            
            # Split by semicolon
            statements = sql_script.split(';')
            
            count = 0
            for statement in statements:
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        count += 1
                    except mysql.connector.Error as err:
                        print(f"⚠️ Warning executing statement: {err}")
            
            connection.commit()
            print(f"✅ Executed {count} SQL statements from {file_path}")
            return True

        except Exception as e:
            print(f"❌ Error executing SQL script: {e}")
            return False
        finally:
            if cursor: cursor.close()
            if connection: connection.close()


# Create global instance
DB = DBManager()