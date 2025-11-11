#!/usr/bin/env python3
"""
Legacy helper retained for backwards compatibility.

To create the demo user set (including country-specific accounts) run
`python create_demo_users.py`. This wrapper delegates to that script so any
existing automation continues to function.
"""

from create_demo_users import main

if __name__ == "__main__":
    print("[info] create_country_users_final.py has been superseded by create_demo_users.py.")
    print("       Delegating to create_demo_users...")
    main()