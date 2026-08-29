"""
database/seed.py
================================================================================
Populates the database with a large, realistic, deterministic Pakistani dataset
so every analytics chart, table and statistics screen looks completely full:

  * 12 cities, 14 categories
  * 14 shops (one verified/unverified seller each) across the country
  * 40 buyers, 12 delivery partners, 1 admin
  * ~190 products across 14 categories with realistic PKR pricing, flash sales
    (with real expiry timestamps for live countdowns), stock levels and views
  * ~280 orders spanning ~120 days and every order status, with line items,
    a realistic distribution of reviews, coupons, notifications, disputes,
    payouts, referrals, shop messages, announcements and JSON activity logs

The data is generated deterministically (fixed random seed) so the dashboards
look identical and full on every machine.  Seeding runs only once — `main.py`
checks whether the database is already populated before calling `seed()`.
================================================================================
"""

import json
import random
from datetime import datetime, timedelta

from database.db_manager import db
from utils.security import hash_password

random.seed(220)  # deterministic dataset every run

NOW = datetime.now()

# ----------------------------------------------------------------------------
# Static reference data
# ----------------------------------------------------------------------------
CITIES = [
    ("Karachi", "Sindh"), ("Lahore", "Punjab"), ("Islamabad", "Capital"),
    ("Rawalpindi", "Punjab"), ("Peshawar", "KPK"), ("Quetta", "Balochistan"),
    ("Faisalabad", "Punjab"), ("Multan", "Punjab"), ("Sialkot", "Punjab"),
    ("Hyderabad", "Sindh"), ("Gujranwala", "Punjab"), ("Abbottabad", "KPK"),
]

CATEGORIES = [
    ("Electronics", "💻"), ("Clothing", "👕"), ("Food", "🍱"), ("Books", "📚"),
    ("Home Goods", "🏠"), ("Beauty", "💄"), ("Sports", "🏏"), ("Toys", "🧸"),
    ("Handicrafts", "🎨"), ("Mobile Accessories", "🔌"), ("Groceries", "🛒"),
    ("Stationery", "✏️"), ("Health", "💊"), ("Automotive", "🚗"),
]

# (shop_name, seller_full_name, banner_color, city)
SHOPS = [
    ("Karachi Tech Hub",      "Bilal Ahmed",   "#4f46e5", "Karachi"),
    ("Lahore Fashion House",  "Ayesha Khan",   "#ef4444", "Lahore"),
    ("Capital Mart",          "Usman Tariq",   "#10b981", "Islamabad"),
    ("Pindi General Store",   "Fatima Noor",   "#f59e0b", "Rawalpindi"),
    ("Khyber Handicrafts",    "Imran Gul",     "#8b5cf6", "Peshawar"),
    ("Quetta Sports Corner",  "Sana Baloch",   "#0ea5e9", "Quetta"),
    ("Faisalabad Textiles",   "Hamza Sheikh",  "#fb7185", "Faisalabad"),
    ("Multan Sweets & More",  "Zara Iqbal",    "#14b8a6", "Multan"),
    ("Sialkot Sports Gear",   "Bilal Butt",    "#6366f1", "Sialkot"),
    ("Hyderabad Bazaar",      "Nadia Memon",   "#ec4899", "Hyderabad"),
    ("Gujranwala Electronics","Asad Mahmood",  "#0284c7", "Gujranwala"),
    ("Hilltop Organics",      "Maria Yousaf",  "#059669", "Abbottabad"),
    ("Metro Mobile World",    "Kamran Aziz",   "#7c3aed", "Karachi"),
    ("Royal Home Decor",      "Sadia Anwar",   "#d97706", "Lahore"),
]

# Product name pools per category; price ranges in PKR (lo, hi).
PRODUCTS_BY_CAT = {
    "Electronics": [
        ("Dawlance LED TV 32\"", 42000, 55000), ("Haier Microwave Oven", 18000, 25000),
        ("PEL Air Cooler", 22000, 30000), ("Audionic Bluetooth Speaker", 3500, 6000),
        ("Power Bank 20000mAh", 2500, 4500), ("Wireless Mouse", 900, 1800),
        ("LED Study Lamp", 1200, 2200), ("Electric Kettle", 2800, 4000),
        ("Orient Washing Machine", 28000, 45000), ("Smart Watch Fitness", 4500, 9000),
    ],
    "Clothing": [
        ("Khaadi Lawn 3-Piece", 4500, 8500), ("Gul Ahmed Kurta", 2200, 4500),
        ("Bonanza Sweater", 1800, 3500), ("Cotton Shalwar Kameez", 2500, 5000),
        ("Embroidered Dupatta", 800, 2000), ("Denim Jeans", 2000, 4000),
        ("Pashmina Shawl", 3500, 7000), ("Kids Frock", 1200, 2500),
        ("Waistcoat Formal", 3000, 6000), ("Sports Tracksuit", 2800, 5500),
    ],
    "Food": [
        ("Basmati Rice 5kg", 1800, 2600), ("Pure Desi Ghee 1kg", 1400, 2200),
        ("Sohan Halwa Box", 900, 1800), ("Dry Fruits Mix 1kg", 2200, 3800),
        ("Honey 1kg Pure", 1500, 2800), ("Chapli Kebab Pack", 800, 1500),
        ("Mango Pickle Jar", 350, 700), ("Green Tea 250g", 600, 1100),
        ("Multani Sohan", 1100, 2000), ("Dates Ajwa 500g", 1800, 3500),
    ],
    "Books": [
        ("Urdu Novel Collection", 800, 1600), ("CSS Guide Book", 1200, 2200),
        ("Children Story Set", 600, 1200), ("Islamic Studies Book", 400, 900),
        ("English Grammar Book", 500, 1000), ("Mathematics Reference", 900, 1700),
        ("Poetry Diwan", 700, 1400), ("History of Pakistan", 850, 1600),
        ("Programming in Python", 1500, 2800), ("Competitive Exam Set", 1800, 3200),
    ],
    "Home Goods": [
        ("Cotton Bed Sheet Set", 2500, 4500), ("Steel Cookware Set", 5500, 9000),
        ("Wall Clock Decorative", 1200, 2400), ("Prayer Mat Velvet", 900, 1800),
        ("Curtain Pair", 1800, 3500), ("Dinner Set 32pcs", 4000, 7500),
        ("Storage Organizer", 1100, 2200), ("Floor Cushion", 1300, 2600),
        ("LED Ceiling Light", 2200, 4200), ("Non-stick Tawa", 1400, 2800),
    ],
    "Beauty": [
        ("Saeed Ghani Rose Water", 350, 700), ("Herbal Face Wash", 450, 900),
        ("Kajal Surma Set", 300, 650), ("Hair Oil Amla", 400, 800),
        ("Lipstick Matte", 600, 1200), ("Sunblock SPF50", 800, 1600),
        ("Mehndi Cone Pack", 200, 500), ("Perfume Attar", 1200, 2800),
        ("Facial Kit Whitening", 1500, 3000), ("Beard Oil Organic", 700, 1400),
    ],
    "Sports": [
        ("Cricket Bat English Willow", 8000, 18000), ("Football Size 5", 1500, 3000),
        ("Badminton Racket Pair", 2200, 4500), ("Yoga Mat", 1200, 2400),
        ("Cricket Ball Leather", 600, 1400), ("Gym Gloves", 800, 1600),
        ("Skipping Rope", 350, 700), ("Table Tennis Set", 1800, 3500),
        ("Dumbbell Set 10kg", 4000, 8000), ("Hockey Stick Pro", 2500, 5500),
    ],
    "Toys": [
        ("Remote Control Car", 2500, 5000), ("Building Blocks Set", 1500, 3000),
        ("Soft Teddy Bear", 1200, 2400), ("Puzzle 500pcs", 800, 1600),
        ("Doll House", 3500, 6500), ("Toy Train Set", 2200, 4200),
        ("Action Figure", 900, 1800), ("Educational Tablet Toy", 2800, 5200),
        ("Nerf Blaster", 2000, 4000), ("Board Game Family", 1500, 3000),
    ],
    "Handicrafts": [
        ("Truck Art Frame", 1800, 3800), ("Blue Pottery Vase", 2200, 4500),
        ("Camel Skin Lamp", 2500, 5000), ("Hand-knotted Rug", 8000, 18000),
        ("Brass Decor Piece", 1500, 3200), ("Wooden Jewelry Box", 1200, 2600),
        ("Embroidered Wall Hanging", 1600, 3400), ("Clay Tea Set", 1100, 2400),
        ("Multani Khussa", 1800, 3600), ("Ralli Quilt Handmade", 3500, 7000),
    ],
    "Mobile Accessories": [
        ("Phone Case Premium", 500, 1200), ("Tempered Glass Protector", 300, 700),
        ("Fast Charger Type-C", 800, 1800), ("Earbuds Wireless", 1800, 3800),
        ("Phone Stand Holder", 400, 900), ("USB Cable Braided", 350, 800),
        ("Car Phone Mount", 600, 1400), ("Selfie Ring Light", 1100, 2400),
        ("Bluetooth Neckband", 1500, 3200), ("Memory Card 128GB", 2000, 3800),
    ],
    "Groceries": [
        ("Sugar 10kg Bag", 1300, 1900), ("Cooking Oil 5L", 2400, 3600),
        ("Wheat Flour 20kg", 2200, 3200), ("Red Chilli Powder 1kg", 700, 1300),
        ("Tea Whole Leaf 1kg", 1400, 2400), ("Lentils Mix 5kg", 1600, 2600),
        ("Salt Pack 2kg", 150, 350), ("Spice Box Combo", 900, 1800),
    ],
    "Stationery": [
        ("A4 Paper Ream", 900, 1500), ("Ball Pen Box 50", 600, 1100),
        ("Notebook Pack 5", 500, 1000), ("Geometry Box Set", 400, 900),
        ("Sticky Notes Combo", 300, 700), ("Office Files 20pcs", 800, 1600),
        ("Marker Set 12", 600, 1300), ("School Bag", 1800, 3500),
    ],
    "Health": [
        ("Vitamin C Tablets", 600, 1300), ("Digital BP Monitor", 3500, 6500),
        ("First Aid Kit", 1200, 2400), ("Protein Powder 1kg", 4500, 8500),
        ("Hand Sanitizer 500ml", 300, 700), ("Thermometer Digital", 700, 1500),
        ("Face Mask Box 50", 400, 900), ("Omega-3 Capsules", 1500, 3000),
    ],
    "Automotive": [
        ("Car Vacuum Cleaner", 2500, 5000), ("Engine Oil 4L", 3000, 5500),
        ("Microfiber Cloth Pack", 500, 1100), ("Car Seat Cover Set", 4500, 9000),
        ("Dashboard Camera", 5500, 12000), ("Tyre Inflator Portable", 3500, 7000),
        ("Car Air Freshener", 250, 600), ("LED Headlight Pair", 3000, 6500),
    ],
}

BUYER_NAMES = [
    "Ahmed Raza", "Mariam Aslam", "Bilawal Hussain", "Hina Malik", "Saad Qureshi",
    "Nimra Javed", "Talha Mehmood", "Komal Shah", "Faizan Ali", "Areeba Siddiqui",
    "Daniyal Khan", "Rabia Yousaf", "Hassan Raza", "Iqra Naseem", "Owais Akhtar",
    "Sana Tariq", "Zeeshan Haider", "Mahnoor Fatima", "Arsalan Bhatti", "Laiba Saeed",
    "Hamza Yusuf", "Aiman Riaz", "Shahzaib Anwar", "Noor ul Ain", "Junaid Aslam",
    "Sidra Kausar", "Waleed Farooq", "Anaya Pervaiz", "Bilal Saleem", "Mehwish Iqbal",
    "Taimoor Khan", "Hooria Naveed", "Saif Ullah", "Marwa Hassan", "Zain Abbas",
    "Fariha Latif", "Usama Ghani", "Eman Shahid", "Rohaan Malik", "Aleena Tariq",
]

PARTNER_NAMES = [
    ("Junaid Rider", "Bike", "KHI-1234"), ("Naveed Express", "Bike", "LHR-5678"),
    ("Kashif Speedy", "Car", "ISB-9012"), ("Rashid Wheels", "Bike", "RWP-3456"),
    ("Adnan Cargo", "Van", "PEW-7890"), ("Shoaib Quick", "Bike", "QTA-2345"),
    ("Yasir Swift", "Bike", "FSD-6701"), ("Imtiaz Fast", "Car", "MUL-8842"),
    ("Wajid Dash", "Bike", "SKT-1199"), ("Faraz Motion", "Van", "HYD-5521"),
    ("Tariq Bolt", "Bike", "GUJ-3390"), ("Sajid Trail", "Car", "ABT-7764"),
]

REVIEW_COMMENTS = [
    "Excellent quality, highly recommended!", "Fast delivery, good packaging.",
    "Value for money. Will buy again.", "Product as described. Satisfied.",
    "Good but delivery was a bit slow.", "Amazing! Exceeded expectations.",
    "Decent product for the price.", "Loved it, thank you!",
    "Quality could be better.", "Perfect, exactly what I needed.",
    "Genuine product, trustworthy seller.", "Packaging was premium. Impressed.",
    "Works flawlessly, five stars.", "Slightly different from picture but okay.",
    "Best purchase this month!",
]

MESSAGE_BODIES = [
    "Is this product available in other colours?",
    "Can you deliver to my city by the weekend?",
    "Do you offer any discount on bulk orders?",
    "Thank you, the order arrived in perfect condition!",
    "Is the warranty included with this item?",
    "Please confirm the stock availability.",
]


def _city_map():
    return {r["name"]: r["city_id"] for r in db.query("SELECT * FROM cities")}


def _ts(days_ago, spread_hours=23):
    """A timestamp `days_ago` days back at a random hour."""
    return (NOW - timedelta(days=days_ago,
                            hours=random.randint(0, spread_hours),
                            minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")


def seed():
    """Populate the database. Should only be called on a fresh, empty DB."""
    # -- cities & categories ------------------------------------------------
    db.executemany("INSERT INTO cities(name, province) VALUES (?,?)", CITIES)
    cmap = _city_map()
    db.executemany("INSERT INTO categories(name, icon) VALUES (?,?)", CATEGORIES)
    catmap = {r["name"]: r["category_id"] for r in db.query("SELECT * FROM categories")}

    pw = hash_password("password")  # every demo account uses 'password'

    # -- admin (created earliest so growth chart has history) ---------------
    db.execute(
        "INSERT INTO users(full_name,email,phone,password_hash,role,city_id,"
        "loyalty_points,created_at) VALUES(?,?,?,?,?,?,?,?)",
        ("Mustafa Shahid", "admin@bazaar.pk", "03001112233", pw, "admin",
         cmap["Islamabad"], 0, _ts(150)))

    # -- sellers + shops ----------------------------------------------------
    shop_ids = []  # (shop_id, city, seller_id)
    for shop_name, seller_name, color, city in SHOPS:
        email = seller_name.lower().replace(" ", ".") + "@seller.pk"
        seller_id = db.execute(
            "INSERT INTO users(full_name,email,phone,password_hash,role,city_id,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (seller_name, email, "0300" + str(random.randint(1000000, 9999999)),
             pw, "seller", cmap[city], _ts(random.randint(90, 140))))
        verified = 1 if random.random() > 0.28 else 0
        shop_id = db.execute(
            "INSERT INTO shops(seller_id,shop_name,description,banner_color,city_id,"
            "is_verified,created_at) VALUES(?,?,?,?,?,?,?)",
            (seller_id, shop_name,
             f"Your trusted source for quality products in {city}. "
             f"Serving customers nationwide with the best deals since 2021.",
             color, cmap[city], verified, _ts(random.randint(90, 140))))
        shop_ids.append((shop_id, city, seller_id))

    # -- products -----------------------------------------------------------
    product_pool = []  # (product_id, price, shop_id)
    cat_names = [c[0] for c in CATEGORIES]
    flash_count = 0
    for i in range(len(cat_names) * 14):          # ~196 products
        cat = cat_names[i % len(cat_names)]
        # Random shop (deterministic via the seeded RNG) so every shop carries a
        # varied mix of categories rather than a single one.
        shop_id, city, _sid = random.choice(shop_ids)
        pool = PRODUCTS_BY_CAT[cat]
        name, lo, hi = pool[(i // len(cat_names)) % len(pool)]
        price = random.randint(lo, hi)
        stock = random.choice([0, 2, 3, 4, 5, 8, 12, 18, 25, 35, 50, 70, 90])
        is_flash = 1 if (random.random() < 0.16 and flash_count < 24) else 0
        flash_price = round(price * random.uniform(0.65, 0.85)) if is_flash else None
        flash_ends = None
        if is_flash:
            flash_count += 1
            # Flash ends a few hours to a couple of days out → live countdowns.
            flash_ends = (NOW + timedelta(hours=random.randint(4, 52),
                                          minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
        status = "approved"
        r = random.random()
        if r < 0.05:
            status = "pending"
        elif r < 0.075:
            status = "flagged"
        views = random.randint(5, 800)
        pid = db.execute(
            "INSERT INTO products(shop_id,category_id,name,description,price,stock,"
            "low_stock_at,status,is_flash,flash_price,flash_ends_at,views,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (shop_id, catmap[cat], name,
             f"High quality {name} available now. Authentic product with warranty. "
             f"Sourced from trusted suppliers and delivered across Pakistan.",
             price, stock, random.choice([3, 5, 5, 8]), status, is_flash,
             flash_price, flash_ends, views, _ts(random.randint(30, 120))))
        if status == "approved":
            product_pool.append((pid, price, shop_id))

    # -- buyers + addresses (1-2 each) --------------------------------------
    buyer_ids = []
    for idx, name in enumerate(BUYER_NAMES):
        email = name.lower().replace(" ", ".") + "@buyer.pk"
        city = random.choice([c[0] for c in CITIES])
        bid = db.execute(
            "INSERT INTO users(full_name,email,phone,password_hash,role,city_id,"
            "loyalty_points,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (name, email, "0301" + str(random.randint(1000000, 9999999)),
             pw, "buyer", cmap[city], random.randint(0, 650),
             _ts(random.randint(5, 130))))
        db.execute(
            "INSERT INTO addresses(user_id,label,line1,city_id,is_default) VALUES(?,?,?,?,1)",
            (bid, "Home", f"House {random.randint(1,500)}, Street {random.randint(1,40)}",
             cmap[city]))
        if random.random() < 0.4:                 # some buyers add a work address
            c2 = random.choice([c[0] for c in CITIES])
            db.execute(
                "INSERT INTO addresses(user_id,label,line1,city_id,is_default) VALUES(?,?,?,?,0)",
                (bid, "Office", f"Office {random.randint(1,90)}, Block {random.choice('ABCDE')}",
                 cmap[c2]))
        buyer_ids.append(bid)

    # -- delivery partners --------------------------------------------------
    partner_ids = []
    for pname, vtype, plate in PARTNER_NAMES:
        email = pname.lower().replace(" ", ".") + "@rider.pk"
        city = random.choice([c[0] for c in CITIES])
        uid = db.execute(
            "INSERT INTO users(full_name,email,phone,password_hash,role,city_id,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (pname, email, "0302" + str(random.randint(1000000, 9999999)),
             pw, "delivery", cmap[city], _ts(random.randint(60, 130))))
        pid = db.execute(
            "INSERT INTO delivery_partners(user_id,vehicle_type,vehicle_plate,zone_city_id,"
            "rating,balance) VALUES(?,?,?,?,?,?)",
            (uid, vtype, plate, cmap[city], round(random.uniform(4.1, 5.0), 1),
             round(random.uniform(0, 12000), 0)))
        partner_ids.append((pid, cmap[city]))

    # -- coupons ------------------------------------------------------------
    db.executemany(
        "INSERT INTO coupons(code,discount_pct,shop_id,min_amount,is_active) VALUES(?,?,?,?,?)",
        [("EID2026", 15, None, 2000, 1), ("WELCOME10", 10, None, 0, 1),
         ("BAZAAR20", 20, None, 5000, 1), ("FREESHIP", 12, None, 1500, 1),
         ("SALE25", 25, shop_ids[0][0], 3000, 1), ("AZADI14", 14, None, 1000, 1),
         ("MEGA30", 30, None, 8000, 1), ("NEWUSER", 18, None, 500, 0)])
    coupon_ids = [r["coupon_id"] for r in db.query("SELECT coupon_id FROM coupons WHERE is_active=1")]

    # -- orders (~280) across ~120 days, every status -----------------------
    status_pool = (["delivered"] * 150 + ["pending"] * 22 + ["accepted"] * 18 +
                   ["assigned"] * 14 + ["picked_up"] * 12 + ["in_transit"] * 14 +
                   ["cancelled"] * 16 + ["returned"] * 10 + ["rejected"] * 10)
    random.shuffle(status_pool)
    n_orders = len(status_pool)

    for i in range(n_orders):
        buyer_id = random.choice(buyer_ids)
        shop_id, scity, _sid = random.choice(shop_ids)
        shop_products = [p for p in product_pool if p[2] == shop_id]
        if not shop_products:
            continue
        chosen = random.sample(shop_products, k=min(len(shop_products), random.randint(1, 4)))
        status = status_pool[i]
        placed = _ts(random.randint(0, 118))
        addr = db.query_one("SELECT address_id FROM addresses WHERE user_id=? AND is_default=1",
                            (buyer_id,))
        # Assign a partner (preferably one whose zone matches the shop city).
        partner_id = None
        if status in ("assigned", "picked_up", "in_transit", "delivered"):
            zone_matches = [p for p, z in partner_ids if z == cmap[scity]]
            partner_id = random.choice(zone_matches) if zone_matches else random.choice(partner_ids)[0]
        coupon_id = random.choice(coupon_ids) if random.random() < 0.32 else None

        subtotal, items = 0, []
        for pid, price, _ in chosen:
            qty = random.randint(1, 3)
            subtotal += price * qty
            items.append((pid, qty, price))
        # Use the real coupon's discount percentage if one was applied.
        disc_pct = 0
        if coupon_id:
            cp = db.query_one("SELECT discount_pct,min_amount FROM coupons WHERE coupon_id=?", (coupon_id,))
            if cp and subtotal >= cp["min_amount"]:
                disc_pct = cp["discount_pct"]
            else:
                coupon_id = None
        discount = round(subtotal * disc_pct / 100)
        delivery_fee = random.choice([120, 150, 150, 180, 200])
        total = subtotal - discount + delivery_fee

        order_id = db.execute(
            "INSERT INTO orders(buyer_id,shop_id,partner_id,address_id,coupon_id,"
            "subtotal,discount,delivery_fee,total,status,placed_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (buyer_id, shop_id, partner_id, addr["address_id"] if addr else None,
             coupon_id, subtotal, discount, delivery_fee, total, status, placed))

        for pid, qty, price in items:
            # Pre-add qty so the AFTER-INSERT stock-decrement trigger leaves the
            # curated stock unchanged (and never goes negative) for a clean demo.
            db.execute("UPDATE products SET stock = stock + ? WHERE product_id=?", (qty, pid))
            db.execute("INSERT INTO order_items(order_id,product_id,quantity,unit_price)"
                       " VALUES(?,?,?,?)", (order_id, pid, qty, price))

        if status == "delivered":
            db.execute("UPDATE shops SET balance = balance + ? WHERE shop_id=?",
                       (subtotal - discount, shop_id))
            # Mirror the loyalty the delivered-trigger would grant (seed inserts
            # directly as 'delivered', so we add it explicitly here).
            db.execute("UPDATE users SET loyalty_points = loyalty_points + ? WHERE user_id=?",
                       (int(total // 100), buyer_id))

    # -- reviews (≈65% of delivered buyer/product pairs) --------------------
    delivered_pairs = db.query(
        "SELECT DISTINCT oi.product_id, o.buyer_id "
        "FROM orders o JOIN order_items oi ON oi.order_id=o.order_id "
        "WHERE o.status='delivered'")
    seen = set()
    for row in delivered_pairs:
        key = (row["product_id"], row["buyer_id"])
        if key in seen or random.random() < 0.35:
            continue
        seen.add(key)
        db.execute(
            "INSERT INTO reviews(product_id,buyer_id,rating,comment,created_at) VALUES(?,?,?,?,?)",
            (row["product_id"], row["buyer_id"],
             random.choices([5, 4, 3, 2, 1], weights=[48, 30, 13, 6, 3])[0],
             random.choice(REVIEW_COMMENTS), _ts(random.randint(0, 60))))

    # -- demo cart (populate the primary demo buyer's cart so the cart page,
    #    coupon and loyalty-redemption flow look complete out of the box) ----
    demo = db.query_one("SELECT user_id FROM users WHERE email='ahmed.raza@buyer.pk'")
    if demo:
        in_stock = [p for p in product_pool
                    if db.query_one("SELECT stock FROM products WHERE product_id=?",
                                    (p[0],))["stock"] > 3]
        for pid, _price, _shop in random.sample(in_stock, k=min(4, len(in_stock))):
            try:
                db.execute("INSERT INTO cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)",
                           (demo["user_id"], pid, random.randint(1, 2)))
            except Exception:
                pass

    # -- wishlist -----------------------------------------------------------
    for bid in buyer_ids:
        for pid, _, _ in random.sample(product_pool, k=random.randint(0, 6)):
            try:
                db.execute("INSERT INTO wishlist(buyer_id,product_id) VALUES(?,?)", (bid, pid))
            except Exception:
                pass

    # -- referrals (drives leaderboard + loyalty rewards) -------------------
    referrer_pool = random.sample(buyer_ids, k=12)
    referred_pool = [b for b in buyer_ids if b not in referrer_pool]
    for ref in referrer_pool:
        for _ in range(random.randint(1, 4)):
            if not referred_pool:
                break
            target = referred_pool.pop()
            db.execute(
                "INSERT INTO referrals(referrer_id,referred_id,reward_points,created_at) VALUES(?,?,?,?)",
                (ref, target, random.choice([100, 100, 150, 200]), _ts(random.randint(1, 90))))
            # Credit the referrer (seed inserts directly, mirroring the trigger).
            db.execute("UPDATE users SET loyalty_points = loyalty_points + 100 WHERE user_id=?", (ref,))

    # -- shop messages ------------------------------------------------------
    for _ in range(40):
        shop_id = random.choice([s[0] for s in shop_ids])
        buyer_id = random.choice(buyer_ids)
        db.execute("INSERT INTO messages(shop_id,buyer_id,body,created_at) VALUES(?,?,?,?)",
                   (shop_id, buyer_id, random.choice(MESSAGE_BODIES), _ts(random.randint(0, 40))))

    # -- announcements ------------------------------------------------------
    db.executemany(
        "INSERT INTO announcements(title,body,created_at) VALUES(?,?,?)",
        [("Eid Sale Live!", "Enjoy up to 30% off across all categories this Eid. Use code EID2026.", _ts(8)),
         ("New Sellers Onboarded", "We welcomed 14 verified sellers across Pakistan this season.", _ts(20)),
         ("Faster Delivery", "Average delivery time reduced to 2 days in major cities.", _ts(33)),
         ("Loyalty Programme Upgraded", "Earn 1 point per Rs.100 spent and redeem at checkout.", _ts(45)),
         ("Independence Day Deals", "Celebrate Azadi with code AZADI14 — 14% off platform-wide.", _ts(60))])

    # -- disputes (on returned/delivered orders) ----------------------------
    dispute_orders = db.query(
        "SELECT order_id, buyer_id FROM orders WHERE status IN ('returned','delivered') "
        "ORDER BY RANDOM() LIMIT 7")
    reasons = ["Item arrived damaged, requesting refund.",
               "Wrong product delivered.", "Item not as described.",
               "Late delivery, requesting partial refund.",
               "Missing item from the order.", "Product stopped working after a day.",
               "Quality issue, requesting replacement."]
    for o, reason in zip(dispute_orders, reasons):
        st = random.choice(["open", "open", "resolved", "rejected"])
        db.execute("INSERT INTO disputes(order_id,raised_by,reason,status,created_at) VALUES(?,?,?,?,?)",
                   (o["order_id"], o["buyer_id"], reason, st, _ts(random.randint(1, 40))))

    # -- payouts (sellers + partners, mixed statuses) -----------------------
    payout_users = db.query("SELECT user_id FROM users WHERE role IN ('seller','delivery') "
                            "ORDER BY RANDOM() LIMIT 9")
    for u in payout_users:
        st = random.choice(["pending", "pending", "approved", "rejected"])
        db.execute("INSERT INTO payouts(user_id,amount,status,requested_at) VALUES(?,?,?,?)",
                   (u["user_id"], round(random.uniform(4000, 30000), 0), st, _ts(random.randint(1, 35))))

    # -- NoSQL activity log (JSON documents) --------------------------------
    cities_list = [c[0] for c in CITIES]
    sample_products = ["Cricket Bat English Willow", "Khaadi Lawn 3-Piece",
                       "Audionic Bluetooth Speaker", "Pure Desi Ghee 1kg",
                       "Smart Watch Fitness", "Earbuds Wireless"]
    event_builders = [
        lambda: {"event": "login", "role": random.choice(["buyer", "seller", "delivery"]),
                 "ip": f"39.40.{random.randint(1,255)}.{random.randint(1,255)}"},
        lambda: {"event": "product_view", "product": random.choice(sample_products),
                 "category": random.choice(cat_names)},
        lambda: {"event": "search", "term": random.choice(["lawn suit", "cricket bat",
                 "earbuds", "ghee", "smart watch"]), "results": random.randint(0, 18)},
        lambda: {"event": "checkout", "amount_pkr": random.randint(800, 25000),
                 "items": random.randint(1, 5)},
        lambda: {"event": "coupon_applied", "code": random.choice(["EID2026", "BAZAAR20", "AZADI14"]),
                 "discount_pct": random.choice([10, 15, 20, 25])},
        lambda: {"event": "review_posted", "stars": random.randint(1, 5)},
        lambda: {"event": "wishlist_add", "product": random.choice(sample_products)},
        lambda: {"event": "filter_used", "by": random.choice(["city", "category", "price"]),
                 "value": random.choice(cities_list)},
        lambda: {"event": "referral", "reward_points": 100},
        lambda: {"event": "payout_request", "amount_pkr": random.randint(5000, 30000)},
    ]
    for _ in range(36):
        doc = random.choice(event_builders)()
        db.execute("INSERT INTO activity_log(doc,created_at) VALUES(?,?)",
                   (json.dumps(doc), _ts(random.randint(0, 30))))

    # -- audit log ----------------------------------------------------------
    db.execute("INSERT INTO audit_log(user_id,action,entity,details) VALUES(?,?,?,?)",
               (1, "SEED", "system", "Initial dataset generated."))
    for _ in range(15):
        act = random.choice(["APPROVE_PRODUCT", "RESOLVE_DISPUTE", "APPROVE_PAYOUT",
                             "DEACTIVATE_USER", "ADD_COUPON", "ADD_ANNOUNCEMENT"])
        db.execute("INSERT INTO audit_log(user_id,action,entity,details,created_at) VALUES(?,?,?,?,?)",
                   (1, act, "admin", f"Admin performed {act.lower().replace('_',' ')}.",
                    _ts(random.randint(0, 40))))


if __name__ == "__main__":
    db.initialize_schema()
    if not db.table_has_rows("users"):
        seed()
        print("Seed complete.")
    else:
        print("Database already populated.")
