import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Get table structure
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()

print("Users table columns:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()