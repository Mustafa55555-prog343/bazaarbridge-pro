# BazaarBridge Pro

A full desktop marketplace application connecting four types of users — buyers, sellers, delivery riders, and an admin — through role-based dashboards covering the complete order lifecycle, from checkout to delivery to seller payout.

Built with Python and SQLite, the app runs with **zero setup** — no server, no internet required — and demonstrates a full range of real-world database engineering concepts applied to a realistic, full-scale application.

## Overview

| | |
|---|---|
| **Roles** | Buyer · Seller · Delivery Rider · Admin |
| **Pages** | 39 fully functional pages across 4 dashboards |
| **Database** | SQLite, 22 tables (3NF) |
| **Tests** | Automated harness covering all 39 pages and ~70 core operations |

## Features

- **Complete order lifecycle** — from checkout to delivery to seller payout, with all four user roles interacting through the same live data
- **Role-based access control** — each dashboard exposes only what that role should see
- **Full-text search** — instant product search via SQLite FTS5
- **Secure by default** — hashed passwords and parameterized queries throughout to prevent SQL injection
- **Graceful failure** — global error handling means the app never crashes, only shows friendly messages

## Database Engineering

- 22-table schema normalized to **Third Normal Form (3NF)**
- **13 SQL views**, **12 triggers**, and **7 indexes** keeping dashboards fast and data self-consistent
- **ACID-compliant transactions** on checkout — stock, orders, and loyalty points update atomically, with zero partial writes
- A **JSON-based NoSQL activity log** embedded inside the relational database for flexible event tracking

## Architecture

Built as a three-layer system — **views → business logic → database** — so the SQL layer can be tested completely independently of the UI.
