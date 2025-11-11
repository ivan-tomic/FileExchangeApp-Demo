#!/usr/bin/env python3
"""
Legacy helper retained for backwards compatibility.

All demo users (including country-specific accounts) are now created via
`create_demo_users.py`. This wrapper simply delegates to that script so existing
automation does not break.
"""

from create_demo_users import main

if __name__ == "__main__":
    print("[info] create_test_country_user.py has been replaced by create_demo_users.py.")
    print("       Delegating to create_demo_users...")
    main()