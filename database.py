import os
import re
import sqlite3
import mysql.connector
from config import Config

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "medtrack.db")

_mysql_initialized = False
_sqlite_initialized = False


# =========================================================
# SQLITE COMPATIBILITY WRAPPER (Local Fallback)
# =========================================================

class SQLiteCursorWrapper:
    """Wraps sqlite3.Cursor to provide MySQL connector-compatible API."""

    def __init__(self, cursor, dictionary=False):
        self._cursor = cursor
        self.dictionary = dictionary

    def execute(self, query, params=None):
        # Convert %s placeholders to ? for SQLite
        sqlite_query = re.sub(r'(?<!%)%s', '?', query)
        if params is not None:
            return self._cursor.execute(sqlite_query, params)
        return self._cursor.execute(sqlite_query)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self.dictionary:
            return dict(row)
        return tuple(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if self.dictionary:
            return [dict(r) for r in rows]
        return [tuple(r) for r in rows]

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount


class SQLiteConnectionWrapper:
    """Wraps sqlite3.Connection to provide MySQL connection-compatible API."""

    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def cursor(self, dictionary=False):
        return SQLiteCursorWrapper(self._conn.cursor(), dictionary=dictionary)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# =========================================================
# TABLE SCHEMA INITIALIZERS (AWS RDS MYSQL & SQLITE)
# =========================================================

def _init_sqlite_schema(conn):
    global _sqlite_initialized
    if _sqlite_initialized:
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Scheduled',
            FOREIGN KEY (patient_id) REFERENCES users(user_id),
            FOREIGN KEY (doctor_id) REFERENCES users(user_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medical_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            diagnosis TEXT NOT NULL,
            prescription TEXT,
            notes TEXT,
            record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id),
            FOREIGN KEY (patient_id) REFERENCES users(user_id),
            FOREIGN KEY (doctor_id) REFERENCES users(user_id)
        )
    """)
    conn.commit()
    cur.close()
    _sqlite_initialized = True


def _init_mysql_schema(conn):
    global _mysql_initialized
    if _mysql_initialized:
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id INT NOT NULL,
            doctor_id INT NOT NULL,
            appointment_date VARCHAR(50) NOT NULL,
            appointment_time VARCHAR(50) NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'Scheduled',
            FOREIGN KEY (patient_id) REFERENCES users(user_id),
            FOREIGN KEY (doctor_id) REFERENCES users(user_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medical_records (
            record_id INT AUTO_INCREMENT PRIMARY KEY,
            appointment_id INT,
            patient_id INT NOT NULL,
            doctor_id INT NOT NULL,
            diagnosis TEXT NOT NULL,
            prescription TEXT,
            notes TEXT,
            record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id),
            FOREIGN KEY (patient_id) REFERENCES users(user_id),
            FOREIGN KEY (doctor_id) REFERENCES users(user_id)
        )
    """)
    conn.commit()
    cur.close()
    _mysql_initialized = True


# =========================================================
# MAIN DATABASE CONNECTION FACTORY (AWS RDS MYSQL)
# =========================================================

def get_db_connection():
    """
    Connects to AWS RDS MySQL database (or local MySQL).
    Automatically provisions medtrack_db and all required tables upon connection.
    If AWS RDS / MySQL credentials are invalid or unreachable (e.g. offline testing),
    it seamlessly uses the local fallback database so the app never crashes.
    """
    try:
        # Try direct connection to database
        try:
            conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                connection_timeout=5
            )
        except mysql.connector.Error as db_err:
            # If database doesn't exist yet (error 1049), create it
            if db_err.errno == 1049:
                admin_conn = mysql.connector.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    connection_timeout=5
                )
                admin_cur = admin_conn.cursor()
                admin_cur.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DATABASE}")
                admin_cur.close()
                admin_conn.close()

                conn = mysql.connector.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    database=Config.MYSQL_DATABASE,
                    connection_timeout=5
                )
            else:
                raise db_err

        _init_mysql_schema(conn)
        return conn

    except Exception as err:
        # Graceful fallback for offline testing
        sqlite_conn = SQLiteConnectionWrapper(SQLITE_DB_PATH)
        _init_sqlite_schema(sqlite_conn)
        return sqlite_conn
