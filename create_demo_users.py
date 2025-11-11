#!/usr/bin/env python3
"""
Utility to generate a clean demo user database for the File Exchange Portal.

This script clears any existing user database (creating a timestamped backup)
and seeds a minimal set of demo accounts covering the roles used in the demo
environment.
"""

import argparse
import datetime as dt
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

from config import USER_DB_PATH, UK_TIMEZONE

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  email TEXT,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN (
    'super',
    'admin',
    'user',
    'country_user_uk',
    'country_user_de',
    'country_user_it',
    'country_user_fr',
    'country_user_es'
  )) DEFAULT 'user',
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
"""

CREATE_INVITES_SQL = """
CREATE TABLE IF NOT EXISTS invites (
  code TEXT PRIMARY KEY,
  country TEXT,
  is_used INTEGER NOT NULL DEFAULT 0,
  used_by TEXT,
  used_at TEXT,
  created_at TEXT NOT NULL
);
"""

DEMO_ACCOUNTS = [
    {
        "username": "demo_super",
        "email": "demo.super@example.com",
        "password": "DemoSuper!23",
        "role": "super",
    },
    {
        "username": "demo_admin",
        "email": "demo.admin@example.com",
        "password": "DemoAdmin!23",
        "role": "admin",
    },
    {
        "username": "demo_editor",
        "email": "demo.editor@example.com",
        "password": "DemoEditor!23",
        "role": "user",
    },
    {
        "username": "demo_country_uk",
        "email": "demo.country.uk@example.com",
        "password": "DemoCountryUK!23",
        "role": "country_user_uk",
    },
    {
        "username": "demo_country_de",
        "email": "demo.country.de@example.com",
        "password": "DemoCountryDE!23",
        "role": "country_user_de",
    },
    {
        "username": "demo_country_fr",
        "email": "demo.country.fr@example.com",
        "password": "DemoCountryFR!23",
        "role": "country_user_fr",
    },
    {
        "username": "demo_country_it",
        "email": "demo.country.it@example.com",
        "password": "DemoCountryIT!23",
        "role": "country_user_it",
    },
    {
        "username": "demo_country_es",
        "email": "demo.country.es@example.com",
        "password": "DemoCountryES!23",
        "role": "country_user_es",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a clean demo user database.")
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not create a backup of the current database before overwriting.",
    )
    parser.add_argument(
        "--skip-if-present",
        action="store_true",
        help="Abort if the database already exists instead of overwriting it.",
    )
    return parser.parse_args()


def backup_database(db_path: Path) -> None:
    timestamp = dt.datetime.now(UK_TIMEZONE).strftime("%Y%m%d%H%M%S")
    backup_path = db_path.with_suffix(db_path.suffix + f".bak.{timestamp}")
    db_path.replace(backup_path)
    print(f"[backup] Existing database moved to {backup_path}")


def initialise_schema(connection: sqlite3.Connection) -> None:
    connection.execute(CREATE_USERS_SQL)
    connection.execute(CREATE_INVITES_SQL)
    # Ensure country column exists on invites for older schemas
    try:
        connection.execute("ALTER TABLE invites ADD COLUMN country TEXT")
    except sqlite3.OperationalError:
        pass


def seed_demo_accounts(connection: sqlite3.Connection) -> None:
    now = dt.datetime.now(UK_TIMEZONE).isoformat()
    for account in DEMO_ACCOUNTS:
        password_hash = generate_password_hash(account["password"])
        connection.execute(
            """
            INSERT INTO users (username, email, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                account["username"],
                account["email"],
                password_hash,
                account["role"],
                now,
            ),
        )
        print(f"[ok] Created {account['username']} ({account['role']})")


def main() -> None:
    args = parse_args()
    db_path = Path(USER_DB_PATH)

    if db_path.exists():
        if args.skip_if_present:
            print("[warn] Database already exists. Aborting (--skip-if-present set).")
            return
        if not args.keep_existing:
            backup_database(db_path)
        else:
            print("[warn] Overwriting existing database without keeping a backup.")

    with sqlite3.connect(db_path) as connection:
        initialise_schema(connection)
        connection.execute("DELETE FROM users")
        connection.execute("DELETE FROM invites")
        seed_demo_accounts(connection)
        connection.commit()

    print("[done] Demo database ready:", db_path.resolve())


if __name__ == "__main__":
    main()

