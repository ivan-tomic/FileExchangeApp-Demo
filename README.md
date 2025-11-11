# Business Reporter - File Exchange Portal (Demo)

This repository contains a fully sanitised demo of the Business Reporter File
Exchange Portal. It ships with placeholder branding, safe sample documents, and
scripted demo accounts so stakeholders can explore the workflow without
exposing production data or credentials.

## Features

- **Multi-Role Access Control**: 7 different user roles with granular permissions
- **Country-Specific Filtering**: Separate workflows for UK, DE, IT, FR, ES markets
- **File Management**: Upload, archive, approve, and restore files
- **Publication Status Tracking**: Track files through various stages
- **Email Notifications**: Automated notifications for file uploads and approvals
- **Audit Logging**: Complete audit trail for compliance
- **Invite System**: Secure invitation-based user registration
- **Modern UI**: Responsive design with dark/light theme support

## Demo Overview

- Sanitised sample files live in `files/` with metadata in `files/.index.json`. No
  production assets are included.
- `create_demo_users.py` seeds a clean `users.db` with demo accounts covering
  super, admin, user, and country roles.
- `.env.example` references placeholder SMTP and application values. Provide
  real credentials locally when required.
- Static assets reference neutral Business Reporter branding and demo-friendly
  dashboard links.

## Tech Stack

- **Backend**: Python 3.9+, Flask 3.0
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **Email**: SMTP integration
- **Deployment**: Gunicorn, Nginx, systemd
- **Security**: Password hashing, CSRF protection, session management

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- SQLite3 (usually pre-installed)
- SMTP credentials if you plan to test email notifications (optional)

### Installation

1. **Clone the repository** (when available):
   ```bash
   git clone https://github.com/yourusername/businessreporter-app.git
   cd businessreporter-app
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
# Copy the example file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env and fill in your values.
# At minimum set SECRET_KEY (generate a unique value) and optionally SMTP/DASHBOARD overrides.
   ```

5. **Generate a secure secret key**:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output to `SECRET_KEY` in your `.env` file.

6. **Ensure upload directories exist** (repo ships with placeholders, but you can recreate them at any time):
   ```bash
   mkdir -p files/_approved
   ```

7. **Run the application**:
   ```bash
   python app.py
   ```
   
   The app will be available at `http://localhost:5000`

### First-Time Setup

1. **Seed demo accounts** by running:
   ```bash
   python create_demo_users.py
   ```
   This generates `users.db` with super, admin, user, and country-scoped demo users.

2. **Login** with your admin credentials

3. **Configure email** by adding SMTP credentials to `.env` (optional)

## Configuration

All configuration is done through environment variables. See `.env.example` for a complete list of available settings.

### Important Settings

- `SECRET_KEY`: Cryptographically secure random key for session encryption (required)
- `INVITE_CODE`: Code required for user registration (required)
- `SMTP_USERNAME` / `SMTP_PASSWORD`: SMTP credentials for email notifications (optional)
- `SESSION_COOKIE_SECURE=1`: Enable for production with HTTPS
- `FLASK_ENV=production`: Production mode (disables debug features)

### Email Configuration

To test email notifications:
1. Update `.env` with your SMTP host, port, username, and password.
2. Optionally adjust `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` to match your sender.
3. Set `EMAIL_NOTIFICATIONS_ENABLED=1`.
4. Restart the Flask app after changing credentials.

## Sample Data Included

- `files/Demo_Brochure_FirstDraft.docx` – High urgency admin upload in the first-draft stage.
- `files/Demo_PressKit_Rewrite.docx` – Business Reporter team upload awaiting review.
- `files/Demo_Interview_Feedback.docx` – Country-scoped upload marked ready.
- `files/Demo_FinalAssets.zip` – Normal urgency asset bundle.
- `files/_approved/Demo_Approved_Pack.zip` – Archived example.

Metadata for these artifacts lives in `files/.index.json`. Update that file if you
add or rename demo assets so the UI reflects the correct status, notes, and
countries.

## User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `user` | Business Reporter team | Upload files, view all files |
| `admin` | Administrator | All user permissions + create users, manage roles |
| `super` | Super admin | All admin permissions + system configuration |
| `country_user_uk` | UK market specialist | View/download UK files only |
| `country_user_de` | DE market specialist | View/download DE files only |
| `country_user_it` | IT market specialist | View/download IT files only |
| `country_user_fr` | FR market specialist | View/download FR files only |
| `country_user_es` | ES market specialist | View/download ES files only |

## Database Schema

The application uses SQLite with the following main tables:
- `users`: User accounts, roles, email, password hashes
- `invites`: Invitation codes for registration
- `files`: File metadata and metadata

See `update_database_schema.py` for schema migrations.

## Deployment

### Production Deployment (Ubuntu Server)

See `DEPLOYMENT.md` for detailed deployment instructions with:
- Gunicorn + systemd setup
- Nginx reverse proxy configuration
- SSL/HTTPS with Let's Encrypt
- Backup strategies
- Security hardening

## Development

### Project Structure

```
FileExchangeApp/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── email_utils.py         # Email notification utilities
├── templates/             # HTML templates
├── static/                # CSS, JavaScript, images
├── files/                 # User-uploaded files (not in git)
├── users.db               # SQLite database (not in git)
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (not in git)
```

### Running Tests

```bash
# Run check scripts
python check_db_structure.py
python check_invites.py

# List users
python list_users.py
```

### Seeding Demo Users

```bash
# Reset the database and load demo accounts
python create_demo_users.py
```

Legacy helper scripts (`create_test_country_user.py`, `create_all_country_users.py`,
etc.) delegate to the same logic for backwards compatibility.

## Security Considerations

- ✅ Password hashing with Werkzeug
- ✅ SQL injection protection via parameterized queries
- ✅ CSRF protection on forms
- ✅ Secure session management
- ✅ Role-based access control
- ✅ Audit logging for compliance
- ⚠️ Use HTTPS in production (set `SESSION_COOKIE_SECURE=1`)
- ⚠️ Keep `SECRET_KEY` secret and unique per deployment
- ⚠️ Regularly backup `users.db` and `files/` directory

## Troubleshooting

### Import errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`

### Database errors
- Check `users.db` exists and is readable
- Run `python update_database_schema.py` to migrate schema

### Email not sending
- Verify SMTP credentials in `.env`
- Check `EMAIL_NOTIFICATIONS_ENABLED=1`
- Check firewall allows SMTP port 587
- For Gmail, ensure App Password is used (not regular password)

### Permission errors
- Ensure `files/` and `files/_approved/` directories exist
- Check write permissions on these directories

## Differences from Production

- Demo assets, metadata, and emails use neutral placeholders. Replace with real
  values before deploying to production.
- `create_demo_users.py` resets `users.db` with non-sensitive accounts—remove
  these and create real users before go-live.
- Default URLs (dashboard, SMTP host, sender address) point to example domains.
- Audit logs and invite codes are empty by default; configure them for your
  environment.

## Contributing

This is a production application. Please:
1. Test thoroughly in development
2. Follow existing code style
3. Update documentation for new features
4. Never commit sensitive data

## License

Proprietary - Business Reporter

## Contact

For issues or questions, contact the development team.

## Changelog

### Version 2.0 (Current)
- Multi-role system with 7 user types
- Country-specific filtering
- Publication status tracking
- Email notifications
- Invite system
- Archive/restore functionality
- Production deployment with Gunicorn + Nginx

### Version 1.0
- Initial release
- Basic file upload/download
- Simple authentication

