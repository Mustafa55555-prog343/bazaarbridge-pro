"""
models/admin_model.py
================================================================================
Data-access functions for admin operations (user management, product
moderation, transactions/audit, payouts, disputes, announcements, coupons,
referrals, NoSQL activity log) and shared delivery-partner actions.
================================================================================
"""

import json
from database.db_manager import db


# ----------------------------------------------------------------- USER MGMT
def all_users(role=None, search=""):
    """Return users for the admin user-management table (filter by role/search)."""
    sql = """SELECT u.*, c.name AS city_name FROM users u
              LEFT JOIN cities c ON c.city_id=u.city_id WHERE 1=1"""
    params = []
    if role and role != "all":
        sql += " AND u.role=?"; params.append(role)
    if search.strip():
        sql += " AND (u.full_name LIKE ? OR u.email LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    sql += " ORDER BY u.created_at DESC"
    return db.query(sql, tuple(params))


def set_user_active(user_id, active):
    """Activate / deactivate a user account (admin control)."""
    db.execute("UPDATE users SET is_active=? WHERE user_id=?", (1 if active else 0, user_id))
    log_action(None, "TOGGLE_ACTIVE", "users", f"user {user_id} -> active={active}")


# ----------------------------------------------------------------- MODERATION
def products_for_moderation(status=None):
    """Return products with shop names for the moderation panel."""
    sql = """SELECT p.*, s.shop_name FROM products p JOIN shops s ON s.shop_id=p.shop_id"""
    params = []
    if status and status != "all":
        sql += " WHERE p.status=?"; params.append(status)
    sql += " ORDER BY p.created_at DESC"
    return db.query(sql, tuple(params))


def set_product_status(product_id, status):
    """Approve / reject / flag a product (admin moderation)."""
    db.execute("UPDATE products SET status=? WHERE product_id=?", (status, product_id))
    log_action(None, "MODERATE", "products", f"product {product_id} -> {status}")


# ----------------------------------------------------------------- TRANSACTIONS / AUDIT
def transactions(search=""):
    """Full transaction log (orders) for admin, searchable."""
    sql = """SELECT o.order_id, o.total, o.status, o.placed_at,
                    u.full_name AS buyer, s.shop_name AS shop
               FROM orders o JOIN users u ON u.user_id=o.buyer_id
               JOIN shops s ON s.shop_id=o.shop_id WHERE 1=1"""
    params = []
    if search.strip():
        sql += " AND (u.full_name LIKE ? OR s.shop_name LIKE ? OR o.status LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    sql += " ORDER BY o.placed_at DESC"
    return db.query(sql, tuple(params))


def audit_entries(limit=200):
    """Return recent audit-log rows with user names."""
    return db.query("""
        SELECT al.*, u.full_name FROM audit_log al
          LEFT JOIN users u ON u.user_id=al.user_id
         ORDER BY al.created_at DESC LIMIT ?""", (limit,))


def log_action(user_id, action, entity, details):
    """Insert an audit-log entry (used across the app for traceability)."""
    db.execute("INSERT INTO audit_log(user_id,action,entity,details) VALUES(?,?,?,?)",
               (user_id, action, entity, details))


# ----------------------------------------------------------------- PAYOUTS
def all_payouts(status=None):
    """Return payout requests with requester names."""
    sql = """SELECT p.*, u.full_name, u.role FROM payouts p
              JOIN users u ON u.user_id=p.user_id"""
    params = []
    if status and status != "all":
        sql += " WHERE p.status=?"; params.append(status)
    sql += " ORDER BY p.requested_at DESC"
    return db.query(sql, tuple(params))


def set_payout_status(payout_id, status):
    """Approve / reject a payout request (admin)."""
    db.execute("UPDATE payouts SET status=? WHERE payout_id=?", (status, payout_id))
    log_action(None, "PAYOUT", "payouts", f"payout {payout_id} -> {status}")


def request_payout(user_id, amount):
    """A seller or delivery partner requests a withdrawal."""
    db.execute("INSERT INTO payouts(user_id,amount) VALUES(?,?)", (user_id, amount))


# ----------------------------------------------------------------- DISPUTES
def all_disputes(status=None):
    """Return disputes with order + buyer info for the resolution centre."""
    sql = """SELECT d.*, o.total, u.full_name AS buyer FROM disputes d
              JOIN orders o ON o.order_id=d.order_id
              JOIN users u ON u.user_id=d.raised_by"""
    params = []
    if status and status != "all":
        sql += " WHERE d.status=?"; params.append(status)
    sql += " ORDER BY d.created_at DESC"
    return db.query(sql, tuple(params))


def set_dispute_status(dispute_id, status):
    """Resolve / reject a dispute (admin)."""
    db.execute("UPDATE disputes SET status=? WHERE dispute_id=?", (status, dispute_id))
    log_action(None, "DISPUTE", "disputes", f"dispute {dispute_id} -> {status}")


# ----------------------------------------------------------------- ANNOUNCEMENTS
def all_announcements():
    """Return platform announcements, newest first."""
    return db.query("SELECT * FROM announcements ORDER BY created_at DESC")


def add_announcement(title, body):
    """Create a platform-wide announcement (admin)."""
    db.execute("INSERT INTO announcements(title,body) VALUES(?,?)", (title, body))
    log_action(None, "ANNOUNCE", "announcements", title)


def delete_announcement(announcement_id):
    """Delete an announcement."""
    db.execute("DELETE FROM announcements WHERE announcement_id=?", (announcement_id,))


# ----------------------------------------------------------------- COUPONS
def all_coupons():
    """Return all coupons with optional shop names."""
    return db.query("""
        SELECT co.*, s.shop_name FROM coupons co
          LEFT JOIN shops s ON s.shop_id=co.shop_id ORDER BY co.coupon_id DESC""")


def add_coupon(code, discount_pct, min_amount, shop_id=None):
    """Create a coupon (admin platform-wide, or seller shop-scoped). (ok,msg)."""
    try:
        db.execute("INSERT INTO coupons(code,discount_pct,shop_id,min_amount) VALUES(?,?,?,?)",
                   (code.strip().upper(), discount_pct, shop_id, min_amount))
        return True, "Coupon created."
    except Exception:
        return False, "A coupon with that code already exists."


def toggle_coupon(coupon_id):
    """Enable/disable a coupon."""
    db.execute("UPDATE coupons SET is_active = 1 - is_active WHERE coupon_id=?", (coupon_id,))


# ----------------------------------------------------------------- REFERRALS
def all_referrals():
    """Return referral records with referrer/referred names."""
    return db.query("""
        SELECT r.*, ru.full_name AS referrer, rd.full_name AS referred
          FROM referrals r
          JOIN users ru ON ru.user_id=r.referrer_id
          JOIN users rd ON rd.user_id=r.referred_id
         ORDER BY r.created_at DESC""")


# ----------------------------------------------------------------- NoSQL (JSON)
def activity_documents(event_filter=None):
    """
    Return rows from the NoSQL activity_log. Demonstrates querying inside JSON
    documents with the JSON1 extension (json_extract).
    """
    if event_filter:
        return db.query("""
            SELECT activity_id, doc, created_at,
                   json_extract(doc,'$.event') AS event
              FROM activity_log
             WHERE json_extract(doc,'$.event')=?
             ORDER BY activity_id DESC""", (event_filter,))
    return db.query("""
        SELECT activity_id, doc, created_at,
               json_extract(doc,'$.event') AS event
          FROM activity_log ORDER BY activity_id DESC""")


def log_activity(doc_dict):
    """Insert a JSON document into the NoSQL activity log."""
    db.execute("INSERT INTO activity_log(doc) VALUES(?)", (json.dumps(doc_dict),))


def activity_event_types():
    """Distinct event types present in the JSON activity log (for a filter)."""
    return db.query("""
        SELECT DISTINCT json_extract(doc,'$.event') AS event
          FROM activity_log WHERE event IS NOT NULL ORDER BY event""")


# ----------------------------------------------------------------- DELIVERY ACTIONS
def claim_order(order_id, partner_id):
    """A delivery partner claims an available order (assigns it to themselves)."""
    db.execute("UPDATE orders SET partner_id=?, status='assigned' WHERE order_id=?",
               (partner_id, order_id))
    log_action(None, "CLAIM", "orders", f"order {order_id} -> partner {partner_id}")


def update_vehicle(partner_id, vehicle_type, vehicle_plate, zone_city_id):
    """Update a delivery partner's vehicle + zone info."""
    db.execute("""UPDATE delivery_partners
                     SET vehicle_type=?, vehicle_plate=?, zone_city_id=?
                   WHERE partner_id=?""",
               (vehicle_type, vehicle_plate, zone_city_id, partner_id))


# ----------------------------------------------------------------- PLATFORM HEALTH
def platform_health():
    """Return a comprehensive system-health snapshot for the admin.

    Combines several reporting views and live table counts into one dict so the
    Platform Health dashboard can render system statistics at a glance.
    """
    def scalar(sql, default=0):
        row = db.query_one(sql)
        if not row:
            return default
        return list(row.values() if hasattr(row, "values") else dict(row).values())[0]

    health = {
        "users":            scalar("SELECT COUNT(*) FROM users"),
        "active_users":     scalar("SELECT COUNT(*) FROM users WHERE is_active=1"),
        "sellers":          scalar("SELECT COUNT(*) FROM users WHERE role='seller'"),
        "buyers":           scalar("SELECT COUNT(*) FROM users WHERE role='buyer'"),
        "partners":         scalar("SELECT COUNT(*) FROM delivery_partners"),
        "shops":            scalar("SELECT COUNT(*) FROM shops"),
        "verified_shops":   scalar("SELECT COUNT(*) FROM shops WHERE is_verified=1"),
        "products":         scalar("SELECT COUNT(*) FROM products"),
        "approved_products": scalar("SELECT COUNT(*) FROM products WHERE status='approved'"),
        "pending_products": scalar("SELECT COUNT(*) FROM products WHERE status='pending'"),
        "flagged_products": scalar("SELECT COUNT(*) FROM products WHERE status='flagged'"),
        "active_flash":     scalar("SELECT COUNT(*) FROM products WHERE is_flash=1 AND status='approved'"),
        "low_stock":        scalar("SELECT COUNT(*) FROM v_low_stock"),
        "out_of_stock":     scalar("SELECT COUNT(*) FROM products WHERE stock=0"),
        "orders":           scalar("SELECT COUNT(*) FROM orders"),
        "delivered":        scalar("SELECT COUNT(*) FROM orders WHERE status='delivered'"),
        "in_progress":      scalar("SELECT COUNT(*) FROM orders WHERE status IN "
                                   "('accepted','assigned','picked_up','in_transit')"),
        "pending_orders":   scalar("SELECT COUNT(*) FROM orders WHERE status='pending'"),
        "revenue":          scalar("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='delivered'"),
        "open_disputes":    scalar("SELECT COUNT(*) FROM disputes WHERE status='open'"),
        "pending_payouts":  scalar("SELECT COUNT(*) FROM payouts WHERE status='pending'"),
        "reviews":          scalar("SELECT COUNT(*) FROM reviews"),
        "coupons_active":   scalar("SELECT COUNT(*) FROM coupons WHERE is_active=1"),
        "referrals":        scalar("SELECT COUNT(*) FROM referrals"),
        "activity_docs":    scalar("SELECT COUNT(*) FROM activity_log"),
        "notifications":    scalar("SELECT COUNT(*) FROM notifications"),
    }
    # Per-table row counts for the "database footprint" panel.
    tables = ["users", "shops", "products", "orders", "order_items", "reviews",
              "wishlist", "coupons", "referrals", "messages", "disputes",
              "payouts", "announcements", "notifications", "activity_log",
              "audit_log", "order_status_history", "addresses", "cities",
              "categories", "delivery_partners"]
    footprint = []
    for t in tables:
        footprint.append((t, scalar(f"SELECT COUNT(*) FROM {t}")))
    health["footprint"] = footprint
    # Object inventory (schema richness).
    health["trigger_count"] = scalar(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
    health["view_count"] = scalar(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
    health["index_count"] = scalar(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    health["table_count"] = scalar(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%'")
    return health


def low_stock_products(limit=50):
    """Return low-stock products from the v_low_stock reporting view."""
    return db.query(f"SELECT * FROM v_low_stock LIMIT {int(limit)}")


def all_partners():
    """Delivery-partner performance leaderboard (from v_partner_performance)."""
    return db.query("SELECT * FROM v_partner_performance ORDER BY deliveries DESC, earnings DESC")
