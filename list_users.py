import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("SELECT username, email, role, is_active FROM users")
users = cursor.fetchall()

print("All users in database:")
print("-" * 60)
for user in users:
    print(f"Username: {user[0]:<20} Role: {user[2]:<20} Active: {user[3]}")

conn.close()