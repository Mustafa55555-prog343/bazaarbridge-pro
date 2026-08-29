# BazaarBridge Pro

A complete digital marketplace desktop application for Pakistan, built for
**CS-220 Database Systems**, NUST SEECS.

**Student:** Mustafa Shahid &nbsp;|&nbsp; **Class:** BSCS-14B &nbsp;|&nbsp; **CMS ID:** 500889

Built with **Python + ttkbootstrap + SQLite**. Four full role dashboards
(Buyer, Seller, Delivery Partner, Admin) with live full-text search, a shopping
cart, transactional checkout, loyalty points, order tracking, embedded analytics
charts, product moderation, payouts, disputes, coupons, referrals, a platform
health monitor, a NoSQL JSON activity log, and CSV/JSON/XML export.

---

## How to run (Windows 11, Python 3.10+)

Open a terminal in this folder and run:

```bash
pip install -r requirements.txt
python main.py
```

That's it. The database is created and filled with a large sample dataset
automatically on the first launch. No other setup is needed.

> `tkinter` ships with the standard Python installer on Windows, so it does
> not appear in `requirements.txt`.

---

## Demo logins

Every account uses the password: **password**

| Role             | Email                      |
|------------------|----------------------------|
| Admin            | `admin@bazaar.pk`          |
| Seller           | `bilal.ahmed@seller.pk`    |
| Buyer            | `ahmed.raza@buyer.pk`      |
| Delivery Partner | `junaid.rider@rider.pk`    |

You can also register a brand-new account from the login screen.

---

## Headline features

**Buyer** — full-text product browse with filters, flash sales with **live
countdown timers**, personalised recommendations, side-by-side product
comparison (up to 3), a cart with coupons **and loyalty-point redemption at
checkout**, multiple saved addresses with a default selector, order tracking,
wishlist, **personal spending analytics** (charts by month and category),
and disputes.

**Seller** — shop scorecard, product management, **bulk order management**
(accept/assign in one click), inventory with low-stock view, sales analytics,
flash-sale + coupon creation, reviews, a **customer messages inbox**
with reply, and payout requests.

**Delivery Partner** — claimable order pool by zone, active-delivery workflow,
earnings, history and vehicle/zone management.

**Admin** — platform analytics (six charts + revenue forecast) with **advanced
filters by date range, city and category**, a **Platform Health dashboard**
(system statistics + database footprint), user management, product/review
moderation, transactions with CSV/JSON/XML export, a NoSQL activity log,
dispute resolution, payout approval, announcements, coupons, and a referral
leaderboard.

**All roles** — a **notification center** with a live unread badge on the
header bell.

---

## Project layout

```
BazaarBridgePro/
├── main.py              # launch point
├── requirements.txt
├── database/            # schema.sql, db manager, seed data, SQLite file
├── models/              # data access + business logic ("stored procedures")
├── views/               # login screen, 4 dashboards, shared UI components, charts
├── utils/               # theming, validation, security, CSV/JSON/XML exporters
└── controllers/
```

---

## Database concepts demonstrated (CS-220)

- **3NF schema** with foreign keys and CHECK constraints for domain integrity.
- **12 triggers** — stock auto-decrement, low-stock alerts, order-status
  logging + buyer notifications, review/shop rating averaging, loyalty-point
  award on delivery, referral rewards, automatic flagging of poorly-rated
  products, and full-text-search synchronisation.
- **13 reporting views** — product/shop/seller performance, daily & monthly
  revenue, category & city breakdowns, top buyers, partner performance,
  low-stock, dispute summary, referral leaderboard, and user growth.
- **Transactions** with commit/rollback at checkout (atomic, multi-shop,
  oversell-safe, with loyalty redemption applied inside the transaction).
- **Complex queries** — multi-table joins, correlated subqueries, dynamic
  parameterised analytics filters.
- **Full-text search (FTS5)** on products, kept in sync by triggers.
- **NoSQL / document storage** — a JSON activity log queried with SQLite's
  JSON1 extension.
- **Query-level role-based access control** across the four roles.
- **Indexes** on the hottest join/filter paths.

---

## Sample dataset (auto-seeded, deterministic)

12 cities · 14 categories · 14 shops · 67 users (1 admin, 14 sellers,
40 buyers, 12 delivery partners) · 196 products (23 live flash sales) ·
266 orders across every status · 668 order items · 209 reviews · 25 referrals ·
coupons, disputes, payouts, announcements, messages, notifications and a NoSQL
activity log — so every chart, table and statistics screen looks full.
