from db import get_connection

try:
    connection = get_connection()

    if connection.is_connected():
        print("MySQL connection successful")
        print("Database:", connection.database)

    connection.close()

except Exception as e:
    print("Database connection failed:", e)