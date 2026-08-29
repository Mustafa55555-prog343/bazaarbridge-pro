"""
models/analytics_model.py
================================================================================
Reporting / analytics queries that power the matplotlib charts and stat cards
across the Seller, Delivery and Admin dashboards. Almost everything here reads
from the VIEWS defined in schema.sql, demonstrating that complex reporting is
expressed declaratively in the database.
================================================================================
"""

from database.db_manager import db


# ----------------------------------------------------------------- PLATFORM (admin)
def platform_totals():
    """Headline KPIs for the admin dashboard stat cards."""
    return {
        "users":    db.query_one("SELECT COUNT(*) n FROM users")["n"],
        "sellers":  db.query_one("SELECT COUNT(*) n FROM users WHERE role='seller'")["n"],
        "buyers":   db.query_one("SELECT COUNT(*) n FROM users WHERE role='buyer'")["n"],
        "products": db.query_one("SELECT COUNT(*) n FROM products")["n"],
        "orders":   db.query_one("SELECT COUNT(*) n FROM orders")["n"],
        "revenue":  db.query_one("SELECT COALESCE(SUM(total),0) s FROM orders WHERE status='delivered'")["s"],
        "pending_products": db.query_one("SELECT COUNT(*) n FROM products WHERE status='pending'")["n"],
        "open_disputes":    db.query_one("SELECT COUNT(*) n FROM disputes WHERE status='open'")["n"],
    }


def daily_revenue():
    """Revenue per day (reads v_daily_revenue view)."""
    return db.query("SELECT * FROM v_daily_revenue")


def category_revenue():
    """Revenue per category (reads v_category_revenue view)."""
    return db.query("SELECT * FROM v_category_revenue ORDER BY revenue DESC")


def city_orders():
    """City-wise order distribution (reads v_city_orders view)."""
    return db.query("SELECT * FROM v_city_orders")


def top_sellers(limit=5):
    """Top performing shops by revenue (reads v_shop_performance view)."""
    return db.query("SELECT * FROM v_shop_performance ORDER BY revenue DESC LIMIT ?", (limit,))


def top_buyers(limit=5):
    """Top buyers by spend (reads v_top_buyers view)."""
    return db.query("SELECT * FROM v_top_buyers LIMIT ?", (limit,))


def platform_growth():
    """Cumulative user sign-ups over time (platform growth chart)."""
    return db.query("""
        SELECT date(created_at) AS day, COUNT(*) AS new_users
          FROM users GROUP BY date(created_at) ORDER BY day""")


def revenue_forecast():
    """
    Naive revenue forecast: average of the last 7 active days projected forward
    3 days. Returns (history_rows, forecast_list). Demonstrates a simple
    analytics computation on top of a view.
    """
    rows = daily_revenue()
    if not rows:
        return [], []
    recent = [r["revenue"] for r in rows[-7:]]
    avg = sum(recent) / len(recent)
    forecast = [round(avg)] * 3
    return rows, forecast


# ----------------------------------------------------------------- SELLER
def seller_totals(shop_id):
    """KPIs for a seller's dashboard stat cards."""
    rev = db.query_one(
        "SELECT COALESCE(SUM(total),0) s FROM orders WHERE shop_id=? AND status='delivered'",
        (shop_id,))["s"]
    month_rev = db.query_one("""
        SELECT COALESCE(SUM(total),0) s FROM orders
         WHERE shop_id=? AND status='delivered'
           AND placed_at >= date('now','-30 days')""", (shop_id,))["s"]
    return {
        "revenue": rev,
        "month_revenue": month_rev,
        "orders": db.query_one("SELECT COUNT(*) n FROM orders WHERE shop_id=?", (shop_id,))["n"],
        "products": db.query_one("SELECT COUNT(*) n FROM products WHERE shop_id=?", (shop_id,))["n"],
        "pending": db.query_one(
            "SELECT COUNT(*) n FROM orders WHERE shop_id=? AND status='pending'", (shop_id,))["n"],
        "balance": (db.query_one("SELECT balance FROM shops WHERE shop_id=?",
                                  (shop_id,)) or {"balance": 0})["balance"],
    }


def seller_revenue_over_time(shop_id):
    """Daily revenue series for one shop (embedded seller chart)."""
    return db.query("""
        SELECT date(placed_at) AS day, SUM(total) AS revenue
          FROM orders WHERE shop_id=? AND status='delivered'
         GROUP BY date(placed_at) ORDER BY day""", (shop_id,))


def seller_best_products(shop_id, limit=5):
    """Best-selling products for a shop (reads v_product_sales view)."""
    return db.query("""
        SELECT name, units_sold, revenue FROM v_product_sales
         WHERE shop_id=? ORDER BY units_sold DESC, revenue DESC LIMIT ?""",
        (shop_id, limit))


def seller_category_breakdown(shop_id):
    """Units sold per category for one shop (seller analytics pie)."""
    return db.query("""
        SELECT c.name AS category, COALESCE(SUM(oi.quantity),0) AS units
          FROM categories c
          JOIN products p ON p.category_id=c.category_id AND p.shop_id=?
          LEFT JOIN order_items oi ON oi.product_id=p.product_id
          LEFT JOIN orders o ON o.order_id=oi.order_id AND o.status='delivered'
         GROUP BY c.category_id HAVING units > 0 ORDER BY units DESC""", (shop_id,))


# ----------------------------------------------------------------- DELIVERY
def partner_for_user(user_id):
    """Return the delivery_partner row for a delivery user."""
    row = db.query_one("""
        SELECT dp.*, c.name AS zone FROM delivery_partners dp
          JOIN cities c ON c.city_id=dp.zone_city_id WHERE dp.user_id=?""", (user_id,))
    return dict(row) if row else None


def available_orders(zone_city_id):
    """
    Orders that are accepted by a seller but not yet assigned to a partner,
    within the partner's zone (the buyer's city matches the zone).
    """
    return db.query("""
        SELECT o.*, s.shop_name, u.full_name AS buyer_name, ci.name AS buyer_city,
               a.line1 AS address_line
          FROM orders o
          JOIN shops s ON s.shop_id=o.shop_id
          JOIN users u ON u.user_id=o.buyer_id
          JOIN cities ci ON ci.city_id=u.city_id
          LEFT JOIN addresses a ON a.address_id=o.address_id
         WHERE o.status='accepted' AND o.partner_id IS NULL AND u.city_id=?
         ORDER BY o.placed_at""", (zone_city_id,))


def partner_active(partner_id):
    """Active deliveries currently assigned to a partner."""
    return db.query("""
        SELECT o.*, s.shop_name, u.full_name AS buyer_name, ci.name AS buyer_city,
               a.line1 AS address_line
          FROM orders o
          JOIN shops s ON s.shop_id=o.shop_id
          JOIN users u ON u.user_id=o.buyer_id
          JOIN cities ci ON ci.city_id=u.city_id
          LEFT JOIN addresses a ON a.address_id=o.address_id
         WHERE o.partner_id=? AND o.status IN ('assigned','picked_up','in_transit')
         ORDER BY o.placed_at""", (partner_id,))


def partner_history(partner_id):
    """Completed deliveries for a partner (with per-delivery earning)."""
    return db.query("""
        SELECT o.*, s.shop_name, u.full_name AS buyer_name
          FROM orders o
          JOIN shops s ON s.shop_id=o.shop_id
          JOIN users u ON u.user_id=o.buyer_id
         WHERE o.partner_id=? AND o.status='delivered'
         ORDER BY o.placed_at DESC""", (partner_id,))


def partner_totals(partner_id):
    """KPIs for the delivery dashboard stat cards."""
    delivered = db.query_one(
        "SELECT COUNT(*) n FROM orders WHERE partner_id=? AND status='delivered'",
        (partner_id,))["n"]
    active = db.query_one("""
        SELECT COUNT(*) n FROM orders WHERE partner_id=?
           AND status IN ('assigned','picked_up','in_transit')""", (partner_id,))["n"]
    earnings = db.query_one(
        "SELECT COALESCE(SUM(delivery_fee),0) s FROM orders WHERE partner_id=? AND status='delivered'",
        (partner_id,))["s"]
    row = db.query_one("SELECT rating, balance FROM delivery_partners WHERE partner_id=?",
                       (partner_id,))
    return {"delivered": delivered, "active": active, "earnings": earnings,
            "rating": row["rating"] if row else 0,
            "balance": row["balance"] if row else 0}


def partner_daily_earnings(partner_id):
    """Daily delivery earnings series (embedded delivery chart)."""
    return db.query("""
        SELECT date(placed_at) AS day, SUM(delivery_fee) AS earnings
          FROM orders WHERE partner_id=? AND status='delivered'
         GROUP BY date(placed_at) ORDER BY day""", (partner_id,))


# ----------------------------------------------------------------- FILTERED (admin)
def filter_options():
    """Return cities and categories for the admin analytics filter controls."""
    cities = db.query("SELECT city_id, name FROM cities ORDER BY name")
    cats = db.query("SELECT category_id, name FROM categories ORDER BY name")
    return cities, cats


def filtered_analytics(date_from=None, date_to=None, city_id=None, category_id=None):
    """
    Advanced, parameterised analytics used by the admin filter panel.

    Filters delivered-order revenue by an optional placed-at date range, the
    buyer's city and the product category, then returns headline metrics plus a
    daily revenue series and a category breakdown. Demonstrates dynamic,
    safely-parameterised SQL across a multi-table join.
    """
    where = ["o.status = 'delivered'"]
    params = []
    if date_from:
        where.append("date(o.placed_at) >= date(?)"); params.append(date_from)
    if date_to:
        where.append("date(o.placed_at) <= date(?)"); params.append(date_to)
    if city_id:
        where.append("u.city_id = ?"); params.append(city_id)
    if category_id:
        where.append("p.category_id = ?"); params.append(category_id)
    clause = " AND ".join(where)

    base = f"""
        FROM orders o
        JOIN users u       ON u.user_id = o.buyer_id
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p    ON p.product_id = oi.product_id
       WHERE {clause}
    """
    totals = db.query_one(f"""
        SELECT COUNT(DISTINCT o.order_id) AS orders,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue,
               COALESCE(SUM(oi.quantity), 0) AS units {base}""", params)

    daily = db.query(f"""
        SELECT date(o.placed_at) AS day,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue {base}
        GROUP BY date(o.placed_at) ORDER BY day""", params)

    by_cat = db.query(f"""
        SELECT c.name AS category,
               COALESCE(SUM(oi.quantity * oi.unit_price),0) AS revenue
        FROM orders o
        JOIN users u        ON u.user_id = o.buyer_id
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p     ON p.product_id = oi.product_id
        JOIN categories c   ON c.category_id = p.category_id
       WHERE {clause}
       GROUP BY p.category_id ORDER BY revenue DESC""", params)

    return {"orders": totals["orders"], "revenue": totals["revenue"],
            "units": totals["units"], "daily": daily, "by_cat": by_cat}


def buyer_spending(buyer_id):
    """
    A buyer's personal spending analytics: lifetime totals, a monthly spend
    series and a category breakdown — all from their delivered/active orders.
    """
    totals = db.query_one("""
        SELECT COUNT(*) AS orders,
               COALESCE(SUM(total),0) AS spent,
               COALESCE(AVG(total),0) AS avg_order
          FROM orders WHERE buyer_id=? AND status NOT IN ('cancelled','rejected')
    """, (buyer_id,)) or {"orders": 0, "spent": 0, "avg_order": 0}

    monthly = db.query("""
        SELECT strftime('%Y-%m', placed_at) AS month,
               COALESCE(SUM(total),0) AS spent
          FROM orders
         WHERE buyer_id=? AND status NOT IN ('cancelled','rejected')
         GROUP BY month ORDER BY month
    """, (buyer_id,))

    by_cat = db.query("""
        SELECT c.name AS category,
               COALESCE(SUM(oi.quantity * oi.unit_price),0) AS spent
          FROM orders o
          JOIN order_items oi ON oi.order_id = o.order_id
          JOIN products p     ON p.product_id = oi.product_id
          JOIN categories c   ON c.category_id = p.category_id
         WHERE o.buyer_id=? AND o.status NOT IN ('cancelled','rejected')
         GROUP BY p.category_id ORDER BY spent DESC
    """, (buyer_id,))

    loyalty = (db.query_one("SELECT loyalty_points FROM users WHERE user_id=?",
                            (buyer_id,)) or {"loyalty_points": 0})["loyalty_points"]
    return {"orders": totals["orders"], "spent": totals["spent"],
            "avg_order": totals["avg_order"], "monthly": monthly,
            "by_cat": by_cat, "loyalty": loyalty}
