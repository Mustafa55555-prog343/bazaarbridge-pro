"""
models/order_model.py
================================================================================
Data-access functions for the cart, checkout (a real multi-step TRANSACTION),
order lifecycle (accept/reject/assign/deliver), cancellations, returns, coupons
and loyalty points.
================================================================================
"""

from database.db_manager import db


# ----------------------------------------------------------------- CART
def get_cart(buyer_id):
    """Return cart items joined with product + shop info (with line totals)."""
    return db.query("""
        SELECT ci.cart_item_id, ci.quantity, p.product_id, p.name, p.price,
               p.stock, p.is_flash, p.flash_price, s.shop_id, s.shop_name,
               (CASE WHEN p.is_flash=1 THEN p.flash_price ELSE p.price END) AS unit_price,
               (CASE WHEN p.is_flash=1 THEN p.flash_price ELSE p.price END)*ci.quantity AS line_total
          FROM cart_items ci
          JOIN products p ON p.product_id=ci.product_id
          JOIN shops s ON s.shop_id=p.shop_id
         WHERE ci.buyer_id=? ORDER BY ci.cart_item_id""", (buyer_id,))


def cart_count(buyer_id):
    """Return total quantity of items in the cart (for the header badge)."""
    row = db.query_one("SELECT COALESCE(SUM(quantity),0) n FROM cart_items WHERE buyer_id=?",
                       (buyer_id,))
    return row["n"]


def add_to_cart(buyer_id, product_id, quantity=1):
    """
    Add a product to the cart (or bump quantity). Validates stock.
    Returns (ok, message).
    """
    product = db.query_one("SELECT stock, name FROM products WHERE product_id=?", (product_id,))
    if not product:
        return False, "Product not found."
    if product["stock"] <= 0:
        return False, "This product is out of stock."
    existing = db.query_one(
        "SELECT cart_item_id, quantity FROM cart_items WHERE buyer_id=? AND product_id=?",
        (buyer_id, product_id))
    new_qty = quantity + (existing["quantity"] if existing else 0)
    if new_qty > product["stock"]:
        return False, f"Only {product['stock']} in stock."
    if existing:
        db.execute("UPDATE cart_items SET quantity=? WHERE cart_item_id=?",
                   (new_qty, existing["cart_item_id"]))
    else:
        db.execute("INSERT INTO cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)",
                   (buyer_id, product_id, quantity))
    return True, f"Added '{product['name']}' to cart."


def update_cart_quantity(cart_item_id, quantity):
    """Set the quantity of a cart line (or remove it if quantity <= 0)."""
    if quantity <= 0:
        db.execute("DELETE FROM cart_items WHERE cart_item_id=?", (cart_item_id,))
    else:
        db.execute("UPDATE cart_items SET quantity=? WHERE cart_item_id=?",
                   (quantity, cart_item_id))


def remove_cart_item(cart_item_id):
    """Remove one item from the cart."""
    db.execute("DELETE FROM cart_items WHERE cart_item_id=?", (cart_item_id,))


def clear_cart(buyer_id):
    """Empty a buyer's cart."""
    db.execute("DELETE FROM cart_items WHERE buyer_id=?", (buyer_id,))


# ----------------------------------------------------------------- COUPONS
def validate_coupon(code, subtotal, shop_id):
    """
    Check a coupon code against the subtotal and shop scope.
    Returns (coupon_row_or_None, message).
    """
    row = db.query_one("SELECT * FROM coupons WHERE code=? AND is_active=1",
                       (code.strip().upper(),))
    if not row:
        return None, "Invalid or expired coupon code."
    if row["shop_id"] is not None and row["shop_id"] != shop_id:
        return None, "This coupon does not apply to items in your cart."
    if subtotal < row["min_amount"]:
        return None, f"Minimum order of Rs {row['min_amount']:.0f} required for this coupon."
    return dict(row), f"Coupon applied: {row['discount_pct']}% off."


# ----------------------------------------------------------------- CHECKOUT
def checkout(buyer_id, address_id, coupon_code=None, redeem_points=0):
    """
    Place orders from the cart inside a single TRANSACTION.

    Because items can belong to multiple shops, we create one order per shop.
    The whole operation is atomic: if anything fails, every change is rolled
    back (no half-placed orders, no lost stock). On success the cart is cleared,
    any redeemed loyalty points are deducted, and fresh loyalty points are
    awarded on the amount actually paid.

    ``redeem_points`` lets the buyer spend loyalty points at 1 point = Rs 1,
    applied as an extra discount on the first order. It is clamped to the
    buyer's available balance and never exceeds the order value.

    Returns (ok, message, order_ids).
    """
    cart = get_cart(buyer_id)
    if not cart:
        return False, "Your cart is empty.", []

    # Re-validate stock right before committing (prevents overselling).
    for item in cart:
        if item["quantity"] > item["stock"]:
            return False, f"'{item['name']}' has only {item['stock']} left.", []

    # Clamp the redemption to what the buyer actually has.
    available = db.query_one("SELECT loyalty_points FROM users WHERE user_id=?",
                             (buyer_id,))["loyalty_points"]
    redeem_points = max(0, min(int(redeem_points or 0), int(available)))

    # Group cart lines by shop.
    by_shop = {}
    for item in cart:
        by_shop.setdefault(item["shop_id"], []).append(item)

    created = []
    redeemed_used = 0
    try:
        with db.transaction() as cur:
            first = True
            for shop_id, items in by_shop.items():
                subtotal = sum(i["unit_price"] * i["quantity"] for i in items)

                # Resolve coupon (per shop).
                discount = 0
                coupon_id = None
                if coupon_code:
                    crow = db.query_one(
                        "SELECT * FROM coupons WHERE code=? AND is_active=1",
                        (coupon_code.strip().upper(),))
                    if crow and (crow["shop_id"] is None or crow["shop_id"] == shop_id) \
                            and subtotal >= crow["min_amount"]:
                        discount = round(subtotal * crow["discount_pct"] / 100)
                        coupon_id = crow["coupon_id"]

                delivery_fee = 150
                # Apply any loyalty redemption to the first order only.
                loyalty_cut = 0
                if first and redeem_points > 0:
                    loyalty_cut = min(redeem_points, subtotal - discount)
                    redeemed_used = loyalty_cut
                    first = False
                total = subtotal - discount - loyalty_cut + delivery_fee

                cur.execute("""
                    INSERT INTO orders(buyer_id,shop_id,address_id,coupon_id,
                                       subtotal,discount,delivery_fee,total,status)
                    VALUES(?,?,?,?,?,?,?,?, 'pending')""",
                    (buyer_id, shop_id, address_id, coupon_id,
                     subtotal, discount + loyalty_cut, delivery_fee, total))
                order_id = cur.lastrowid
                created.append(order_id)

                for i in items:
                    # Insert line item -> stock-decrement trigger fires here.
                    cur.execute("""
                        INSERT INTO order_items(order_id,product_id,quantity,unit_price)
                        VALUES(?,?,?,?)""",
                        (order_id, i["product_id"], i["quantity"], i["unit_price"]))

                # Notify the seller of the new order.
                seller = db.query_one("SELECT seller_id FROM shops WHERE shop_id=?", (shop_id,))
                cur.execute("INSERT INTO notifications(user_id,message) VALUES(?,?)",
                            (seller["seller_id"],
                             f"New order #{order_id} received ({len(items)} item(s))."))

            # Clear the cart, deduct redeemed points, then award fresh points
            # (1 point per Rs 100) on the amount actually paid.
            cur.execute("DELETE FROM cart_items WHERE buyer_id=?", (buyer_id,))
            total_spent = sum(i["line_total"] for i in cart) - redeemed_used
            net_points = int(total_spent // 100) - redeemed_used
            cur.execute("UPDATE users SET loyalty_points = loyalty_points + ? WHERE user_id=?",
                        (net_points, buyer_id))
            detail = f"Placed {len(created)} order(s)."
            if redeemed_used:
                detail += f" Redeemed {redeemed_used} loyalty points."
            cur.execute("INSERT INTO audit_log(user_id,action,entity,details) VALUES(?,?,?,?)",
                        (buyer_id, "CHECKOUT", "orders", detail))
        msg = f"Order placed successfully! {len(created)} order(s) created."
        if redeemed_used:
            msg += f" Rs {redeemed_used:,} paid with loyalty points."
        return True, msg, created
    except Exception as e:
        # transaction() already rolled back; report cleanly.
        return False, f"Checkout failed and was rolled back: {e}", []


# ----------------------------------------------------------------- ORDER VIEWS
def buyer_orders(buyer_id):
    """Return a buyer's orders (newest first) with shop name + item count."""
    return db.query("""
        SELECT o.*, s.shop_name,
               (SELECT COUNT(*) FROM order_items WHERE order_id=o.order_id) AS item_count
          FROM orders o JOIN shops s ON s.shop_id=o.shop_id
         WHERE o.buyer_id=? ORDER BY o.placed_at DESC""", (buyer_id,))


def order_items(order_id):
    """Return the line items of an order with product names."""
    return db.query("""
        SELECT oi.*, p.name FROM order_items oi
          JOIN products p ON p.product_id=oi.product_id
         WHERE oi.order_id=?""", (order_id,))


def order_detail(order_id):
    """Return a single order header with buyer/shop/address joined."""
    row = db.query_one("""
        SELECT o.*, s.shop_name, u.full_name AS buyer_name, u.phone AS buyer_phone,
               a.line1 AS address_line, ci.name AS address_city
          FROM orders o
          JOIN shops s ON s.shop_id=o.shop_id
          JOIN users u ON u.user_id=o.buyer_id
          LEFT JOIN addresses a ON a.address_id=o.address_id
          LEFT JOIN cities ci ON ci.city_id=a.city_id
         WHERE o.order_id=?""", (order_id,))
    return dict(row) if row else None


# ----------------------------------------------------------------- LIFECYCLE
def set_order_status(order_id, status):
    """
    Change an order's status. The status-logging TRIGGER records the change
    and notifies the buyer automatically. On a genuine transition into
    'delivered', the shop and delivery-partner balances are credited exactly
    once. Safe to call with any order_id — a missing order is ignored.
    """
    o = db.query_one(
        "SELECT status, shop_id, partner_id, subtotal, discount, delivery_fee "
        "FROM orders WHERE order_id=?", (order_id,))
    if not o:
        return False
    was_delivered = (o["status"] == "delivered")
    db.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
    # Credit balances only on a real first-time transition into 'delivered'.
    if status == "delivered" and not was_delivered:
        db.execute("UPDATE shops SET balance = balance + ? WHERE shop_id=?",
                   (o["subtotal"] - o["discount"], o["shop_id"]))
        if o["partner_id"]:
            db.execute("UPDATE delivery_partners SET balance = balance + ? "
                       "WHERE partner_id=?", (o["delivery_fee"], o["partner_id"]))
    return True


def cancel_order(order_id, buyer_id):
    """Buyer cancels an order if it is still pending/accepted. Returns (ok,msg)."""
    o = db.query_one("SELECT status FROM orders WHERE order_id=? AND buyer_id=?",
                     (order_id, buyer_id))
    if not o:
        return False, "Order not found."
    if o["status"] not in ("pending", "accepted"):
        return False, "This order can no longer be cancelled."
    set_order_status(order_id, "cancelled")
    return True, "Order cancelled."


def request_return(order_id, buyer_id, reason):
    """Buyer requests a return on a delivered order (opens a dispute)."""
    o = db.query_one("SELECT status FROM orders WHERE order_id=? AND buyer_id=?",
                     (order_id, buyer_id))
    if not o or o["status"] != "delivered":
        return False, "Only delivered orders can be returned."
    with db.transaction() as cur:
        cur.execute("UPDATE orders SET status='returned' WHERE order_id=?", (order_id,))
        cur.execute("INSERT INTO disputes(order_id,raised_by,reason) VALUES(?,?,?)",
                    (order_id, buyer_id, reason))
    return True, "Return requested. Our team will review it."


# ----------------------------------------------------------------- SELLER ORDERS
def shop_orders(shop_id, status=None):
    """Return orders for a shop, optionally filtered by status."""
    sql = """SELECT o.*, u.full_name AS buyer_name,
                    (SELECT COUNT(*) FROM order_items WHERE order_id=o.order_id) AS item_count
               FROM orders o JOIN users u ON u.user_id=o.buyer_id
              WHERE o.shop_id=?"""
    params = [shop_id]
    if status:
        sql += " AND o.status=?"; params.append(status)
    sql += " ORDER BY o.placed_at DESC"
    return db.query(sql, tuple(params))


def shop_messages(shop_id, limit=100):
    """Customer inquiries sent to a shop, newest first, with the buyer's name."""
    return db.query("""
        SELECT m.message_id, m.body, m.created_at, u.user_id AS buyer_id,
               u.full_name AS buyer_name, u.email AS buyer_email
          FROM messages m
          JOIN users u ON u.user_id = m.buyer_id
         WHERE m.shop_id = ?
         ORDER BY m.created_at DESC
         LIMIT ?
    """, (shop_id, limit))
