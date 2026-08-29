"""
models/user_model.py
================================================================================
Data-access functions for users, authentication, profiles, addresses and
notifications. These functions act as the application's "stored procedures":
each one is a clearly-named operation that wraps the SQL for a single business
task, so controllers never embed raw SQL.
================================================================================
"""

from database.db_manager import db
from utils.security import hash_password, verify_password


# ----------------------------------------------------------------- AUTH
def authenticate(email, password):
    """
    STORED-PROCEDURE STYLE: validate credentials.
    Returns the user row (as dict) on success, or None on failure / inactive.
    """
    row = db.query_one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    if row and row["is_active"] == 1 and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def register_user(full_name, email, password, role, city_id, phone=None):
    """
    Create a new user. Returns (user_id, None) on success or (None, error_msg).
    Demonstrates a transaction: for sellers/delivery we also create their
    extension row, all-or-nothing.
    """
    email = email.strip().lower()
    if db.query_one("SELECT 1 FROM users WHERE email = ?", (email,)):
        return None, "An account with this email already exists."

    try:
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO users(full_name,email,phone,password_hash,role,city_id)"
                " VALUES(?,?,?,?,?,?)",
                (full_name.strip(), email, phone, hash_password(password), role, city_id),
            )
            uid = cur.lastrowid
            if role == "seller":
                cur.execute(
                    "INSERT INTO shops(seller_id,shop_name,description,city_id)"
                    " VALUES(?,?,?,?)",
                    (uid, full_name.strip() + "'s Shop",
                     "Welcome to my shop!", city_id),
                )
            elif role == "delivery":
                cur.execute(
                    "INSERT INTO delivery_partners(user_id,zone_city_id) VALUES(?,?)",
                    (uid, city_id),
                )
        return uid, None
    except Exception as e:
        return None, f"Could not create account: {e}"


# ----------------------------------------------------------------- PROFILE
def get_user(user_id):
    """Return a single user as dict (with city name joined), or None."""
    row = db.query_one(
        "SELECT u.*, c.name AS city_name FROM users u "
        "LEFT JOIN cities c ON c.city_id = u.city_id WHERE u.user_id = ?",
        (user_id,))
    return dict(row) if row else None


def update_profile(user_id, full_name, phone, city_id):
    """Update editable profile fields for any user."""
    db.execute("UPDATE users SET full_name=?, phone=?, city_id=? WHERE user_id=?",
               (full_name.strip(), phone, city_id, user_id))


def change_password(user_id, new_password):
    """Set a new password hash for the user."""
    db.execute("UPDATE users SET password_hash=? WHERE user_id=?",
               (hash_password(new_password), user_id))


# ----------------------------------------------------------------- ADDRESSES
def get_addresses(user_id):
    """Return all saved addresses for a buyer (with city names)."""
    return db.query(
        "SELECT a.*, c.name AS city_name FROM addresses a "
        "JOIN cities c ON c.city_id=a.city_id WHERE a.user_id=? ORDER BY is_default DESC",
        (user_id,))


def add_address(user_id, label, line1, city_id, is_default=0):
    """Add a saved address; if default, clear other defaults first."""
    with db.transaction() as cur:
        if is_default:
            cur.execute("UPDATE addresses SET is_default=0 WHERE user_id=?", (user_id,))
        cur.execute(
            "INSERT INTO addresses(user_id,label,line1,city_id,is_default)"
            " VALUES(?,?,?,?,?)", (user_id, label, line1, city_id, is_default))


def delete_address(address_id):
    """Remove a saved address."""
    db.execute("DELETE FROM addresses WHERE address_id=?", (address_id,))


# ----------------------------------------------------------------- NOTIFICATIONS
def get_notifications(user_id, unread_only=False):
    """Return notifications for a user, newest first."""
    sql = "SELECT * FROM notifications WHERE user_id=?"
    if unread_only:
        sql += " AND is_read=0"
    sql += " ORDER BY created_at DESC"
    return db.query(sql, (user_id,))


def unread_count(user_id):
    """Return the number of unread notifications for the bell badge."""
    return db.query_one(
        "SELECT COUNT(*) n FROM notifications WHERE user_id=? AND is_read=0",
        (user_id,))["n"]


def mark_notifications_read(user_id):
    """Mark all of a user's notifications as read."""
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))


def add_notification(user_id, message):
    """Insert a notification for a user."""
    db.execute("INSERT INTO notifications(user_id,message) VALUES(?,?)",
               (user_id, message))


# ----------------------------------------------------------------- LOOKUPS
def get_cities():
    """Return all cities for dropdowns."""
    return db.query("SELECT * FROM cities ORDER BY name")


def get_categories():
    """Return all categories for dropdowns/filters."""
    return db.query("SELECT * FROM categories ORDER BY name")
