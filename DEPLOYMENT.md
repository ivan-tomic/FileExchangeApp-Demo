# Deployment Guide - Business Reporter File Exchange Portal

This guide covers deploying the application to production on Ubuntu Server 22.04 LTS with Gunicorn, Nginx, and systemd.

## Prerequisites

- Ubuntu Server 22.04 LTS or similar
- Root or sudo access
- Domain name pointed to your server IP
- Python 3.9+ installed

## Production Deployment Steps

### 1. Initial Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv nginx git sqlite3 ufw

# Configure firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 2. Create Application User

```bash
# Create non-root user for the application
sudo adduser deploy
sudo usermod -aG sudo deploy

# Switch to deploy user
su - deploy
```

### 3. Set Up Application Directory

```bash
# Create application directory structure
sudo mkdir -p /opt/businessreporter/{app,venv,run,logs,files,files/_approved}
sudo chown -R deploy:deploy /opt/businessreporter

# Navigate to app directory
cd /opt/businessreporter
```

### 4. Clone and Install Application

```bash
# Clone repository (adjust URL to your repo)
git clone <your-repo-url> app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip wheel
pip install -r app/requirements.txt

# Install Gunicorn
pip install gunicorn
```

### 5. Configure Environment Variables

```bash
# Create production .env file
cd /opt/businessreporter/app
nano .env
```

**Important Environment Variables:**

```env
# Application
APP_NAME=Business Reporter - File Exchange Portal
FLASK_ENV=production

# Paths
FILES_DIR=/opt/businessreporter/files
USER_DB_PATH=/opt/businessreporter/app/users.db
AUDIT_LOG=/opt/businessreporter/logs/audit.log

# Security - GENERATE NEW VALUES!
SECRET_KEY=your_super_secret_key_here_64_chars_minimum
INVITE_CODE=your_invite_code_here
SESSION_COOKIE_SECURE=1

# Email SMTP
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_EMAIL=noreply@example.com
SMTP_FROM_NAME=Business Reporter File Exchange Demo
EMAIL_NOTIFICATIONS_ENABLED=1

# File Upload
MAX_CONTENT_LENGTH=524288000
```

**Generate secure keys:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Initialize Database

```bash
cd /opt/businessreporter/app
python3 app.py  # This will create the database

# Seed demo users (safe defaults for testing)
python3 create_demo_users.py --keep-existing
```

### 7. Configure Gunicorn

Create `/opt/businessreporter/gunicorn_config.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "/opt/businessreporter/logs/gunicorn_access.log"
errorlog = "/opt/businessreporter/logs/gunicorn_error.log"
loglevel = "info"
capture_output = True
```

### 8. Create systemd Service

Create `/etc/systemd/system/businessreporter.service`:

```ini
[Unit]
Description=Business Reporter File Exchange Portal
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/opt/businessreporter/app
Environment="PATH=/opt/businessreporter/venv/bin"
ExecStart=/opt/businessreporter/venv/bin/gunicorn --config /opt/businessreporter/gunicorn_config.py app:app
Restart=always
RestartSec=3
StandardOutput=append:/opt/businessreporter/logs/gunicorn.out.log
StandardError=append:/opt/businessreporter/logs/gunicorn.err.log

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable businessreporter
sudo systemctl start businessreporter
sudo systemctl status businessreporter
```

### 9. Configure Nginx

Create `/etc/nginx/sites-available/businessreporter`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name files-demo.example.com www.files-demo.example.com;
    
    # Redirect to HTTPS (will be enabled after SSL setup)
    # return 301 https://$server_name$request_uri;

    client_max_body_size 500M;
    server_tokens off;

    location /static/ {
        alias /opt/businessreporter/app/static/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 75;
        
        # Security headers
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self'" always;
    }
}
```

Enable site and test configuration:

```bash
sudo ln -s /etc/nginx/sites-available/businessreporter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 10. Set Up SSL/HTTPS

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d files-demo.example.com -d www.files-demo.example.com \
    --redirect --no-eff-email -m your_email@example.com --agree-tos

# Test auto-renewal
sudo certbot renew --dry-run
```

**After SSL is installed, uncomment the redirect line in Nginx config:**

```bash
sudo nano /etc/nginx/sites-available/businessreporter
# Uncomment: return 301 https://$server_name$request_uri;
sudo systemctl reload nginx
```

### 11. Set Up Log Rotation

Create `/etc/logrotate.d/businessreporter`:

```
/opt/businessreporter/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 deploy www-data
    sharedscripts
    postrotate
        systemctl reload businessreporter > /dev/null 2>&1 || true
    endscript
}
```

### 12. Configure Backups

Create backup script `/opt/businessreporter/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/businessreporter/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
cp /opt/businessreporter/app/users.db $BACKUP_DIR/users.db.$TIMESTAMP

# Backup files
tar -czf $BACKUP_DIR/files.$TIMESTAMP.tar.gz /opt/businessreporter/files

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

Make executable and schedule:

```bash
chmod +x /opt/businessreporter/backup.sh
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/businessreporter/backup.sh >> /opt/businessreporter/logs/backup.log 2>&1
```

## Deployment Workflow

### Updating the Application

```bash
# On server
cd /opt/businessreporter/app
git pull origin main
source /opt/businessreporter/venv/bin/activate
pip install -r requirements.txt

# Run any migrations
python3 update_database_schema.py

# Restart service
sudo systemctl restart businessreporter
```

### Checking Service Status

```bash
# Check service status
sudo systemctl status businessreporter

# Check logs
sudo journalctl -u businessreporter -f
tail -f /opt/businessreporter/logs/gunicorn_error.log

# Check Nginx
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

## Security Checklist

- ✅ Firewall (UFW) configured
- ✅ SSL/HTTPS enabled
- ✅ Non-root application user
- ✅ Secure SECRET_KEY generated
- ✅ SESSION_COOKIE_SECURE=1 set
- ✅ Security headers configured
- ✅ File permissions set correctly
- ✅ Regular backups scheduled
- ✅ Log rotation configured
- ✅ System updates automated
- ✅ Fail2ban installed (recommended)

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u businessreporter -n 100

# Check permissions
ls -la /opt/businessreporter/app
```

### 502 Bad Gateway
```bash
# Verify Gunicorn is running
curl http://127.0.0.1:8000

# Check Gunicorn config
cat /opt/businessreporter/gunicorn_config.py
```

### Database errors
```bash
# Check database permissions
ls -la /opt/businessreporter/app/users.db

# Verify schema
sqlite3 /opt/businessreporter/app/users.db ".schema"
```

### Email not sending
```bash
# Check SMTP credentials
cat /opt/businessreporter/app/.env | grep SMTP

# Test SMTP connection
python3 -c "import smtplib; s = smtplib.SMTP('smtp.example.com', 587); s.starttls(); print('Connected')"
```

## Performance Tuning

### Gunicorn Workers
Adjust `workers` in gunicorn_config.py based on CPU:
- 1-2 CPU cores: 3-5 workers
- 4 CPU cores: 8-10 workers
- 8+ CPU cores: 16+ workers

### Database Optimization
```bash
# Add to .env
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-32000;
```

## Monitoring

### Basic Monitoring Script

Create `/opt/businessreporter/healthcheck.sh`:

```bash
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login)
if [ $response -eq 200 ]; then
    echo "OK"
else
    echo "FAIL: HTTP $response"
    sudo systemctl restart businessreporter
fi
```

## Disaster Recovery

### Restore from Backup

```bash
# Stop service
sudo systemctl stop businessreporter

# Restore database
cp /opt/businessreporter/backups/users.db.YYYYMMDD_HHMMSS /opt/businessreporter/app/users.db

# Restore files
tar -xzf /opt/businessreporter/backups/files.YYYYMMDD_HHMMSS.tar.gz -C /

# Start service
sudo systemctl start businessreporter
```

## Additional Resources

- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Ubuntu Server Security](https://ubuntu.com/server/docs/security)

