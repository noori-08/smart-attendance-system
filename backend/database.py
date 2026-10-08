import os
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST","localhost"),
        user=os.getenv("DB_USER","root"),
        password=os.getenv("DB_PASSWORD","Noori08"),
        database=os.getenv("DB_NAME","attendance_system")
    )
