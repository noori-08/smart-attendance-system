import os
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "4000")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "attendance_system"),
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )
