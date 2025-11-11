#!/usr/bin/env python3
"""
Legacy helper retained for backwards compatibility.

All country demo users are now provisioned through `create_demo_users.py`. This
wrapper simply invokes that script so existing automation continues to work.
"""

from create_demo_users import main

if __name__ == "__main__":
    print("[info] create_all_country_users.py has been superseded by create_demo_users.py.")
    print("       Delegating to create_demo_users...")
    main()