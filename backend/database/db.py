import os

import mysql.connector


def get_connection():
    """Open a connection to the project's MySQL database.

    Set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME in the
    environment to match the local MySQL installation.
    """
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "drone_forensics"),
    )
