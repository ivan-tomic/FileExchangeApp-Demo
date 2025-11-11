import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check current table structure
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
current_schema = cursor.fetchone()[0]
print("Current schema:")
print(current_schema)
print("\n" + "="*60 + "\n")

# Drop the old constraint and recreate the table with new roles
cursor.execute("PRAGMA foreign_keys=off")

# Create new table with updated constraint
cursor.execute("""
    CREATE TABLE users_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('super','admin','user','country_user_uk','country_user_de','country_user_it','country_user_fr','country_user_es')),
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
""")

# Copy data from old table to new table
cursor.execute("""
    INSERT INTO users_new (id, username, email, password_hash, role, is_active, created_at)
    SELECT id, username, email, password_hash, role, is_active, created_at
    FROM users
""")

# Drop old table and rename new table
cursor.execute("DROP TABLE users")
cursor.execute("ALTER TABLE users_new RENAME TO users")

cursor.execute("PRAGMA foreign_keys=on")

conn.commit()
print("✅ Database schema updated!")
print("✅ New roles allowed: super, admin, user, country_user_uk, country_user_de, country_user_it, country_user_fr, country_user_es")

# Verify new schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
new_schema = cursor.fetchone()[0]
print("\nNew schema:")
print(new_schema)

conn.close()