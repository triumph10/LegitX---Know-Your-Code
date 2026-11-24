import sqlite3

conn = sqlite3.connect("data/legitx.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM evaluations")

print("Total saved evaluations:", cursor.fetchone()[0])

cursor.execute("SELECT * FROM evaluations")

for row in cursor.fetchall():
    print(row)

conn.close()