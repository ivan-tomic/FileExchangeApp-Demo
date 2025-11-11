import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check if country column already exists
cursor.execute("PRAGMA table_info(invites)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

if 'country' not in column_names:
    print("Adding 'country' column to invites table...")
    
    # Add country column
    cursor.execute("ALTER TABLE invites ADD COLUMN country TEXT DEFAULT 'UK'")
    
    conn.commit()
    print("✅ Added 'country' column to invites table")
else:
    print("✅ 'country' column already exists")

# Verify
cursor.execute("PRAGMA table_info(invites)")
columns = cursor.fetchall()
print("\nInvites table structure:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()