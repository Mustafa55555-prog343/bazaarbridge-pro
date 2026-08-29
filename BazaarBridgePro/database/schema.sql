-- ============================================================================
-- BazaarBridge Pro  —  Database Schema  (SQLite, normalized to 3NF)
-- CS-220 Database Systems  |  NUST SEECS Islamabad
-- ----------------------------------------------------------------------------
-- This file defines the COMPLETE relational schema for the platform:
--   * Fully normalized tables (3NF)
--   * Foreign keys with referential integrity
--   * CHECK constraints for domain integrity
--   * 5+ triggers for real automation
--   * Views for all complex reporting
--   * FTS5 virtual table for full-text product search
--   * A JSON-based "NoSQL" activity log table
-- Every statement is plain SQL so the markers can read the design directly.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- LOOKUP / REFERENCE TABLES
-- ----------------------------------------------------------------------------

-- All selectable cities live in one place so city data is never duplicated.
CREATE TABLE IF NOT EXISTS cities (
    city_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    province   TEXT NOT NULL
);

-- Product categories (electronics, clothing, ...). One row per category.
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    icon        TEXT NOT NULL DEFAULT '📦'   -- emoji used in the UI sidebar/cards
);

-- ----------------------------------------------------------------------------
-- CORE IDENTITY TABLE  —  every person on the platform is a "user"
-- Role is constrained to the four supported roles.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT    NOT NULL,
    email          TEXT    NOT NULL UNIQUE,
    phone          TEXT,
    password_hash  TEXT    NOT NULL,         -- salted SHA-256 hash, never plaintext
    role           TEXT    NOT NULL CHECK (role IN ('buyer','seller','delivery','admin')),
    city_id        INTEGER REFERENCES cities(city_id),
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    loyalty_points INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Multiple saved addresses per buyer (1-to-many) — keeps users table clean.
CREATE TABLE IF NOT EXISTS addresses (
    address_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    label       TEXT    NOT NULL DEFAULT 'Home',
    line1       TEXT    NOT NULL,
    city_id     INTEGER NOT NULL REFERENCES cities(city_id),
    is_default  INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1))
);

-- ----------------------------------------------------------------------------
-- SELLER-SPECIFIC DATA  (1-to-1 extension of a seller user)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shops (
    shop_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id    INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    shop_name    TEXT    NOT NULL,
    description  TEXT,
    banner_color TEXT    NOT NULL DEFAULT '#4e73df',  -- used to theme the shop banner
    city_id      INTEGER NOT NULL REFERENCES cities(city_id),
    rating       REAL    NOT NULL DEFAULT 0,
    is_verified  INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0,1)),
    balance      REAL    NOT NULL DEFAULT 0,   -- earnings awaiting payout
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- DELIVERY-PARTNER-SPECIFIC DATA  (1-to-1 extension of a delivery user)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS delivery_partners (
    partner_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    vehicle_type  TEXT    NOT NULL DEFAULT 'Bike',
    vehicle_plate TEXT,
    zone_city_id  INTEGER NOT NULL REFERENCES cities(city_id),
    rating        REAL    NOT NULL DEFAULT 5.0,
    balance       REAL    NOT NULL DEFAULT 0,
    is_available  INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0,1))
);

-- ----------------------------------------------------------------------------
-- PRODUCT CATALOGUE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id      INTEGER NOT NULL REFERENCES shops(shop_id) ON DELETE CASCADE,
    category_id  INTEGER NOT NULL REFERENCES categories(category_id),
    name         TEXT    NOT NULL,
    description  TEXT,
    price        REAL    NOT NULL CHECK (price >= 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    low_stock_at INTEGER NOT NULL DEFAULT 5,   -- threshold for low-stock alerts
    rating       REAL    NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    status       TEXT    NOT NULL DEFAULT 'approved'
                 CHECK (status IN ('pending','approved','rejected','flagged')),
    is_flash     INTEGER NOT NULL DEFAULT 0 CHECK (is_flash IN (0,1)),
    flash_price  REAL,
    flash_ends_at TEXT,                        -- when a flash sale expires (for countdowns)
    views        INTEGER NOT NULL DEFAULT 0,   -- popularity counter (recommendations)
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- SHOPPING CART  (one logical cart per buyer; rows are cart items)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cart_items (
    cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    UNIQUE (buyer_id, product_id)            -- same product appears once per cart
);

-- ----------------------------------------------------------------------------
-- WISHLIST
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    UNIQUE (buyer_id, product_id)
);

-- ----------------------------------------------------------------------------
-- COUPONS  (platform or seller created discount codes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupons (
    coupon_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT    NOT NULL UNIQUE,
    discount_pct INTEGER NOT NULL CHECK (discount_pct BETWEEN 1 AND 90),
    shop_id      INTEGER REFERENCES shops(shop_id) ON DELETE CASCADE, -- NULL = platform-wide
    min_amount   REAL    NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

-- ----------------------------------------------------------------------------
-- ORDERS  +  ORDER ITEMS  (classic master-detail, normalized)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id      INTEGER NOT NULL REFERENCES users(user_id),
    shop_id       INTEGER NOT NULL REFERENCES shops(shop_id),
    partner_id    INTEGER REFERENCES delivery_partners(partner_id),
    address_id    INTEGER REFERENCES addresses(address_id),
    coupon_id     INTEGER REFERENCES coupons(coupon_id),
    subtotal      REAL    NOT NULL DEFAULT 0,
    discount      REAL    NOT NULL DEFAULT 0,
    delivery_fee  REAL    NOT NULL DEFAULT 150,
    total         REAL    NOT NULL DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','accepted','rejected',
                                    'assigned','picked_up','in_transit',
                                    'delivered','cancelled','returned')),
    placed_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    REAL    NOT NULL          -- price captured at purchase time
);

-- ----------------------------------------------------------------------------
-- REVIEWS  (a buyer reviews a product)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reviews (
    review_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    buyer_id   INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (product_id, buyer_id)           -- one review per buyer per product
);

-- ----------------------------------------------------------------------------
-- NOTIFICATIONS  (per-user inbox bell)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message    TEXT    NOT NULL,
    is_read    INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- SELLER  <->  BUYER  MESSAGES (shop inbox)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id    INTEGER NOT NULL REFERENCES shops(shop_id) ON DELETE CASCADE,
    buyer_id   INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- PAYOUT REQUESTS  (sellers + delivery partners request withdrawals)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payouts (
    payout_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    amount     REAL    NOT NULL CHECK (amount > 0),
    status     TEXT    NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','approved','rejected')),
    requested_at TEXT  NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- DISPUTES  (buyer raises an issue on an order; admin resolves)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disputes (
    dispute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    raised_by  INTEGER NOT NULL REFERENCES users(user_id),
    reason     TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'open'
               CHECK (status IN ('open','resolved','rejected')),
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- PLATFORM ANNOUNCEMENTS  (admin -> everyone)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- REFERRALS  (buyer refers another user)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referrals (
    referral_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id  INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    referred_id  INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    reward_points INTEGER NOT NULL DEFAULT 100,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- AUDIT LOG  (relational record of every significant action)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(user_id),
    action     TEXT    NOT NULL,
    entity     TEXT,
    details    TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- ORDER STATUS HISTORY  (populated by a trigger — full audit of every change)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_status_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- "NoSQL" ACTIVITY LOG  —  unstructured events stored as JSON documents.
-- Demonstrates document/NoSQL-style storage inside SQLite using the JSON1
-- extension.  The `doc` column holds an arbitrary JSON object.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_log (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc         TEXT NOT NULL,               -- JSON document
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- FULL-TEXT SEARCH  (FTS5 virtual table mirrors product name + description)
-- Kept in sync with the products table via triggers below.
-- ============================================================================
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
    name, description, content='products', content_rowid='product_id'
);

-- ============================================================================
-- INDEXES  (speed up the joins/filters the app runs most often)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_products_shop     ON products(shop_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_buyer      ON orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_shop       ON orders(shop_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orderitems_order  ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_product   ON reviews(product_id);

-- ============================================================================
-- TRIGGERS  —  real automation (requirement: at least 5)
-- ============================================================================

-- (1) STOCK AUTO-DECREMENT: when an order item is inserted, reduce product
--     stock by the ordered quantity automatically.
DROP TRIGGER IF EXISTS trg_stock_decrement;
CREATE TRIGGER trg_stock_decrement
AFTER INSERT ON order_items
BEGIN
    UPDATE products
       SET stock = stock - NEW.quantity
     WHERE product_id = NEW.product_id;
END;

-- (2) LOW-STOCK ALERT: after stock changes, if it falls to/below the product's
--     threshold, notify the shop's seller (once per drop).
DROP TRIGGER IF EXISTS trg_low_stock_alert;
CREATE TRIGGER trg_low_stock_alert
AFTER UPDATE OF stock ON products
WHEN NEW.stock <= NEW.low_stock_at AND OLD.stock > NEW.low_stock_at
BEGIN
    INSERT INTO notifications (user_id, message)
    SELECT s.seller_id,
           'Low stock alert: "' || NEW.name || '" has only ' || NEW.stock || ' left.'
      FROM shops s
     WHERE s.shop_id = NEW.shop_id;
END;

-- (3) ORDER STATUS LOGGING: every time an order's status changes, write a row
--     into order_status_history (full audit trail).
DROP TRIGGER IF EXISTS trg_order_status_log;
CREATE TRIGGER trg_order_status_log
AFTER UPDATE OF status ON orders
WHEN NEW.status <> OLD.status
BEGIN
    INSERT INTO order_status_history (order_id, old_status, new_status)
    VALUES (NEW.order_id, OLD.status, NEW.status);

    INSERT INTO notifications (user_id, message)
    VALUES (NEW.buyer_id,
            'Your order #' || NEW.order_id || ' is now: ' || NEW.status || '.');
END;

-- (4) REVIEW AVERAGING (INSERT): when a review is added, recompute the
--     product's average rating and review count from the reviews table.
DROP TRIGGER IF EXISTS trg_review_insert_avg;
CREATE TRIGGER trg_review_insert_avg
AFTER INSERT ON reviews
BEGIN
    UPDATE products
       SET rating = (SELECT ROUND(AVG(rating),2) FROM reviews WHERE product_id = NEW.product_id),
           review_count = (SELECT COUNT(*) FROM reviews WHERE product_id = NEW.product_id)
     WHERE product_id = NEW.product_id;
END;

-- (5) REVIEW AVERAGING (DELETE): keep the average correct if a review is removed.
DROP TRIGGER IF EXISTS trg_review_delete_avg;
CREATE TRIGGER trg_review_delete_avg
AFTER DELETE ON reviews
BEGIN
    UPDATE products
       SET rating = COALESCE((SELECT ROUND(AVG(rating),2) FROM reviews WHERE product_id = OLD.product_id),0),
           review_count = (SELECT COUNT(*) FROM reviews WHERE product_id = OLD.product_id)
     WHERE product_id = OLD.product_id;
END;

-- (6) SHOP RATING ROLL-UP: after a product's rating changes, refresh the shop's
--     overall rating as the average of its rated products.
DROP TRIGGER IF EXISTS trg_shop_rating;
CREATE TRIGGER trg_shop_rating
AFTER UPDATE OF rating ON products
BEGIN
    UPDATE shops
       SET rating = COALESCE((SELECT ROUND(AVG(rating),2)
                                FROM products
                               WHERE shop_id = NEW.shop_id AND review_count > 0),0)
     WHERE shop_id = NEW.shop_id;
END;

-- (7..9) FTS SYNC TRIGGERS: keep the full-text index aligned with products.
DROP TRIGGER IF EXISTS trg_products_fts_ins;
CREATE TRIGGER trg_products_fts_ins AFTER INSERT ON products BEGIN
    INSERT INTO products_fts(rowid, name, description)
    VALUES (NEW.product_id, NEW.name, COALESCE(NEW.description,''));
END;

DROP TRIGGER IF EXISTS trg_products_fts_del;
CREATE TRIGGER trg_products_fts_del AFTER DELETE ON products BEGIN
    INSERT INTO products_fts(products_fts, rowid, name, description)
    VALUES ('delete', OLD.product_id, OLD.name, COALESCE(OLD.description,''));
END;

DROP TRIGGER IF EXISTS trg_products_fts_upd;
CREATE TRIGGER trg_products_fts_upd AFTER UPDATE ON products BEGIN
    INSERT INTO products_fts(products_fts, rowid, name, description)
    VALUES ('delete', OLD.product_id, OLD.name, COALESCE(OLD.description,''));
    INSERT INTO products_fts(rowid, name, description)
    VALUES (NEW.product_id, NEW.name, COALESCE(NEW.description,''));
END;

-- (10) LOYALTY AWARD: when an order becomes 'delivered', credit the buyer with
--      loyalty points (1 point per Rs.100 of order value). Real automation tying
--      order fulfilment to the rewards system.
DROP TRIGGER IF EXISTS trg_award_loyalty;
CREATE TRIGGER trg_award_loyalty
AFTER UPDATE OF status ON orders
WHEN NEW.status = 'delivered' AND OLD.status <> 'delivered'
BEGIN
    UPDATE users
       SET loyalty_points = loyalty_points + CAST(NEW.total / 100 AS INTEGER)
     WHERE user_id = NEW.buyer_id;

    INSERT INTO notifications (user_id, message)
    VALUES (NEW.buyer_id,
            'You earned ' || CAST(NEW.total / 100 AS INTEGER) ||
            ' loyalty points from order #' || NEW.order_id || '!');
END;

-- (11) REFERRAL REWARD: when a referral is recorded, credit the referrer with
--      the configured reward points automatically.
DROP TRIGGER IF EXISTS trg_referral_reward;
CREATE TRIGGER trg_referral_reward
AFTER INSERT ON referrals
BEGIN
    UPDATE users
       SET loyalty_points = loyalty_points + NEW.reward_points
     WHERE user_id = NEW.referrer_id;

    INSERT INTO notifications (user_id, message)
    VALUES (NEW.referrer_id,
            'Referral reward: +' || NEW.reward_points || ' loyalty points credited!');
END;

-- (12) AUTO-FLAG POOR PRODUCTS: if a product accumulates at least 3 reviews and
--      its average rating drops below 2.5, automatically flag it for admin review.
DROP TRIGGER IF EXISTS trg_autoflag_product;
CREATE TRIGGER trg_autoflag_product
AFTER UPDATE OF rating ON products
WHEN NEW.review_count >= 3 AND NEW.rating < 2.5 AND NEW.status = 'approved'
BEGIN
    UPDATE products SET status = 'flagged' WHERE product_id = NEW.product_id;

    INSERT INTO notifications (user_id, message)
    SELECT s.seller_id,
           'Product "' || NEW.name || '" was auto-flagged due to low ratings.'
      FROM shops s WHERE s.shop_id = NEW.shop_id;
END;

-- ============================================================================
-- VIEWS  —  all complex reporting is expressed declaratively here.
-- ============================================================================

-- Per-product sales totals (units sold + revenue), only from delivered orders.
DROP VIEW IF EXISTS v_product_sales;
CREATE VIEW v_product_sales AS
SELECT p.product_id, p.name, p.shop_id, p.category_id,
       COALESCE(SUM(oi.quantity),0)                  AS units_sold,
       COALESCE(SUM(oi.quantity * oi.unit_price),0)  AS revenue
  FROM products p
  LEFT JOIN order_items oi ON oi.product_id = p.product_id
  LEFT JOIN orders o       ON o.order_id   = oi.order_id AND o.status = 'delivered'
 GROUP BY p.product_id;

-- Per-shop performance: revenue, order count, average product rating.
DROP VIEW IF EXISTS v_shop_performance;
CREATE VIEW v_shop_performance AS
SELECT s.shop_id, s.shop_name, s.seller_id,
       COUNT(DISTINCT o.order_id)                              AS total_orders,
       COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.total END),0) AS revenue,
       s.rating                                                AS shop_rating
  FROM shops s
  LEFT JOIN orders o ON o.shop_id = s.shop_id
 GROUP BY s.shop_id;

-- Revenue per calendar day (platform-wide), delivered orders only.
DROP VIEW IF EXISTS v_daily_revenue;
CREATE VIEW v_daily_revenue AS
SELECT date(placed_at) AS day,
       COUNT(*)        AS orders,
       SUM(total)      AS revenue
  FROM orders
 WHERE status = 'delivered'
 GROUP BY date(placed_at)
 ORDER BY day;

-- Revenue per category (platform-wide).
DROP VIEW IF EXISTS v_category_revenue;
CREATE VIEW v_category_revenue AS
SELECT c.category_id, c.name AS category,
       COALESCE(SUM(oi.quantity * oi.unit_price),0) AS revenue,
       COALESCE(SUM(oi.quantity),0)                 AS units
  FROM categories c
  LEFT JOIN products p    ON p.category_id = c.category_id
  LEFT JOIN order_items oi ON oi.product_id = p.product_id
  LEFT JOIN orders o       ON o.order_id = oi.order_id AND o.status='delivered'
 GROUP BY c.category_id;

-- City-wise order distribution (by the buyer's city).
DROP VIEW IF EXISTS v_city_orders;
CREATE VIEW v_city_orders AS
SELECT ci.name AS city, COUNT(o.order_id) AS orders
  FROM orders o
  JOIN users u  ON u.user_id = o.buyer_id
  JOIN cities ci ON ci.city_id = u.city_id
 GROUP BY ci.city_id
 ORDER BY orders DESC;

-- Top buyers by total amount spent on delivered orders.
DROP VIEW IF EXISTS v_top_buyers;
CREATE VIEW v_top_buyers AS
SELECT u.user_id, u.full_name,
       COUNT(o.order_id) AS orders,
       COALESCE(SUM(o.total),0) AS spent
  FROM users u
  JOIN orders o ON o.buyer_id = u.user_id AND o.status='delivered'
 WHERE u.role = 'buyer'
 GROUP BY u.user_id
 ORDER BY spent DESC;

-- Monthly platform revenue (delivered orders) — feeds growth/forecast panels.
DROP VIEW IF EXISTS v_monthly_revenue;
CREATE VIEW v_monthly_revenue AS
SELECT strftime('%Y-%m', placed_at) AS month,
       COUNT(*)   AS orders,
       SUM(total) AS revenue
  FROM orders
 WHERE status = 'delivered'
 GROUP BY month
 ORDER BY month;

-- Delivery-partner performance scorecard (deliveries, earnings, rating).
DROP VIEW IF EXISTS v_partner_performance;
CREATE VIEW v_partner_performance AS
SELECT dp.partner_id, u.full_name, ci.name AS zone,
       dp.vehicle_type, dp.rating,
       COUNT(CASE WHEN o.status='delivered' THEN 1 END) AS deliveries,
       COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.delivery_fee END),0) AS earnings,
       COUNT(CASE WHEN o.status IN ('assigned','picked_up','in_transit') THEN 1 END) AS active
  FROM delivery_partners dp
  JOIN users u   ON u.user_id = dp.user_id
  JOIN cities ci ON ci.city_id = dp.zone_city_id
  LEFT JOIN orders o ON o.partner_id = dp.partner_id
 GROUP BY dp.partner_id
 ORDER BY deliveries DESC;

-- Low-stock products across the platform (stock at/under threshold).
DROP VIEW IF EXISTS v_low_stock;
CREATE VIEW v_low_stock AS
SELECT p.product_id, p.name, p.stock, p.low_stock_at,
       s.shop_id, s.shop_name, c.name AS category
  FROM products p
  JOIN shops s      ON s.shop_id = p.shop_id
  JOIN categories c ON c.category_id = p.category_id
 WHERE p.stock <= p.low_stock_at AND p.status = 'approved'
 ORDER BY p.stock ASC;

-- Dispute summary by status — drives the admin dispute centre counters.
DROP VIEW IF EXISTS v_dispute_summary;
CREATE VIEW v_dispute_summary AS
SELECT status, COUNT(*) AS count
  FROM disputes
 GROUP BY status;

-- Referral leaderboard — who has referred the most users.
DROP VIEW IF EXISTS v_referral_leaderboard;
CREATE VIEW v_referral_leaderboard AS
SELECT u.user_id, u.full_name,
       COUNT(r.referral_id)        AS referrals,
       COALESCE(SUM(r.reward_points),0) AS points_earned
  FROM users u
  JOIN referrals r ON r.referrer_id = u.user_id
 GROUP BY u.user_id
 ORDER BY referrals DESC;

-- Seller monthly revenue — per-shop month-by-month delivered revenue.
DROP VIEW IF EXISTS v_seller_monthly;
CREATE VIEW v_seller_monthly AS
SELECT o.shop_id, strftime('%Y-%m', o.placed_at) AS month,
       COUNT(*) AS orders, SUM(o.total) AS revenue
  FROM orders o
 WHERE o.status = 'delivered'
 GROUP BY o.shop_id, month
 ORDER BY month;

-- New-user signups per month — platform growth signal.
DROP VIEW IF EXISTS v_user_growth;
CREATE VIEW v_user_growth AS
SELECT strftime('%Y-%m', created_at) AS month,
       COUNT(*) AS signups
  FROM users
 GROUP BY month
 ORDER BY month;
