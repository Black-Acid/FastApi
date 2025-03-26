import sqlite3

db_path = "C:\\Users\\LENOVO\\Desktop\\FastApi\\sqlite3.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("SELECT last_update FROM Account;")
    result = cursor.fetchall()
    print("Query Result:", result)
except Exception as e:
    print("ERROR:", e)

conn.close()
