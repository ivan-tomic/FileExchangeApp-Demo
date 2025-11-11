# Demo User Credentials

Run `python create_demo_users.py` to generate a clean database with these demo
accounts. All passwords are intentionally simple but unique per role to make it
easy to test access controls.

## Quick Reference

| Username | Password | Role | Notes |
|----------|----------|------|-------|
| **demo_super** | `DemoSuper!23` | super | Full access, including invite/code management |
| **demo_admin** | `DemoAdmin!23` | admin | Uploads, approvals, and user management |
| **demo_editor** | `DemoEditor!23` | user | Standard newsroom/editor workflow |
| **demo_country_uk** | `DemoCountryUK!23` | country_user_uk | Sees only UK files |
| **demo_country_de** | `DemoCountryDE!23` | country_user_de | Sees only DE files |
| **demo_country_fr** | `DemoCountryFR!23` | country_user_fr | Sees only FR files |
| **demo_country_it** | `DemoCountryIT!23` | country_user_it | Sees only IT files |
| **demo_country_es** | `DemoCountryES!23` | country_user_es | Sees only ES files |

## Suggested Test Flow

1. `demo_super` – verify admin console, invite generation, and archive access.
2. `demo_admin` – check upload, metadata editing, approvals, and dashboard links.
3. `demo_editor` – confirm Business Reporter user workflow (upload + needs review).
4. `demo_country_uk` – ensure country-scoped users only see UK entries.
5. `demo_country_de` (or FR/IT/ES variants) – confirm cross-country isolation and publication status badges.

Use `/admin/users` (visible to `demo_super`) to reset passwords or deactivate
accounts as part of your demo narrative.

## Troubleshooting

- Re-run `python create_demo_users.py` to regenerate the database if credentials
  are changed during testing.
- Inspect `audit.log` for login or permission denials.
- `python list_users.py` prints the current user table for quick verification.
