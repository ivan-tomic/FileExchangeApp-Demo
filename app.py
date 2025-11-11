#!/usr/bin/env python3
"""
Business Reporter - File Exchange Portal
A Flask application for secure file exchange with role-based access control.
"""

import json
import sqlite3
import shutil
import datetime as dt
from pathlib import Path
from functools import wraps
import re
import random
import string
import threading

from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, request, redirect, url_for, render_template, session,
    send_from_directory, flash, abort, send_file
)

# Import configuration
from config import (
    APP_NAME, FILES_DIR, AUDIT_LOG, INDEX_FILE, USER_DB_PATH, 
    SECRET_KEY, PORT, ALLOWED_EXT, MAX_CONTENT_LENGTH, 
    SESSION_COOKIE_SECURE, STAGE_CHOICES, STAGE_ALIASES, 
    DASHBOARD_URL, INV_CHARS, INVITE_CODE, UK_TIMEZONE
)
# Country and stage choices
COUNTRY_CHOICES = ["UK", "DE", "IT", "FR", "ES"]
STAGE_CHOICES = [
    "First draft",
    "Rewritten/Updated version",
    "Publisher asked for feedback",
    "Final draft",
]

# Country-specific user roles
COUNTRY_USER_ROLES = [
    "country_user_uk",
    "country_user_de",
    "country_user_it",
    "country_user_fr",
    "country_user_es"
]

# Map country_user roles to their countries
COUNTRY_USER_MAP = {
    "country_user_uk": "UK",
    "country_user_de": "DE",
    "country_user_it": "IT",
    "country_user_fr": "FR",
    "country_user_es": "ES"
}

# All valid roles
VALID_ROLES = ["user", "admin", "super"] + COUNTRY_USER_ROLES

def is_country_user(role):
    """Check if role is a country-specific user."""
    return role in COUNTRY_USER_ROLES

def get_user_country(role):
    """Get the country for a country_user role, or None for other roles."""
    return COUNTRY_USER_MAP.get(role)

# Country-specific user roles
COUNTRY_USER_ROLES = [
    "country_user_uk",
    "country_user_de",
    "country_user_it",
    "country_user_fr",
    "country_user_es"
]

# Map country_user roles to their countries
COUNTRY_USER_MAP = {
    "country_user_uk": "UK",
    "country_user_de": "DE",
    "country_user_it": "IT",
    "country_user_fr": "FR",
    "country_user_es": "ES"
}

# All valid roles
VALID_ROLES = ["user", "admin", "super"] + COUNTRY_USER_ROLES
STAGE_CHOICES = [
    "First draft",
    "Rewritten/Updated version",
    "Publisher asked for feedback",
    "Final draft",
]
# Import email utilities
from email_utils import notify_file_upload

# -------------------- Flask App Setup --------------------
app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
)

# -------------------- Helper Functions --------------------
def log_event(user: str, action: str, detail: str = "") -> None:
    """Log an event to the audit log."""
    ts = dt.datetime.now(UK_TIMEZONE).isoformat()
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{user}\t{action}\t{detail}\n")

def login_required(view):
    """Decorator to require login for a view."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("logged_in") is True:
            return view(*args, **kwargs)
        return redirect(url_for("login", next=request.path))
    return wrapper

def role_required(role):
    """Decorator to require a specific role for a view."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if session.get("logged_in"):
                r = session.get("role")
                if r == role or (role == "admin" and r == "super"):
                    return view(*args, **kwargs)
            abort(403)
        return wrapper
    return decorator
def is_country_user(role):
    """Check if role is a country-specific user."""
    return role in COUNTRY_USER_ROLES

def get_user_country(role):
    """Get the country for a country_user role, or None for other roles."""
    return COUNTRY_USER_MAP.get(role)

def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe and has allowed extension."""
    # Extract extension
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Check if extension is allowed
    if ext not in ALLOWED_EXT:
        return False
    
    # Check filename pattern (alphanumeric, spaces, dashes, underscores, dots)
    return bool(re.fullmatch(r"[\w,\-\.\ ]+\.(zip|docx|pdf)", filename, flags=re.IGNORECASE))

def normalize_stage(value):
    """Normalize stage values and handle legacy mappings."""
    if value is None:
        return STAGE_CHOICES[0]
    v = str(value).strip()
    if v == "":
        return ""
    v = STAGE_ALIASES.get(v, v)
    return v if v in STAGE_CHOICES else STAGE_CHOICES[0]

def load_index() -> dict:
    """Load the file index from JSON."""
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            for _, meta in list(data.items()):
                if isinstance(meta, dict):
                    meta["stage"] = normalize_stage(meta.get("stage"))
                    if "note" not in meta:
                        nb = meta.get("notes_by") or {}
                        for _u, n in nb.items():
                            if str(n).strip():
                                meta["note"] = str(n).strip()[:100]
                                break
                        else:
                            meta["note"] = ""
                    else:
                        meta["note"] = str(meta["note"]).strip()[:100]
                    meta.setdefault("note_by", "")
                    meta.setdefault("note_at", "")
            return data
        except Exception:
            return {}
    return {}

def save_index(data: dict) -> None:
    """Save the file index to JSON."""
    for _, meta in list(data.items()):
        if isinstance(meta, dict):
            meta["stage"] = normalize_stage(meta.get("stage"))
            meta["note"] = str(meta.get("note", "") or "").strip()[:100]
            meta["note_by"] = str(meta.get("note_by", "") or "").strip()
            meta["note_at"] = str(meta.get("note_at", "") or "").strip()
    INDEX_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def urgency_rank(urgency: str) -> int:
    """Return sort rank for urgency (High first)."""
    return 0 if urgency == "High" else 1

def visible_files_for(_user: str, _role: str):
    """Get all visible files for a user (zip, docx, pdf).

    Country users only see files from their assigned country.
    Other roles see all files.
    """
    files = []
    for p in FILES_DIR.iterdir():
        if not p.is_file():
            continue
        suffix = p.suffix.lower().lstrip(".")
        if suffix in ALLOWED_EXT:
            files.append(p)

    # If country user, filter by country
    if is_country_user(_role):
        user_country = get_user_country(_role)
        idx = load_index()
        filtered_files = []
        for f in files:
            meta = idx.get(f.name, {})
            file_country = meta.get("country", "UK")
            if file_country == user_country:
                filtered_files.append(f)
        return filtered_files
    
    return files

def sort_rows(rows):
    """Sort rows by urgency and modification time."""
    rows.sort(key=lambda r: (urgency_rank(r["urgency"]), -r["mtime"].timestamp()))
    return rows

def meta_get_uploader_role(meta: dict) -> str:
    """Get the role of the uploader from metadata."""
    role = meta.get("uploader_role")
    if role in {"user", "admin", "super"}:
        return role
    uploader = meta.get("uploader")
    if uploader:
        u = get_user(uploader)
        if u:
            return u["role"]
    return "admin"

# -------------------- Database Functions --------------------
def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db():
    """Ensure database tables exist."""
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          email TEXT,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('super','admin','user','country_user_uk','country_user_de','country_user_it','country_user_fr','country_user_es')) DEFAULT 'user',
          is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS invites (
          code TEXT PRIMARY KEY,
          country TEXT,
          is_used INTEGER NOT NULL DEFAULT 0,
          used_by TEXT,
          used_at TEXT,
          created_at TEXT NOT NULL
        )""")
        # Ensure country column exists on older databases
        try:
            db.execute("ALTER TABLE invites ADD COLUMN country TEXT")
        except Exception:
            pass

def get_user(username):
    """Get a user by username."""
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

def list_users():
    """List all users."""
    with get_db() as db:
        return db.execute("SELECT id, username, email, role, is_active, created_at FROM users ORDER BY created_at DESC").fetchall()

def create_user(username, password, role="user", email=None):
    """Create a new user."""
    ph = generate_password_hash(password)
    created = dt.datetime.now(UK_TIMEZONE).isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO users (username, email, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (username, email, ph, role, created)
        )

def set_role(username, role):
    """Set a user's role."""
    with get_db() as db:
        db.execute("UPDATE users SET role=? WHERE username=?", (role, username))

def set_active(username, active: int):
    """Set a user's active status."""
    with get_db() as db:
        db.execute("UPDATE users SET is_active=? WHERE username=?", (1 if active else 0, username))

def set_password(username, new_password):
    """Set a user's password."""
    ph = generate_password_hash(new_password)
    with get_db() as db:
        db.execute("UPDATE users SET password_hash=? WHERE username=?", (ph, username))

def delete_user(username):
    """Delete a user."""
    with get_db() as db:
        db.execute("DELETE FROM users WHERE username=?", (username,))

def count_supers():
    """Count active superusers."""
    with get_db() as db:
        r = db.execute("SELECT COUNT(*) AS n FROM users WHERE role='super' AND is_active=1").fetchone()
        return int(r["n"])

# -------------------- Invite Functions --------------------
def create_invite_codes(n=10, length=7, country="UK"):
    """Create invite codes for a specific country."""
    import secrets
    now = dt.datetime.now(UK_TIMEZONE).isoformat()
    codes = []
    with get_db() as db:
        for _ in range(n):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
            db.execute(
                "INSERT INTO invites (code, country, created_at) VALUES (?, ?, ?)",
                (code, country, now)
            )
            codes.append(code)
    return codes

def list_invites():
    """List all invites."""
    with get_db() as db:
        return db.execute("SELECT code, country, is_used, used_by, used_at, created_at FROM invites ORDER BY created_at DESC").fetchall()

def revoke_invite(code):
    """Revoke an unused invite."""
    with get_db() as db:
        db.execute("DELETE FROM invites WHERE code=? AND is_used=0", (code,))

def invites_available():
    """Check if any invites are available."""
    with get_db() as db:
        r = db.execute("SELECT COUNT(*) AS n FROM invites WHERE is_used=0").fetchone()
        return int(r["n"]) > 0

def invite_is_valid(code):
    """Return invite row-like object if valid and unused, else None.
    Supports a global INVITE_CODE bypass (no country).
    """
    if not code:
        return None
    if INVITE_CODE and code == INVITE_CODE:
        return {"code": INVITE_CODE, "country": None, "is_used": 0}
    with get_db() as db:
        return db.execute("SELECT * FROM invites WHERE code=? AND is_used=0", (code,)).fetchone()
def consume_invite(code, username):
    """Mark an invite code as used."""
    with get_db() as db:
        db.execute(
            "UPDATE invites SET is_used=1, used_by=?, used_at=? WHERE code=?",
            (username, dt.datetime.now(UK_TIMEZONE).isoformat(), code)
        )

# Initialize database
ensure_db()

# -------------------- Routes: Authentication --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        u = get_user(username)
        if u and u["is_active"] and check_password_hash(u["password_hash"], password):
            session["logged_in"] = True
            session["user"] = username
            session["role"] = u["role"]
            log_event(username, "login", u["role"])
            return redirect(request.args.get("next") or url_for("index"))
        flash("Invalid credentials.", "error")
    return render_template("login.html", app_name=APP_NAME)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user."""
    invite_required = bool(INVITE_CODE) or invites_available()
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        email = (request.form.get("email") or "").strip() or None
        invite = request.form.get("invite", "").strip()
        
        # Check password confirmation
        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
            return render_template("register.html", app_name=APP_NAME, invite_required=invite_required)
        
        # Validate basic requirements
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html", app_name=APP_NAME, invite_required=invite_required)
        
        if get_user(username):
            flash("Username already taken.", "error")
            return render_template("register.html", app_name=APP_NAME, invite_required=invite_required)
        
        # Validate invite code if required
        invite_data = None
        if invite_required:
            invite_data = invite_is_valid(invite)
            if not invite_data:
                flash("Invalid invite code.", "error")
                return render_template("register.html", app_name=APP_NAME, invite_required=invite_required)
        
        # Determine role based on invite code's country
        user_role = "user"  # Default role
        if invite_data and invite_data["country"]:
            country = invite_data["country"]
            country_role = f"country_user_{country.lower()}"
            # Validate the role exists
            if country_role in COUNTRY_USER_ROLES:
                user_role = country_role
        
        # Create user
        create_user(username, password, role=user_role, email=email)
        
        # Consume invite if required
        if invite_required:
            consume_invite(invite, username)
        
        # Log in the new user
        session["logged_in"] = True
        session["user"] = username
        session["role"] = user_role
        flash("Welcome! Account created.", "ok")
        log_event(username, "register", user_role)
        return redirect(url_for("index"))
    
    # GET request - show registration form
    return render_template("register.html", app_name=APP_NAME, invite_required=invite_required)

@app.route("/logout")
@login_required
def logout():
    """Logout."""
    u = session.get("user", "?")
    session.clear()
    log_event(u, "logout")
    return redirect(url_for("login"))

# -------------------- Routes: Main Application --------------------
@app.route("/")
@login_required
def index():
    """Main file listing page."""
    role = session.get("role", "user")
    # Get country filter from query string
    filter_country = request.args.get("country", "")
    user = session.get("user", "?")
    idx = load_index()

    # ONE-TIME MIGRATION: Set all existing files to UK if they don't have a country
    modified = False
    for fname in idx.keys():
        if "country" not in idx[fname] or not idx[fname]["country"]:
            idx[fname]["country"] = "UK"
            modified = True
    if modified:
        save_index(idx)

    rows = []
    for p in visible_files_for(user, role):
        stat = p.stat()
        meta = idx.get(p.name, {}) or {}
        urgency = meta.get("urgency", "Normal")
        stage = normalize_stage(meta.get("stage"))
        reviewed = bool((meta.get("reviewed_by") or {}).get(user))
        note = meta.get("note", "")
        note_by = meta.get("note_by", "")
        note_at = meta.get("note_at", "")
        uploader_role = meta_get_uploader_role(meta)

        rows.append({
            "name": p.name,
            "country": meta.get("country", "UK"),
            "size": stat.st_size,
            "mtime": dt.datetime.fromtimestamp(stat.st_mtime),
            "urgency": urgency,
            "stage": stage,
            "reviewed": reviewed,
            "note": note,
            "note_by": note_by,
            "note_at": note_at,
            "uploader": meta.get("uploader", "?"),  # ADD THIS LINE
            "uploader_role": uploader_role,
            "publication_status": meta.get("publication_status"),
        })

    # Apply country filter if provided (for non-country_user roles)
    if filter_country and not role.startswith("country_user_"):
        rows = [r for r in rows if r["country"] == filter_country]
    
    # Split into admin and user rows
    admin_rows = [r for r in rows if r["uploader_role"] in ("admin", "super")]
    user_rows = [r for r in rows if r["uploader_role"] not in ("admin", "super")]
    
    # Sort by urgency (High first, then Normal) and then by date (newest first)
    def sort_key(r):
        urgency_priority = 0 if r["urgency"] == "High" else 1
        return (urgency_priority, -r["mtime"].timestamp())
    
    admin_rows.sort(key=sort_key, reverse=False)
    user_rows.sort(key=sort_key, reverse=False)

    def can_delete(r):
        # Super and admin can delete anything
        if role in ("admin", "super"):
            return True
        # Users and country_users can delete their own files
        current_user = session.get("user")
        file_uploader = r.get("uploader")
        return current_user == file_uploader

    for r in admin_rows + user_rows:
        r["can_delete"] = can_delete(r)

    return render_template(
        "index.html",
        admin_rows=admin_rows,
        user_rows=user_rows,
        role=role,
        country_choices=COUNTRY_CHOICES,
        filter_country=filter_country,
        app_name=APP_NAME,
        dashboard_url=DASHBOARD_URL
    )

@app.route("/edit/<path:filename>", methods=["POST"])
@login_required
def edit_file(filename):
    """Edit file metadata (for admin/super)."""
    role = session.get("role", "user")
    
    if not is_safe_filename(filename):
        abort(400)
    
    # Load index
    idx = load_index()
    
    if filename not in idx:
        abort(404)
    
    file_info = idx[filename]
    file_country = file_info.get("country", "UK")
    
    # Authorization check
    # Only admin and super can edit any file
    if role in ["admin", "super"]:
        pass  # Authorized
    # Regular users can edit files, but let's check country match
    elif role == "user":
        pass  # Users can edit any file
    # Country users can only edit their country's files
    elif role.startswith("country_user_"):
        user_country = role.split("_")[-1].upper()
        if file_country != user_country:
            abort(403)  # Forbidden
    else:
        abort(403)
    
    # Get form data
    urgency = request.form.get("urgency", "Normal")
    stage = request.form.get("stage", "")
    note = request.form.get("note", "")
    country = request.form.get("country", "UK")
    
    # Update metadata
    idx[filename]["urgency"] = urgency
    idx[filename]["stage"] = stage
    idx[filename]["note"] = note
    idx[filename]["note_by"] = session.get("user", "?")
    idx[filename]["note_at"] = dt.datetime.now(UK_TIMEZONE).isoformat()
    idx[filename]["country"] = country
    
    save_index(idx)
    
    log_event(session.get("user", "?"), "edit", filename)
    flash(f"Updated {filename}", "ok")
    return redirect(url_for("index"))
    
    # Get form data
    urgency = request.form.get("urgency", "Normal")
    stage = request.form.get("stage", "")
    note = request.form.get("note", "")
    country = request.form.get("country", "UK")
    
    # Load index
    idx = load_index()
    
    if filename not in idx:
        abort(404)
    
    # Update metadata
    idx[filename]["urgency"] = urgency
    idx[filename]["stage"] = stage
    idx[filename]["note"] = note
    idx[filename]["note_by"] = session.get("user", "?")
    idx[filename]["note_at"] = dt.datetime.now(UK_TIMEZONE).isoformat()
    idx[filename]["country"] = country
    
    save_index(idx)
    
    log_event(session.get("user", "?"), "edit", filename)
    flash(f"Updated {filename}", "ok")
    return redirect(url_for("index"))

@app.route("/archive")
@login_required
def archive_view():
    """View archived files."""
    role = session.get("role", "user")
    if role not in ("admin", "super"):
        abort(403)
    
    # Get filter from query string
    filter_country = request.args.get("country", "")
    
    # Load archived files from _approved folder
    approved_dir = Path("files/_approved")
    if not approved_dir.exists():
        approved_dir.mkdir(parents=True)
    
    idx = load_index()
    rows = []
    
    for p in approved_dir.glob("*"):
        if p.is_file() and p.suffix.lower() in [f".{ext}" for ext in ALLOWED_EXT]:
            stat = p.stat()
            meta = idx.get(p.name, {}) or {}
            
            country = meta.get("country", "UK")
            
            # Apply country filter if specified
            if filter_country and country != filter_country:
                continue
            
            uploaded_at = meta.get("uploaded_at", "")
            archived_at = meta.get("archived_at", "")
            
            rows.append({
                "name": p.name,
                "country": country,
                "size": stat.st_size,
                "uploaded_at": uploaded_at,
                "archived_at": archived_at,
                "mtime": dt.datetime.fromtimestamp(stat.st_mtime),
            })
    
    # Sort by archived date (newest first)
    rows.sort(key=lambda x: x.get("archived_at") or x.get("uploaded_at") or "", reverse=True)
    
    return render_template(
        "archive.html",
        archived_files=rows,
        country_choices=COUNTRY_CHOICES,
        filter_country=filter_country,
        app_name=APP_NAME,
        role=role,
        dashboard_url=DASHBOARD_URL
    )

@app.route("/download_archived/<path:filename>")
@login_required
def download_archived(filename):
    """Download an archived file."""
    role = session.get("role", "user")
    if role not in ("admin", "super"):
        abort(403)
    if not is_safe_filename(filename):
        abort(400)
    
    approved_dir = FILES_DIR / "_approved"
    path = approved_dir / filename
    
    if not path.exists():
        abort(404)
    
    log_event(session.get("user", "?"), "download_archived", filename)
    return send_file(path, as_attachment=True)
    
    # Get filter from query string
    filter_country = request.args.get("country", "")
    
    # Load archived files from _approved folder
    approved_dir = Path("files/_approved")
    if not approved_dir.exists():
        approved_dir.mkdir(parents=True)
    
    idx = load_index()
    rows = []
    
    for p in approved_dir.glob("*"):
        if p.is_file() and p.suffix.lower() in [f".{ext}" for ext in ALLOWED_EXT]:
            stat = p.stat()
            meta = idx.get(p.name, {}) or {}
            
            country = meta.get("country", "UK")
            
            # Apply country filter if specified
            if filter_country and country != filter_country:
                continue
            
            uploaded_at = meta.get("uploaded_at", "")
            archived_at = meta.get("archived_at", "")
            
            rows.append({
                "name": p.name,
                "country": country,
                "size": stat.st_size,
                "uploaded_at": uploaded_at,
                "archived_at": archived_at,
                "mtime": dt.datetime.fromtimestamp(stat.st_mtime),
            })
    
    # Sort by archived date (newest first)
    rows.sort(key=lambda x: x.get("archived_at") or x.get("uploaded_at") or "", reverse=True)
    
    return render_template(
        "archive.html",
        archived_files=rows,
        country_choices=COUNTRY_CHOICES,
        filter_country=filter_country,
        app_name=APP_NAME,
        role=role,
        dashboard_url=DASHBOARD_URL
    )
@app.route("/restore/<path:filename>", methods=["POST"])
@login_required
def restore_file(filename):
    """Restore an archived file back to main files."""
    role = session.get("role", "user")
    if role not in ("admin", "super"):
        abort(403)
    if not is_safe_filename(filename):
        abort(400)
    
    src = FILES_DIR / "_approved" / filename
    if not src.exists():
        abort(404)
    
    dest = FILES_DIR / filename
    
    # Check if file already exists in main files
    if dest.exists():
        flash(f"Cannot restore: {filename} already exists in main files.", "error")
        return redirect(url_for("archive_view"))
    
    # Move file back
    src.rename(dest)
    
    # Update metadata - remove archived_at timestamp
    idx = load_index()
    if filename in idx:
        idx[filename].pop("archived_at", None)
        save_index(idx)
    
    log_event(session.get("user", "?"), "restore", filename)
    flash(f"Restored {filename} to main files", "ok")
    return redirect(url_for("archive_view"))

@app.route("/delete_archived/<path:filename>", methods=["POST"])
@login_required
def delete_archived(filename):
    """Permanently delete an archived file (super only)."""
    role = session.get("role", "user")
    if role != "super":
        abort(403)
    if not is_safe_filename(filename):
        abort(400)
    
    path = FILES_DIR / "_approved" / filename
    if not path.exists():
        abort(404)
    
    # Delete file
    path.unlink()
    
    # Remove from index
    idx = load_index()
    if filename in idx:
        del idx[filename]
        save_index(idx)
    
    log_event(session.get("user", "?"), "delete_archived", filename)
    flash(f"Permanently deleted {filename}", "ok")
    return redirect(url_for("archive_view"))

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    """Handle file upload."""
    f = request.files.get("file")
    if not f or f.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_EXT:
        flash("Only .zip, .docx, and .pdf files are allowed.", "error")
        return redirect(url_for("index"))

    safe_name = re.sub(r"[^\w\-. ]+", "_", f.filename)
    dest = FILES_DIR / safe_name

    role = session.get("role", "user")

    # Get country - auto-assign for country_users, otherwise from form
    if is_country_user(role):
        # Country users automatically upload to their assigned country
        country = get_user_country(role)
    else:
        # Regular users, admins, supers select country
        country = request.form.get("country", "UK").strip().upper()
        if country not in COUNTRY_CHOICES:
            flash("Please select a valid country.", "error")
            return redirect(url_for("index"))

    if role == "user":
        urgency = "Normal"
        stage = ""
    else:
        urgency = request.form.get("urgency", "Normal").strip().title()
        if urgency not in {"High", "Normal"}:
            urgency = "Normal"
        stage = normalize_stage(request.form.get("stage", STAGE_CHOICES[0]).strip())

    f.save(dest)

    idx = load_index()
      # Get publication status for user/country_user uploads
    publication_status = None
    if role == "user" or role.startswith("country_user_"):
        publication_status = request.form.get("publication_status", "needs_review").strip().lower()
        if publication_status not in {"ready", "needs_review"}:
            publication_status = "needs_review"
    idx[safe_name] = {
        "uploader": session.get("user", "?"),
        "uploader_role": role,
        "uploaded_at": dt.datetime.now(UK_TIMEZONE).isoformat(),
        "urgency": urgency,
        "country": country,
        "stage": stage,
        "reviewed_by": {},
        "note": "",
        "note_by": "",
        "note_at": "",
    }
    
    # Add publication_status if applicable
    if publication_status:
        idx[safe_name]["publication_status"] = publication_status
    save_index(idx)

    log_event(session.get("user", "?"), "upload", f"{safe_name} (urgency={urgency}, stage={stage or '[blank]'})")
    flash(f"Uploaded {safe_name}", "ok")
    
    # Send email notifications asynchronously (don't block upload)
    # Pass all needed data to avoid request context issues
    email_data = {
        'filename': safe_name,
        'uploader': session.get("user", "?"),
        'uploader_role': role,
        'urgency': urgency,
        'stage': stage,
        'is_user': role == "user"
    }
    
    def send_email_async(data):
        try:
            recipient_emails = []
            
            if data['is_user']:
                # User uploaded: notify all admin and super users
                import sqlite3
                conn = sqlite3.connect('users.db')
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                admins = cursor.execute(
                    "SELECT email FROM users WHERE (role='admin' OR role='super') AND is_active=1 AND email IS NOT NULL AND email != ''"
                ).fetchall()
                recipient_emails = [admin["email"] for admin in admins]
                conn.close()
            else:
                # Admin/super uploaded: notify all users with emails
                import sqlite3
                conn = sqlite3.connect('users.db')
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                users = cursor.execute(
                    "SELECT email FROM users WHERE role='user' AND is_active=1 AND email IS NOT NULL AND email != ''"
                ).fetchall()
                recipient_emails = [user["email"] for user in users]
                conn.close()
            
            if recipient_emails:
                notify_file_upload(
                    filename=data['filename'],
                    uploader=data['uploader'],
                    uploader_role=data['uploader_role'],
                    recipient_emails=recipient_emails,
                    urgency=data['urgency'],
                    stage=data['stage']
                )
                print(f"✅ Email sent to {len(recipient_emails)} recipient(s)")
        except Exception as e:
            # Log error but don't fail the upload
            print(f"⚠️ Email notification failed: {e}")
    
    # Start email sending in background thread
    email_thread = threading.Thread(target=send_email_async, args=(email_data,))
    email_thread.daemon = True
    email_thread.start()
    return redirect(url_for("index"))

@app.route("/set_urgency/<path:filename>", methods=["POST"])
@login_required
@role_required("admin")
def set_urgency(filename):
    """Set file urgency."""
    if not is_safe_filename(filename):
        abort(400)
    path = FILES_DIR / filename
    if not path.exists():
        abort(404)

    idx = load_index()
    meta = idx.get(filename) or {}
    if meta_get_uploader_role(meta) == "user":
        flash("Cannot change urgency for files uploaded by Business Reporter users.", "error")
        return redirect(url_for("index"))

    new_urg = request.form.get("urgency", "Normal").strip().title()
    if new_urg not in {"High", "Normal"}:
        new_urg = "Normal"

    meta["urgency"] = new_urg
    idx[filename] = meta
    save_index(idx)

    log_event(session.get("user", "?"), "set_urgency", f"{filename} -> {new_urg}")
    flash(f"Updated urgency for {filename} to {new_urg}", "ok")
    return redirect(url_for("index"))

@app.route("/set_stage/<path:filename>", methods=["POST"])
@login_required
@role_required("admin")
def set_stage(filename):
    """Set file stage."""
    if not is_safe_filename(filename):
        abort(400)
    path = FILES_DIR / filename
    if not path.exists():
        abort(404)

    idx = load_index()
    meta = idx.get(filename) or {}
    if meta_get_uploader_role(meta) == "user":
        flash("Cannot change stage for files uploaded by Business Reporter users.", "error")
        return redirect(url_for("index"))

    new_stage = normalize_stage(request.form.get("stage", STAGE_CHOICES[0]).strip())
    meta["stage"] = new_stage
    idx[filename] = meta
    save_index(idx)

    log_event(session.get("user", "?"), "set_stage", f"{filename} -> {new_stage or '[blank]'}")
    flash(f'Updated stage for {filename} to "{new_stage or "—"}".', "ok")
    return redirect(url_for("index"))

@app.route("/toggle_reviewed/<path:filename>", methods=["POST"])
@login_required
def toggle_reviewed(filename):
    """Toggle reviewed status."""
    if session.get("role") != "user":
        abort(403)

    if not is_safe_filename(filename):
        abort(400)
    path = FILES_DIR / filename
    if not path.exists():
        abort(404)

    idx = load_index()
    meta = idx.get(filename) or {}
    if meta_get_uploader_role(meta) == "user":
        flash("Reviewed is not required for files uploaded by Business Reporter users.", "error")
        return redirect(url_for("index"))

    checked = "1" in request.form.getlist("checked")

    rb = meta.get("reviewed_by") or {}
    rb[session.get("user", "?")] = bool(checked)
    meta["reviewed_by"] = rb
    idx[filename] = meta
    save_index(idx)

    return redirect(url_for("index"))

@app.route("/update_file/<path:filename>", methods=["POST"])
@login_required
@role_required("admin")
def update_file(filename):
    """Update urgency, stage, and note for a file in one request."""
    if not is_safe_filename(filename):
        abort(400)
    path = FILES_DIR / filename
    if not path.exists():
        abort(404)

    idx = load_index()
    meta = idx.get(filename) or {}
    
    # Check if file was uploaded by user
    if meta_get_uploader_role(meta) == "user":
        flash("Cannot modify files uploaded by Business Reporter users.", "error")
        return redirect(url_for("index"))
    
    # Get country (default to UK if not provided)
        country = request.form.get("country", "UK").strip().upper()
        if country not in COUNTRY_CHOICES:
            flash("Please select a valid country.", "error")
            return redirect(url_for("index"))

    # Update urgency
    new_urgency = request.form.get("urgency", "Normal").strip().title()
    if new_urgency in {"High", "Normal"}:
        meta["urgency"] = new_urgency

    # Update stage
    new_stage = normalize_stage(request.form.get("stage", "").strip())
    meta["stage"] = new_stage

    # Update country
    new_country = request.form.get("country", "UK").strip().upper()
    if new_country in COUNTRY_CHOICES:
        meta["country"] = new_country

    # Update note
    note = (request.form.get("note") or "").strip()
    if len(note) > 100:
        note = note[:100]
    meta["note"] = note
    meta["note_by"] = session.get("user", "?")
    meta["note_at"] = dt.datetime.now(UK_TIMEZONE).isoformat()

    idx[filename] = meta
    save_index(idx)

    log_event(session.get("user", "?"), "update_file", f"{filename} (urgency={new_urgency}, stage={new_stage})")
    flash(f"Updated {filename} successfully", "ok")
    return redirect(url_for("index"))

@app.route("/set_note/<path:filename>", methods=["POST"])
@login_required
def set_note(filename):
    """Set a note on a file (for user role)."""
    role = session.get("role", "user")
    
    if not is_safe_filename(filename):
        abort(400)
    
    # Load index
    idx = load_index()
    
    if filename not in idx:
        abort(404)
    
    file_info = idx[filename]
    file_country = file_info.get("country", "UK")
    
    # Authorization check
    # Admin and super can edit any file
    if role in ["admin", "super"]:
        pass  # Authorized
    # Regular users can edit any file's notes
    elif role == "user":
        pass  # Authorized
    # Country users can only edit their country's files
    elif role.startswith("country_user_"):
        user_country = role.split("_")[-1].upper()
        if file_country != user_country:
            abort(403)  # Forbidden
    else:
        abort(403)
    
    note = request.form.get("note", "")
    country = request.form.get("country", file_country)
    
    # Update note
    idx[filename]["note"] = note
    idx[filename]["note_by"] = session.get("user", "?")
    idx[filename]["note_at"] = dt.datetime.now(UK_TIMEZONE).isoformat()
    idx[filename]["country"] = country
    
    save_index(idx)
    
    log_event(session.get("user", "?"), "set_note", filename)
    flash(f"Updated note for {filename}", "ok")
    return redirect(url_for("index"))

@app.route("/download/<path:filename>")
@login_required
def download(filename):
    """Download a file with proper authorization checks."""
    if not is_safe_filename(filename):
        abort(400)
    
    role = session.get("role", "user")
    
    # Load file metadata to check country
    idx = load_index()
    if filename not in idx:
        abort(404)
    
    file_info = idx[filename]
    file_country = file_info.get("country", "UK")
    
    # Authorization check
    # Super, admin, and regular user can download anything
    if role in ["super", "admin", "user"]:
        pass  # Authorized
    # Country users can only download from their assigned country
    elif role.startswith("country_user_"):
        user_country = role.split("_")[-1].upper()  # Extract "UK" from "country_user_uk"
        if file_country != user_country:
            abort(403)  # Forbidden - wrong country
    else:
        abort(403)  # Unknown role
    
    # If we get here, user is authorized
    fpath = FILES_DIR / filename
    if not fpath.exists():
        abort(404)
    
    log_event(session.get("user", "?"), "download", filename)
    return send_file(fpath, as_attachment=True)

@app.route("/approve/<path:filename>", methods=["POST"])
@login_required
def approve(filename):
    """Archive a file."""
    role = session.get("role", "user")
    if role not in ("admin", "super"):
        abort(403)
    if not is_safe_filename(filename):
        abort(400)
    
    src = FILES_DIR / filename
    if not src.exists():
        abort(404)
    
    approved_dir = FILES_DIR / "_approved"
    approved_dir.mkdir(exist_ok=True)
    dest = approved_dir / filename
    
    # Move file
    src.rename(dest)
    
    # Update metadata with archive timestamp
    idx = load_index()
    if filename in idx:
        idx[filename]["archived_at"] = dt.datetime.now(UK_TIMEZONE).isoformat()
        save_index(idx)
    
    log_event(session.get("user", "?"), "archive", filename)
    flash(f"Archived {filename}", "ok")
    return redirect(url_for("index"))

    approved_dir = FILES_DIR / "_approved"
    approved_dir.mkdir(parents=True, exist_ok=True)

    target = approved_dir / filename
    if target.exists():
        ts = dt.datetime.now(UK_TIMEZONE).strftime("%Y%m%d%H%M%S")
        stem, suffix = Path(filename).stem, Path(filename).suffix
        target = approved_dir / f"{stem}__approved_{ts}{suffix}"

    shutil.move(str(src), str(target))

    idx = load_index()
    idx.pop(filename, None)
    save_index(idx)

    log_event(session.get("user", "?"), "approve_archive", f"{filename} -> {target.name}")
    flash(f"Archived {filename} to _approved/", "ok")
    return redirect(url_for("index"))

@app.route("/delete/<path:filename>", methods=["POST"])
@login_required
def delete_file(filename):
    """Delete a file."""
    role = session.get("role", "user")
    username = session.get("user", "?")
    
    if not is_safe_filename(filename):
        abort(400)
    
    # Load index
    idx = load_index()
    
    if filename not in idx:
        abort(404)
    
    file_info = idx[filename]
    file_country = file_info.get("country", "UK")
    file_uploader = file_info.get("uploader", "")
    
    # Authorization check
    # Admin and super can delete anything
    if role in ["admin", "super"]:
        pass  # Authorized
    # Regular users can delete their own files
    elif role == "user":
        if file_uploader != username:
            abort(403)  # Can only delete own files
    # Country users can delete their own files from their country
    elif role.startswith("country_user_"):
        user_country = role.split("_")[-1].upper()
        if file_country != user_country or file_uploader != username:
            abort(403)  # Must be same country AND own file
    else:
        abort(403)
    
    # Delete file
    fpath = FILES_DIR / filename
    if fpath.exists():
        fpath.unlink()
    
    # Remove from index
    del idx[filename]
    save_index(idx)
    
    log_event(username, "delete", filename)
    flash(f"Deleted {filename}", "ok")
    return redirect(url_for("index"))

# -------------------- Routes: Admin (User Management) --------------------
@app.route("/admin/users", methods=["GET"])
@login_required
def admin_users():
    """User management page."""
    if session.get("role") != "super":
        abort(403)
    rows = list_users()
    invites = list_invites()
    return render_template(
        "admin_users.html", 
        users=rows, 
        invites=invites, 
        app_name=APP_NAME, 
        dashboard_url=DASHBOARD_URL
    )

@app.route("/admin/users/action", methods=["POST"])
@login_required
def admin_users_action():
    """Handle user management actions."""
    if session.get("role") != "super":
        abort(403)
    action = request.form.get("action")
    username = request.form.get("username")

    try:
        if action in {"promote", "demote", "make_super", "deactivate", "activate", "reset_password", "delete_user"}:
            if not username or not get_user(username):
                flash("Unknown user.", "error")
                return redirect(url_for("admin_users"))

        if action == "promote":
            set_role(username, "admin")
            flash(f"Promoted {username} to admin", "ok")
        elif action == "demote":
            if username == session.get("user"):
                flash("Refusing to demote the current superuser.", "error")
            else:
                set_role(username, "user")
                flash(f"Demoted {username} to user", "ok")
        elif action == "make_super":
            set_role(username, "super")
            flash(f"Granted super role to {username}", "ok")
        elif action == "deactivate":
            if username == session.get("user"):
                flash("Refusing to deactivate the current superuser.", "error")
            else:
                set_active(username, 0)
                flash(f"Deactivated {username}", "ok")
        elif action == "activate":
            set_active(username, 1)
            flash(f"Activated {username}", "ok")
        elif action == "reset_password":
            newpw = request.form.get("new_password", "")
            if len(newpw) < 6:
                flash("New password must be at least 6 characters.", "error")
            else:
                set_password(username, newpw)
                flash(f"Password reset for {username}", "ok")
        elif action == "delete_user":
            if username == session.get("user"):
                flash("Refusing to delete the current superuser.", "error")
            else:
                u = get_user(username)
                if u and u["role"] == "super" and count_supers() <= 1:
                    flash("Cannot delete the last active superuser.", "error")
                else:
                    delete_user(username)
                    flash(f"Deleted user {username}", "ok")
        elif action == "gen_invites":
            n = int(request.form.get("count", "10") or "10")
            length = int(request.form.get("length", "7") or "7")
            n = max(1, min(n, 50))
            length = max(5, min(length, 10))
            
            # Get country from form
            country = request.form.get("country", "").strip().upper()
            if country not in COUNTRY_CHOICES:
                flash("Please select a valid country.", "error")
                return redirect(url_for("admin_users"))
            
            codes = create_invite_codes(n=n, length=length, country=country)
            flash("Generated: " + ", ".join(codes), "ok")
        elif action == "revoke_invite":
            code = request.form.get("code", "")
            revoke_invite(code)
            flash(f"Revoked {code}", "ok")
        else:
            flash("Unknown action.", "error")
    except sqlite3.IntegrityError:
        flash("Operation failed due to a constraint.", "error")

    return redirect(url_for("admin_users"))

# -------------------- Run Application --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)