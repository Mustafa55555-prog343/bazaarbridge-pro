# BazaarBridge Pro

**Pakistan's Local Marketplace — A Desktop Marketplace Platform**

A complete desktop marketplace application connecting four types of users — buyers, sellers, delivery partners, and an admin — through role-based dashboards covering the entire life of an order, from a buyer clicking "Add to Cart" to a rider marking the parcel delivered and the seller getting paid.

Built as the semester project for **CS-220 (Database Systems)**, School of Electrical Engineering & Computer Science (SEECS), NUST.

## Overview

The application is a native Windows desktop program written in Python. It runs with **zero setup**: no server, no internet connection, no configuration. On first launch it creates and seeds its own SQLite database automatically.

```bash
pip install -r requirements.txt
python main.py
```

| | |
|---|---|
| **Roles** | Buyer · Seller · Delivery Partner · Admin |
| **Pages** | 39 fully working pages across 4 dashboards |
| **Database** | SQLite, 22 tables (3NF) |
| **Tests** | Automated harness covering all 39 pages and ~70 model operations |

## Why It Was Built This Way

The goal was to demonstrate database concepts inside a realistic system rather than isolated exercises. A marketplace naturally produces many related entities (users, shops, products, orders, reviews, payouts), real transactional requirements (checkout must decrement stock and create orders atomically), and real reporting needs (revenue analytics, top sellers, city-wise demand).

Every headline database concept from the course — normalization, keys and constraints, joins, views, triggers, indexes, transactions, full-text search, and even NoSQL-style JSON documents — has a concrete, visible job somewhere in the application.

## Design Principles

- **Zero-setup reliability** — the database is created and seeded automatically on first launch
- **Strict layering** — GUI code never contains SQL; all queries live in a models layer, so the same functions power every screen and can be tested independently
- **Graceful failure** — every risky operation is guarded; a global exception handler converts unexpected errors into friendly messages instead of raw tracebacks
- **Professional visual design** — a consistent navy/indigo design system, gradient stat cards, zebra-striped tables, and themed charts

## Architecture

The codebase is organized into three strict layers:
Presentation Layer (views/)
↓ draws windows, reacts to clicks
Business Logic Layer (models/)
↓ every SQL statement and business rule
Database Layer (database/db_manager.py)
owns the SQLite connection, enforces foreign keys, provides transactions

This separation means every model function can be tested headlessly, without the GUI.

## The Four Dashboards

All four dashboards share one skeleton — a dark sidebar, a header with live notifications, and a scrollable content area — but each exposes only what its role is allowed to do.

**Buyer (10 pages)** — product browsing with FTS5 search and filters, flash sales, personalized recommendations, product comparison, cart with coupons and loyalty-point redemption, transactional checkout, order tracking, spending analytics, profile management

**Seller (10 pages)** — shop overview with revenue KPIs, full product CRUD, bulk inventory editing with low-stock warnings, order fulfillment, sales analytics, promotions and coupons, buyer messaging, payout requests

**Delivery (6 pages)** — zone-based order claiming, active deliveries with a four-step progress tracker (Assigned → Picked Up → In Transit → Delivered), delivery history, earnings tracking, vehicle/zone management

**Admin (13 pages)** — platform-wide analytics, live database health monitoring, user management, product moderation, dispute resolution, payout approvals, platform coupons, announcements, referral tracking, JSON activity log, full audit trail

## Database Design

### Schema

22 tables designed directly in **Third Normal Form (3NF)**:
- **1NF** — every column holds a single atomic value, no repeating groups
- **2NF** — every non-key column depends on the whole primary key (e.g. order lines live in `order_items`, not as columns on `orders`)
- **3NF** — no non-key column depends on another non-key column (city, category, and shop details are each referenced by id, not duplicated)

One deliberate, documented exception: `products.rating` and `shops.rating` are cached aggregates maintained automatically by triggers — a standard denormalization that keeps list screens fast while guaranteeing the cache can never drift from the underlying reviews.

## Where Each Database Concept Lives

| Concept | Implementation |
|---|---|
| **Keys & Constraints** | Every table has an `INTEGER PRIMARY KEY`; `FOREIGN KEY` constraints with `PRAGMA foreign_keys = ON`; `CHECK` constraints on enum columns; `UNIQUE` constraints prevent duplicate emails, coupon codes, and reviews |
| **Joins & Subqueries** | Almost every screen is a join — e.g. `orders → users → shops` for the transaction log; correlated and scalar subqueries for per-row aggregates |
| **SQL Views (13)** | Package complex joins/aggregations behind simple names, e.g. `v_daily_revenue`, `v_low_stock` |
| **Triggers (12)** | Keep the database self-maintaining — cached ratings, FTS index sync, and more — regardless of application-layer mistakes |
| **Indexes (7)** | Target the hottest lookups: orders by buyer/shop/status, order items by order, products by shop/category, reviews by product |
| **ACID Transactions** | Checkout runs inside a single `BEGIN…COMMIT`: validates coupons, checks stock, creates orders, moves cart items, deducts loyalty points, and clears the cart — all atomically, with rollback on any failure |
| **Full-Text Search (FTS5)** | `products_fts` virtual table with `MATCH` queries; three FTS triggers keep the index synchronized on every insert/update/delete |
| **NoSQL Inside SQL (JSON1)** | `activity_log` stores one JSON document per event with no fixed columns — a document store living inside SQLite, queried via `json_extract()` |
| **Role-Based Access Control** | `users.role` is checked at login and drives which dashboard is constructed; every model function scopes data to the caller's own id |
| **Security** | Salted SHA-256 password hashing; fully parameterized queries (SQL injection is impossible by construction) |

## Reliability

The application is built to never show a raw error, with three stacked safety nets:
1. Input validators check every form before conversion
2. Every risky call site (database writes, file exports, numeric parses) has a targeted try/except
3. A global exception handler catches anything unexpected, logs the traceback, and shows the user a calm message

The delivered build was verified end-to-end in an automated harness: all 39 pages render for all four roles without error, ~70 model operations were exercised (including hostile edge cases like invalid ids, empty carts, and over-redeemed points), and the full order lifecycle was traced to confirm stock, loyalty, and balance updates apply exactly once.

## Tech Stack

`Python` · `SQLite` · `SQLite FTS5` · `JSON1` · `Tkinter` · `matplotlib`

## Author

**Mustafa Shahid** — CMS 500889, BSCS-14B
School of Electrical Engineering & Computer Science (SEECS), NUST

Built as the semester project for **CS-220 (Database Systems)**.
