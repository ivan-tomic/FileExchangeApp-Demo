import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("SELECT code, country, is_used FROM invites ORDER BY created_at DESC LIMIT 10")
invites = cursor.fetchall()

print("Recent invite codes:")
for inv in invites:
    print(f"  Code: {inv[0]:<15} Country: {inv[1]:<5} Used: {inv[2]}")

conn.close()