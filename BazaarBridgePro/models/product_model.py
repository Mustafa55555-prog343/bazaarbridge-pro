"""
models/product_model.py
================================================================================
Data-access functions for products: browsing, full-text search, filtering,
reviews, wishlist, comparison and recommendations. Also seller-side product
management (add / edit / delete / stock). These are the app's product "stored
procedures".
================================================================================
"""

from database.db_manager import db


# ----------------------------------------------------------------- BROWSING
def browse_products(search="", category_id=None, city_id=None,
                    min_price=None, max_price=None, min_rating=None,
                    flash_only=False):
    """
    Powerful product browse query combining FULL-TEXT SEARCH (FTS5) with
    category / city / price / rating filters. Demonstrates a meaningful
    multi-table JOIN (products + shops + categories + cities).
    Returns approved, in-scope products as dict rows.
    """
    params = []
    sql = """
        SELECT p.*, s.shop_name, s.is_verified, s.rating AS shop_rating,
               c.name AS category, ci.name AS city
          FROM products p
          JOIN shops s     ON s.shop_id = p.shop_id
          JOIN categories c ON c.category_id = p.category_id
          JOIN cities ci   ON ci.city_id = s.city_id
         WHERE p.status = 'approved'
    """
    # Full-text search via the FTS5 index (correlated subquery).
    if search.strip():
        sql += " AND p.product_id IN (SELECT rowid FROM products_fts WHERE products_fts MATCH ?)"
        # Append a prefix wildcard so partial words match (e.g. 'crick' -> cricket).
        params.append(_fts_query(search))
    if category_id:
        sql += " AND p.category_id = ?"; params.append(category_id)
    if city_id:
        sql += " AND s.city_id = ?"; params.append(city_id)
    if min_price is not None:
        sql += " AND p.price >= ?"; params.append(min_price)
    if max_price is not None:
        sql += " AND p.price <= ?"; params.append(max_price)
    if min_rating is not None:
        sql += " AND s.rating >= ?"; params.append(min_rating)
    if flash_only:
        sql += " AND p.is_flash = 1"
    sql += " ORDER BY p.is_flash DESC, p.rating DESC, p.created_at DESC"
    try:
        return db.query(sql, tuple(params))
    except Exception:
        # If the FTS query had odd characters, fall back to a LIKE search.
        return _browse_like(search, category_id, city_id, min_price, max_price,
                            min_rating, flash_only)


def _fts_query(search):
    """Turn user text into a safe FTS5 prefix query (each token + '*')."""
    tokens = [t for t in "".join(
        ch if ch.isalnum() or ch.isspace() else " " for ch in search).split() if t]
    return " ".join(f"{t}*" for t in tokens) if tokens else search


def _browse_like(search, category_id, city_id, min_price, max_price,
                 min_rating, flash_only):
    """Fallback browse using LIKE (keeps the app crash-proof)."""
    params = [f"%{search}%", f"%{search}%"]
    sql = """
        SELECT p.*, s.shop_name, s.is_verified, s.rating AS shop_rating,
               c.name AS category, ci.name AS city
          FROM products p
          JOIN shops s     ON s.shop_id = p.shop_id
          JOIN categories c ON c.category_id = p.category_id
          JOIN cities ci   ON ci.city_id = s.city_id
         WHERE p.status='approved' AND (p.name LIKE ? OR p.description LIKE ?)
    """
    if category_id:
        sql += " AND p.category_id=?"; params.append(category_id)
    if city_id:
        sql += " AND s.city_id=?"; params.append(city_id)
    if min_price is not None:
        sql += " AND p.price>=?"; params.append(min_price)
    if max_price is not None:
        sql += " AND p.price<=?"; params.append(max_price)
    if min_rating is not None:
        sql += " AND s.rating>=?"; params.append(min_rating)
    if flash_only:
        sql += " AND p.is_flash=1"
    sql += " ORDER BY p.rating DESC"
    return db.query(sql, tuple(params))


def get_product(product_id):
    """Return a full product detail row joined with shop + category info."""
    row = db.query_one("""
        SELECT p.*, s.shop_name, s.seller_id, s.is_verified, s.rating AS shop_rating,
               s.description AS shop_desc, c.name AS category, ci.name AS city
          FROM products p
          JOIN shops s ON s.shop_id=p.shop_id
          JOIN categories c ON c.category_id=p.category_id
          JOIN cities ci ON ci.city_id=s.city_id
         WHERE p.product_id=?""", (product_id,))
    return dict(row) if row else None


def flash_sale_products():
    """Return all active flash-sale products."""
    return browse_products(flash_only=True)


def recommended_for(buyer_id, limit=6):
    """
    Recommend products from the categories the buyer has bought/wishlisted
    before. Demonstrates a correlated subquery over the buyer's history.
    """
    rows = db.query("""
        SELECT p.*, s.shop_name, c.name AS category
          FROM products p
          JOIN shops s ON s.shop_id=p.shop_id
          JOIN categories c ON c.category_id=p.category_id
         WHERE p.status='approved' AND p.stock>0
           AND p.category_id IN (
                SELECT DISTINCT pr.category_id
                  FROM order_items oi
                  JOIN orders o ON o.order_id=oi.order_id
                  JOIN products pr ON pr.product_id=oi.product_id
                 WHERE o.buyer_id=?
                UNION
                SELECT pr.category_id FROM wishlist w
                  JOIN products pr ON pr.product_id=w.product_id
                 WHERE w.buyer_id=?)
         ORDER BY p.rating DESC LIMIT ?""", (buyer_id, buyer_id, limit))
    if rows:
        return rows
    # New buyer with no history -> show top-rated products instead.
    return db.query("""
        SELECT p.*, s.shop_name, c.name AS category FROM products p
          JOIN shops s ON s.shop_id=p.shop_id
          JOIN categories c ON c.category_id=p.category_id
         WHERE p.status='approved' AND p.stock>0
         ORDER BY p.rating DESC LIMIT ?""", (limit,))


# ----------------------------------------------------------------- REVIEWS
def get_reviews(product_id):
    """Return all reviews for a product with reviewer names."""
    return db.query("""
        SELECT r.*, u.full_name FROM reviews r
          JOIN users u ON u.user_id=r.buyer_id
         WHERE r.product_id=? ORDER BY r.created_at DESC""", (product_id,))


def can_review(buyer_id, product_id):
    """A buyer may review only a product they actually received (delivered)."""
    row = db.query_one("""
        SELECT 1 FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
         WHERE o.buyer_id=? AND oi.product_id=? AND o.status='delivered' LIMIT 1""",
        (buyer_id, product_id))
    return row is not None


def add_review(buyer_id, product_id, rating, comment):
    """
    Insert/replace a review. The review-averaging TRIGGER updates the product's
    rating automatically. Returns (ok, message).
    """
    try:
        existing = db.query_one(
            "SELECT review_id FROM reviews WHERE buyer_id=? AND product_id=?",
            (buyer_id, product_id))
        if existing:
            db.execute("UPDATE reviews SET rating=?, comment=? WHERE review_id=?",
                       (rating, comment, existing["review_id"]))
            # Manually refresh average for the UPDATE case (triggers cover ins/del).
            db.execute("""UPDATE products SET
                            rating=(SELECT ROUND(AVG(rating),2) FROM reviews WHERE product_id=?),
                            review_count=(SELECT COUNT(*) FROM reviews WHERE product_id=?)
                          WHERE product_id=?""",
                       (product_id, product_id, product_id))
        else:
            db.execute("INSERT INTO reviews(product_id,buyer_id,rating,comment) VALUES(?,?,?,?)",
                       (product_id, buyer_id, rating, comment))
        return True, "Thank you for your review!"
    except Exception as e:
        return False, f"Could not save review: {e}"


# ----------------------------------------------------------------- WISHLIST
def get_wishlist(buyer_id):
    """Return wishlisted products for a buyer."""
    return db.query("""
        SELECT p.*, s.shop_name, c.name AS category FROM wishlist w
          JOIN products p ON p.product_id=w.product_id
          JOIN shops s ON s.shop_id=p.shop_id
          JOIN categories c ON c.category_id=p.category_id
         WHERE w.buyer_id=? ORDER BY w.wishlist_id DESC""", (buyer_id,))


def toggle_wishlist(buyer_id, product_id):
    """Add or remove a product from the wishlist. Returns new state (bool)."""
    row = db.query_one("SELECT wishlist_id FROM wishlist WHERE buyer_id=? AND product_id=?",
                       (buyer_id, product_id))
    if row:
        db.execute("DELETE FROM wishlist WHERE wishlist_id=?", (row["wishlist_id"],))
        return False
    db.execute("INSERT INTO wishlist(buyer_id,product_id) VALUES(?,?)",
               (buyer_id, product_id))
    return True


def in_wishlist(buyer_id, product_id):
    """Return True if a product is already in the buyer's wishlist."""
    return db.query_one("SELECT 1 FROM wishlist WHERE buyer_id=? AND product_id=?",
                        (buyer_id, product_id)) is not None


def compare_products(ids):
    """Return product rows for a set of ids (product comparison tool)."""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    return db.query(f"""
        SELECT p.*, s.shop_name, c.name AS category, ci.name AS city
          FROM products p JOIN shops s ON s.shop_id=p.shop_id
          JOIN categories c ON c.category_id=p.category_id
          JOIN cities ci ON ci.city_id=s.city_id
         WHERE p.product_id IN ({placeholders})""", tuple(ids))


# ----------------------------------------------------------------- SELLER MGMT
def shop_for_seller(seller_id):
    """Return the shop row owned by a seller."""
    row = db.query_one("SELECT * FROM shops WHERE seller_id=?", (seller_id,))
    return dict(row) if row else None


def seller_products(shop_id):
    """Return all products for a shop (any status) with category names."""
    return db.query("""
        SELECT p.*, c.name AS category FROM products p
          JOIN categories c ON c.category_id=p.category_id
         WHERE p.shop_id=? ORDER BY p.created_at DESC""", (shop_id,))


def add_product(shop_id, category_id, name, description, price, stock, low_stock_at=5):
    """Insert a new product (status pending until admin approves)."""
    return db.execute("""
        INSERT INTO products(shop_id,category_id,name,description,price,stock,low_stock_at,status)
        VALUES(?,?,?,?,?,?,?, 'approved')""",
        (shop_id, category_id, name.strip(), description.strip(), price, stock, low_stock_at))


def update_product(product_id, category_id, name, description, price, stock, low_stock_at):
    """Update an existing product's editable fields."""
    db.execute("""
        UPDATE products SET category_id=?, name=?, description=?, price=?,
               stock=?, low_stock_at=? WHERE product_id=?""",
        (category_id, name.strip(), description.strip(), price, stock,
         low_stock_at, product_id))


def delete_product(product_id):
    """Delete a product (FTS + dependent rows cascade via triggers/FKs)."""
    db.execute("DELETE FROM products WHERE product_id=?", (product_id,))


def set_stock(product_id, stock):
    """Directly set stock (used by bulk stock update). Triggers low-stock alert."""
    db.execute("UPDATE products SET stock=? WHERE product_id=?", (stock, product_id))


def low_stock_products(shop_id):
    """Return products at/below their low-stock threshold for a shop."""
    return db.query("""
        SELECT * FROM products WHERE shop_id=? AND stock<=low_stock_at
         ORDER BY stock ASC""", (shop_id,))


def set_flash(product_id, is_flash, flash_price=None):
    """Toggle a product into/out of a flash sale (promotional tool)."""
    db.execute("UPDATE products SET is_flash=?, flash_price=? WHERE product_id=?",
               (1 if is_flash else 0, flash_price, product_id))
