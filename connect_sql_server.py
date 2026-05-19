import pyodbc

# Connection string - replace with your actual server, database, username, and password
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=your_server_name;"  # e.g., localhost or IP address
    "DATABASE=your_database_name;"  # e.g., Mantenimiento_UGI
    "UID=your_username;"
    "PWD=your_password;"
)

try:
    # Establish connection
    conn = pyodbc.connect(conn_str)
    print("Connection successful!")

    # Create cursor
    cursor = conn.cursor()

    # Execute the query
    query = "SELECT * FROM DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION"
    cursor.execute(query)

    # Fetch and print results
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    # Close cursor and connection
    cursor.close()
    conn.close()
    print("Connection closed.")

except pyodbc.Error as e:
    print(f"Error connecting to SQL Server: {e}")