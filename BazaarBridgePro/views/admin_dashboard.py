"""
views/admin_dashboard.py
================================================================================
The Admin experience — total visibility and control. Pages: Analytics (six
embedded matplotlib charts + forecast), Users, Moderation, Transactions (with
CSV/JSON/XML export), NoSQL Activity Log, Disputes, Payouts, Announcements,
Coupons & Flash, Referrals and Audit Log.

Data flows through the model layer (views, joins, JSON1 queries). Exports are
written to an 'exports' folder next to the app and the path is shown to the user.
All actions are wrapped so a raw traceback is never shown.
================================================================================
"""

import os
import json
import tkinter as tk
import ttkbootstrap as tb

from views.base_dashboard import BaseDashboard
from views.components import (Card, stat_row, section_title, Field, Modal,
                              DataTable, confirm, stars, pill, humanize)
from views import charts
from models import analytics_model, admin_model, user_model
from utils import validators, exporters
from utils.theme import COLORS, FONTS, PAD_S, PAD_M, PAD_L, CARD_ACCENTS


class AdminDashboard(BaseDashboard):
    """Dashboard shown to users with the 'admin' role."""

    ROLE_LABEL = "ADMIN"
    ACCENT = COLORS["danger"]
    NAV = [
        (None, None, "Overview"),
        ("analytics",  "📊", "Analytics"),
        ("health",     "🩺", "Platform Health"),
        (None, None, "Catalogue & Trust"),
        ("users",      "👥", "Users"),
        ("moderation", "🛡️", "Moderation"),
        ("disputes",   "⚖️", "Disputes"),
        (None, None, "Logistics"),
        ("partners",   "🚚", "Delivery Partners"),
        (None, None, "Finance"),
        ("txns",       "🧾", "Transactions"),
        ("payouts",    "💰", "Payouts"),
        ("promos",     "🎟️", "Coupons & Flash"),
        (None, None, "Engagement"),
        ("announce",   "📢", "Announcements"),
        ("referrals",  "🔗", "Referrals"),
        (None, None, "System"),
        ("activity",   "🗂️", "Activity Log"),
        ("audit",      "📜", "Audit Log"),
    ]

    def build_page(self, key, parent):
        {
            "analytics": self._page_analytics, "health": self._page_health,
            "users": self._page_users, "partners": self._page_partners,
            "moderation": self._page_moderation, "txns": self._page_txns,
            "activity": self._page_activity, "disputes": self._page_disputes,
            "payouts": self._page_payouts, "announce": self._page_announce,
            "promos": self._page_promos, "referrals": self._page_referrals,
            "audit": self._page_audit,
        }[key](parent)

    # =====================================================================
    # ANALYTICS
    # =====================================================================
    def _page_analytics(self, parent):
        inner = self.scroll_page(parent)
        t = analytics_model.platform_totals()
        section_title(inner, "Platform Analytics",
                      "Live overview of the entire BazaarBridge marketplace")
        stat_row(inner, [
            {"title": "Total Revenue", "value": f"Rs {t['revenue']:,.0f}",
             "icon": "💵", "accent": CARD_ACCENTS[1]},
            {"title": "Total Orders", "value": t["orders"], "icon": "🧾",
             "accent": CARD_ACCENTS[0]},
            {"title": "Users", "value": t["users"], "icon": "👥",
             "accent": CARD_ACCENTS[2]},
            {"title": "Products", "value": t["products"], "icon": "📦",
             "accent": CARD_ACCENTS[5]},
        ])
        stat_row(inner, [
            {"title": "Sellers", "value": t["sellers"], "icon": "🏪",
             "accent": CARD_ACCENTS[3]},
            {"title": "Buyers", "value": t["buyers"], "icon": "🛒",
             "accent": CARD_ACCENTS[2]},
            {"title": "Pending Approval", "value": t["pending_products"],
             "icon": "⏳", "accent": CARD_ACCENTS[3]},
            {"title": "Open Disputes", "value": t["open_disputes"], "icon": "⚖️",
             "accent": CARD_ACCENTS[4]},
        ])

        # ---- Two charts per row ----
        row1 = tb.Frame(inner); row1.pack(fill="x", pady=(PAD_M, 0))
        row1.columnconfigure(0, weight=1); row1.columnconfigure(1, weight=1)

        c1 = Card(row1); c1.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        section_title(c1, "Daily Revenue Trend")
        dr = analytics_model.daily_revenue()
        charts.line_chart(c1, [r["day"][5:] for r in dr], [r["revenue"] for r in dr],
                          ylabel="Rs", color=COLORS["primary"]).pack(fill="x")

        c2 = Card(row1); c2.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0))
        section_title(c2, "Revenue by Category")
        cr = analytics_model.category_revenue()
        charts.bar_chart(c2, [r["category"] for r in cr], [r["revenue"] for r in cr],
                         ylabel="Rs", color=COLORS["success"]).pack(fill="x")

        row2 = tb.Frame(inner); row2.pack(fill="x", pady=(PAD_M, 0))
        row2.columnconfigure(0, weight=1); row2.columnconfigure(1, weight=1)

        c3 = Card(row2); c3.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        section_title(c3, "Top Sellers")
        ts = analytics_model.top_sellers()
        charts.bar_chart(c3, [r["shop_name"][:20] for r in ts],
                         [r["revenue"] for r in ts], xlabel="Rs",
                         color=COLORS["info"], horizontal=True).pack(fill="x")

        c4 = Card(row2); c4.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0))
        section_title(c4, "Orders by City")
        co = analytics_model.city_orders()
        charts.pie_chart(c4, [r["city"] for r in co],
                         [r["orders"] for r in co]).pack(fill="x")

        row3 = tb.Frame(inner); row3.pack(fill="x", pady=(PAD_M, 0))
        row3.columnconfigure(0, weight=1); row3.columnconfigure(1, weight=1)

        c5 = Card(row3); c5.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        section_title(c5, "Top Buyers")
        tbu = analytics_model.top_buyers()
        charts.bar_chart(c5, [r["full_name"].split()[0] for r in tbu],
                         [r["spent"] for r in tbu], xlabel="Rs",
                         color=COLORS["warning"], horizontal=True).pack(fill="x")

        c6 = Card(row3); c6.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0))
        section_title(c6, "Revenue Forecast (next 3 days)")
        hist, forecast = analytics_model.revenue_forecast()
        charts.forecast_chart(c6, [r["day"][5:] for r in hist],
                              [r["revenue"] for r in hist], forecast).pack(fill="x")

        # ---- Advanced filters (date range + city + category) ----
        self._build_analytics_filters(inner)

    def _build_analytics_filters(self, inner):
        """A filter panel that recomputes revenue metrics by date/city/category."""
        cities, cats = analytics_model.filter_options()
        self._city_map = {"All cities": None}
        self._city_map.update({c["name"]: c["city_id"] for c in cities})
        self._cat_map = {"All categories": None}
        self._cat_map.update({c["name"]: c["category_id"] for c in cats})

        panel = Card(inner); panel.pack(fill="x", pady=(PAD_M, 0))
        section_title(panel, "🔎 Advanced Analytics Filters",
                      "Filter delivered revenue by date range, city and category")
        controls = tb.Frame(panel); controls.pack(fill="x")

        self.f_from = Field(controls, "From (YYYY-MM-DD)", width=16)
        self.f_from.grid(row=0, column=0, sticky="w", padx=(0, PAD_M))
        self.f_to = Field(controls, "To (YYYY-MM-DD)", width=16)
        self.f_to.grid(row=0, column=1, sticky="w", padx=(0, PAD_M))
        self.f_city = Field(controls, "City", kind="combo",
                            values=list(self._city_map.keys()),
                            default="All cities", width=20)
        self.f_city.grid(row=0, column=2, sticky="w", padx=(0, PAD_M))
        self.f_cat = Field(controls, "Category", kind="combo",
                           values=list(self._cat_map.keys()),
                           default="All categories", width=22)
        self.f_cat.grid(row=0, column=3, sticky="w", padx=(0, PAD_M))
        tb.Button(controls, text="Apply Filters", bootstyle="primary",
                  command=lambda: self._run_analytics_filter(panel)).grid(
                      row=0, column=4, sticky="w", pady=(PAD_L, 0))

        self._filter_result = tb.Frame(panel); self._filter_result.pack(fill="x", pady=(PAD_M, 0))
        self._run_analytics_filter(panel)   # show full-range results initially

    def _run_analytics_filter(self, panel):
        for w in self._filter_result.winfo_children():
            w.destroy()
        date_from = self.f_from.get() or None
        date_to = self.f_to.get() or None
        city_id = self._city_map.get(self.f_city.get())
        cat_id = self._cat_map.get(self.f_cat.get())
        try:
            r = analytics_model.filtered_analytics(date_from, date_to, city_id, cat_id)
        except Exception:
            tb.Label(self._filter_result, text="Could not compute — check the date format.",
                     foreground=COLORS["danger"]).pack(anchor="w")
            return

        stat_row(self._filter_result, [
            {"title": "Filtered Revenue", "value": f"Rs {r['revenue']:,.0f}",
             "icon": "💰", "gradient": "indigo"},
            {"title": "Orders", "value": f"{r['orders']:,}", "icon": "🧾",
             "gradient": "emerald"},
            {"title": "Units Sold", "value": f"{r['units']:,}", "icon": "📦",
             "gradient": "sky"},
        ])
        if r["daily"]:
            cc = Card(self._filter_result); cc.pack(fill="x", pady=(PAD_S, 0))
            section_title(cc, "Filtered Daily Revenue")
            charts.line_chart(cc, [str(x["day"])[5:] for x in r["daily"]],
                              [x["revenue"] for x in r["daily"]], ylabel="Rs",
                              color=COLORS["primary"]).pack(fill="x")
        else:
            tb.Label(self._filter_result,
                     text="No delivered orders match these filters.",
                     foreground=COLORS["muted"]).pack(anchor="w", pady=PAD_M)

    # =====================================================================
    # PLATFORM HEALTH  — system-wide statistics at a glance
    # =====================================================================
    def _page_health(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "🩺 Platform Health",
                      "Live system statistics across users, catalogue, orders and the database")
        h = admin_model.platform_health()

        stat_row(inner, [
            {"title": "Total Users", "value": f"{h['users']:,}", "icon": "👥",
             "subtitle": f"{h['active_users']} active", "gradient": "indigo"},
            {"title": "Products", "value": f"{h['products']:,}", "icon": "📦",
             "subtitle": f"{h['approved_products']} approved", "gradient": "emerald"},
            {"title": "Orders", "value": f"{h['orders']:,}", "icon": "🧾",
             "subtitle": f"{h['delivered']} delivered", "gradient": "sky"},
            {"title": "Revenue", "value": f"Rs {h['revenue']:,.0f}", "icon": "💰",
             "subtitle": "delivered orders", "gradient": "amber"},
        ])

        attention = Card(inner); attention.pack(fill="x", pady=(0, PAD_M))
        section_title(attention, "Needs Attention")
        cells = [
            ("Pending products", h["pending_products"], "warning"),
            ("Flagged products", h["flagged_products"], "danger"),
            ("Low stock", h["low_stock"], "warning"),
            ("Out of stock", h["out_of_stock"], "danger"),
            ("Open disputes", h["open_disputes"], "danger"),
            ("Pending payouts", h["pending_payouts"], "warning"),
            ("Orders in progress", h["in_progress"], "info"),
            ("Pending orders", h["pending_orders"], "info"),
        ]
        grid = tb.Frame(attention); grid.pack(fill="x")
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform="att")
        for i, (label, val, kind) in enumerate(cells):
            cell = tb.Frame(grid, bootstyle="light")
            cell.grid(row=i // 4, column=i % 4, sticky="nsew", padx=PAD_S, pady=PAD_S)
            tk.Label(cell, text=str(val), font=("Segoe UI", 20, "bold"),
                     fg=COLORS[kind], bg=COLORS["card"]).pack(anchor="w", padx=PAD_M, pady=(PAD_S, 0))
            tk.Label(cell, text=label, font=FONTS["small"], fg=COLORS["muted"],
                     bg=COLORS["card"]).pack(anchor="w", padx=PAD_M, pady=(0, PAD_S))

        two = tb.Frame(inner); two.pack(fill="x", pady=(0, PAD_M))
        two.columnconfigure(0, weight=1, uniform="h")
        two.columnconfigure(1, weight=1, uniform="h")

        eng = Card(two); eng.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        section_title(eng, "Engagement")
        for label, val in [("Verified shops", f"{h['verified_shops']} / {h['shops']}"),
                           ("Active flash sales", h["active_flash"]),
                           ("Reviews posted", h["reviews"]),
                           ("Active coupons", h["coupons_active"]),
                           ("Referrals tracked", h["referrals"]),
                           ("Notifications sent", h["notifications"]),
                           ("NoSQL activity docs", h["activity_docs"])]:
            r = tb.Frame(eng); r.pack(fill="x", pady=2)
            tb.Label(r, text=label, font=FONTS["body"]).pack(side="left")
            tb.Label(r, text=str(val), font=FONTS["body_b"],
                     foreground=COLORS["primary"]).pack(side="right")

        dbc = Card(two); dbc.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0))
        section_title(dbc, "Database Objects (CS-220)")
        for label, val in [("Tables", h["table_count"]), ("Views", h["view_count"]),
                           ("Triggers", h["trigger_count"]), ("Indexes", h["index_count"])]:
            r = tb.Frame(dbc); r.pack(fill="x", pady=2)
            tb.Label(r, text=label, font=FONTS["body"]).pack(side="left")
            tb.Label(r, text=str(val), font=FONTS["body_b"],
                     foreground=COLORS["success"]).pack(side="right")

        fp = Card(inner); fp.pack(fill="both", expand=True)
        section_title(fp, "Database Footprint", "Row counts across every table")
        table = DataTable(fp, ["Table", "Rows"],
                          widths={"Table": 260, "Rows": 120}, height=11)
        table.pack(fill="both", expand=True)
        table.load([(t, f"{c:,}") for t, c in h["footprint"]])

    # =====================================================================
    # DELIVERY PARTNERS  — fleet performance leaderboard
    # =====================================================================
    def _page_partners(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "🚚 Delivery Partners",
                      "Fleet performance across zones, deliveries and earnings")
        partners = admin_model.all_partners()
        if not partners:
            self._empty(inner, "No delivery partners registered yet.")
            return

        total_deliveries = sum(p["deliveries"] for p in partners)
        total_earnings = sum(p["earnings"] for p in partners)
        active_now = sum(p["active"] for p in partners)
        avg_rating = (sum(p["rating"] for p in partners) / len(partners)) if partners else 0
        stat_row(inner, [
            {"title": "Partners", "value": f"{len(partners):,}", "icon": "🚚",
             "gradient": "indigo"},
            {"title": "Deliveries", "value": f"{total_deliveries:,}", "icon": "✅",
             "gradient": "emerald"},
            {"title": "Active Now", "value": f"{active_now:,}", "icon": "📦",
             "gradient": "sky"},
            {"title": "Avg Rating", "value": f"{avg_rating:.1f}★", "icon": "⭐",
             "gradient": "amber"},
        ])

        # Top earners chart
        chart_card = Card(inner); chart_card.pack(fill="x", pady=(0, PAD_M))
        section_title(chart_card, "Top Earners")
        top = sorted(partners, key=lambda p: p["earnings"], reverse=True)[:8]
        charts.bar_chart(chart_card,
                         [p["full_name"].split()[0] for p in top],
                         [p["earnings"] for p in top], ylabel="Rs",
                         color=COLORS["info"]).pack(fill="x")

        # Full table
        table_card = Card(inner); table_card.pack(fill="both", expand=True)
        section_title(table_card, "All Partners")
        table = DataTable(table_card,
                          ["Partner", "Zone", "Vehicle", "Rating", "Deliveries",
                           "Active", "Earnings"],
                          widths={"Partner": 170, "Zone": 110, "Vehicle": 90,
                                  "Rating": 80, "Deliveries": 100, "Active": 80,
                                  "Earnings": 120}, height=12)
        table.pack(fill="both", expand=True)
        table.load([(p["full_name"], p["zone"], p["vehicle_type"],
                     f"{p['rating']:.1f}★", p["deliveries"], p["active"],
                     f"Rs {p['earnings']:,.0f}") for p in partners])

    # =====================================================================
    # USERS
    # =====================================================================
    def _page_users(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "User Management",
                      "Search, filter and activate/deactivate accounts")

        bar = Card(inner); bar.pack(fill="x", pady=(0, PAD_M))
        row = tb.Frame(bar); row.pack(fill="x")
        self.u_search = Field(row, "Search name/email", width=26)
        self.u_search.pack(side="left", padx=(0, PAD_S))
        self.u_role = Field(row, "Role", kind="combo",
                            values=["All", "buyer", "seller", "delivery", "admin"],
                            default="All", width=14)
        self.u_role.pack(side="left", padx=(0, PAD_S))
        tb.Button(row, text="Search", bootstyle="primary",
                  command=lambda: self._load_users(inner)).pack(side="left", pady=(PAD_M, 0))
        self.u_search.widget.bind("<Return>", lambda e: self._load_users(inner))

        self._users_holder = tb.Frame(inner)
        self._users_holder.pack(fill="both", expand=True)
        self._load_users(inner)

    def _load_users(self, inner):
        for w in self._users_holder.winfo_children():
            w.destroy()
        role = None if self.u_role.get() == "All" else self.u_role.get()
        users = admin_model.all_users(role=role, search=self.u_search.get())
        card = Card(self._users_holder); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["ID", "Name", "Email", "Role", "City", "Status"],
                        widths={"ID": 40, "Name": 160, "Email": 200, "Role": 80,
                                "City": 110, "Status": 80}, height=14)
        tbl.pack(fill="both", expand=True, pady=(0, PAD_S))
        tbl.load([(u["user_id"], u["full_name"], u["email"], u["role"],
                   u["city_name"], "Active" if u["is_active"] else "Disabled")
                  for u in users])
        btns = tb.Frame(card); btns.pack(fill="x")
        tb.Button(btns, text="Activate", bootstyle="success",
                  command=lambda: self._toggle_user(tbl, 1)).pack(side="left")
        tb.Button(btns, text="Deactivate", bootstyle="danger",
                  command=lambda: self._toggle_user(tbl, 0)).pack(side="left", padx=PAD_S)

    def _toggle_user(self, tbl, active):
        sel = tbl.selected()
        if not sel:
            self.notify("Select a user first.", "warning"); return
        if sel[3] == "admin":
            self.notify("Admin accounts cannot be changed here.", "warning"); return
        admin_model.set_user_active(sel[0], active)
        self.notify(f"User {'activated' if active else 'deactivated'}.", "success")
        self.refresh()

    # =====================================================================
    # MODERATION
    # =====================================================================
    def _page_moderation(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Product Moderation",
                      "Approve, reject or flag products")
        bar = tb.Frame(inner); bar.pack(fill="x", pady=(0, PAD_S))
        self.m_status = Field(bar, "Filter status", kind="combo",
                              values=["all", "approved", "pending", "rejected", "flagged"],
                              default="all", width=16)
        self.m_status.pack(side="left")
        tb.Button(bar, text="Apply", bootstyle="primary",
                  command=lambda: self._load_mod(inner)).pack(side="left",
                  padx=PAD_S, pady=(PAD_M, 0))
        self._mod_holder = tb.Frame(inner); self._mod_holder.pack(fill="both", expand=True)
        self._load_mod(inner)

    def _load_mod(self, inner):
        for w in self._mod_holder.winfo_children():
            w.destroy()
        status = self.m_status.get()
        prods = admin_model.products_for_moderation(None if status == "all" else status)
        card = Card(self._mod_holder); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["ID", "Product", "Shop", "Price", "Status"],
                        widths={"ID": 40, "Product": 220, "Shop": 160,
                                "Price": 90, "Status": 90}, height=14)
        tbl.pack(fill="both", expand=True, pady=(0, PAD_S))
        tbl.load([(p["product_id"], p["name"], p["shop_name"],
                   f"Rs {p['price']:,.0f}", humanize(p["status"])) for p in prods])
        btns = tb.Frame(card); btns.pack(fill="x")
        for label, status_val, style in [("Approve", "approved", "success"),
                                         ("Reject", "rejected", "danger"),
                                         ("Flag", "flagged", "warning")]:
            tb.Button(btns, text=label, bootstyle=style,
                      command=lambda s=status_val, t=tbl: self._moderate(t, s)).pack(
                          side="left", padx=(0, PAD_S))

    def _moderate(self, tbl, status):
        sel = tbl.selected()
        if not sel:
            self.notify("Select a product first.", "warning"); return
        admin_model.set_product_status(sel[0], status)
        self.notify(f"Product → {status}.", "success")
        self.refresh()

    # =====================================================================
    # TRANSACTIONS + EXPORT
    # =====================================================================
    def _page_txns(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Transaction Log",
                      "Every order on the platform, with data export")
        bar = tb.Frame(inner); bar.pack(fill="x", pady=(0, PAD_S))
        self.t_search = Field(bar, "Search buyer/shop/status", width=28)
        self.t_search.pack(side="left", padx=(0, PAD_S))
        tb.Button(bar, text="Search", bootstyle="primary",
                  command=lambda: self._load_txns(inner)).pack(side="left", pady=(PAD_M, 0))

        exprow = tb.Frame(inner); exprow.pack(fill="x", pady=(0, PAD_S))
        tb.Label(exprow, text="Export:", font=FONTS["small"],
                 foreground=COLORS["muted"]).pack(side="left", padx=(0, PAD_S))
        for fmt, style in [("CSV", "success-outline"), ("JSON", "info-outline"),
                           ("XML", "warning-outline")]:
            tb.Button(exprow, text=fmt, bootstyle=style,
                      command=lambda f=fmt.lower(): self._export(f)).pack(
                          side="left", padx=(0, PAD_S))

        self._txn_holder = tb.Frame(inner); self._txn_holder.pack(fill="both", expand=True)
        self._load_txns(inner)

    def _load_txns(self, inner):
        for w in self._txn_holder.winfo_children():
            w.destroy()
        self._txn_rows = admin_model.transactions(self.t_search.get())
        card = Card(self._txn_holder); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["Order", "Buyer", "Shop", "Total", "Status", "Date"],
                        widths={"Order": 60, "Buyer": 150, "Shop": 160,
                                "Total": 100, "Status": 90, "Date": 150}, height=15)
        tbl.pack(fill="both", expand=True)
        tbl.load([(f"#{r['order_id']}", r["buyer"], r["shop"],
                   f"Rs {r['total']:,.0f}", humanize(r["status"]), r["placed_at"][:16])
                  for r in self._txn_rows])

    def _export(self, fmt):
        try:
            if not self._txn_rows:
                self.notify("Nothing to export.", "warning"); return
            out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"transactions.{fmt}")
            if fmt == "csv":
                exporters.export_csv(self._txn_rows, path)
            elif fmt == "json":
                exporters.export_json(self._txn_rows, path)
            else:
                exporters.export_xml(self._txn_rows, path)
            self.notify(f"Saved {len(self._txn_rows)} rows to {os.path.abspath(path)}",
                        "success")
        except PermissionError:
            self.notify("Couldn't save — the file may be open in another program.",
                        "danger")
        except OSError as e:
            self.notify(f"Couldn't write the export file ({e.strerror}).", "danger")
        except Exception:
            self.notify("Export failed. Please try again.", "danger")

    # =====================================================================
    # NoSQL ACTIVITY LOG
    # =====================================================================
    def _page_activity(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "NoSQL Activity Log",
                      "Unstructured JSON documents queried with SQLite's JSON1 engine")
        bar = tb.Frame(inner); bar.pack(fill="x", pady=(0, PAD_S))
        events = ["All"] + [e["event"] for e in admin_model.activity_event_types()]
        self.a_event = Field(bar, "Filter by event", kind="combo", values=events,
                             default="All", width=20)
        self.a_event.pack(side="left")
        tb.Button(bar, text="Apply", bootstyle="primary",
                  command=lambda: self._load_activity(inner)).pack(side="left",
                  padx=PAD_S, pady=(PAD_M, 0))
        tb.Button(bar, text="+ Add Document", bootstyle="success-outline",
                  command=self._add_activity_modal).pack(side="left", pady=(PAD_M, 0))
        self._act_holder = tb.Frame(inner); self._act_holder.pack(fill="both", expand=True)
        self._load_activity(inner)

    def _load_activity(self, inner):
        for w in self._act_holder.winfo_children():
            w.destroy()
        ev = None if self.a_event.get() == "All" else self.a_event.get()
        docs = admin_model.activity_documents(ev)
        if not docs:
            tb.Label(self._act_holder, text="No activity documents.",
                     foreground=COLORS["muted"]).pack(anchor="w", pady=PAD_M)
            return
        for d in docs:
            c = Card(self._act_holder); c.pack(fill="x", pady=4)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"🗂️  {d['event'] or 'event'}", font=FONTS["h3"],
                     foreground=COLORS["primary"]).pack(side="left")
            tb.Label(top, text=d["created_at"][:16], font=FONTS["small"],
                     foreground=COLORS["muted"]).pack(side="right")
            # Pretty-print the stored JSON document.
            try:
                pretty = json.dumps(json.loads(d["doc"]), indent=2)
            except Exception:
                pretty = d["doc"]
            box = tk.Text(c, height=min(8, pretty.count("\n") + 1), wrap="word",
                          font=("Consolas", 9), relief="flat",
                          bg="#f7f8fc", fg=COLORS["text"])
            box.insert("1.0", pretty); box.configure(state="disabled")
            box.pack(fill="x", pady=(PAD_S, 0))

    def _add_activity_modal(self):
        dlg = Modal(self.app.root, "Add Activity Document", width=480, height=420)
        ev = Field(dlg.body, "Event type (e.g. login, search)")
        ev.pack(fill="x", pady=PAD_S)
        detail = Field(dlg.body, "Detail / note"); detail.pack(fill="x", pady=PAD_S)

        def save():
            if not ev.get():
                self.notify("Event type is required.", "warning"); return
            admin_model.log_activity({"event": ev.get().lower(),
                                      "detail": detail.get(),
                                      "by": self.user["full_name"]})
            self.notify("Activity document stored.", "success")
            dlg.destroy(); self.refresh()
        tb.Button(dlg.body, text="Store Document", bootstyle="success",
                  command=save).pack(anchor="e", pady=PAD_M)

    # =====================================================================
    # DISPUTES
    # =====================================================================
    def _page_disputes(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Dispute Resolution", "Review and resolve buyer disputes")
        disputes = admin_model.all_disputes()
        if not disputes:
            self._empty(inner, "No disputes raised.")
            return
        for d in disputes:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"Dispute #{d['dispute_id']}  ·  Order #{d['order_id']}",
                     font=FONTS["h3"]).pack(side="left")
            pill(top, d["status"].title(), status=d["status"]).pack(side="right")
            tb.Label(c, text=f"Raised by {d['buyer']}  ·  Order total Rs {d['total']:,.0f}",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w")
            tb.Label(c, text=f"Reason: {d['reason']}", font=FONTS["body"],
                     wraplength=640, justify="left").pack(anchor="w", pady=(PAD_S, 0))
            if d["status"] == "open":
                act = tb.Frame(c); act.pack(fill="x", pady=(PAD_S, 0))
                tb.Button(act, text="Resolve", bootstyle="success",
                          command=lambda d=d: self._resolve_dispute(d, "resolved")).pack(
                              side="right")
                tb.Button(act, text="Reject", bootstyle="danger-outline",
                          command=lambda d=d: self._resolve_dispute(d, "rejected")).pack(
                              side="right", padx=(0, PAD_S))

    def _resolve_dispute(self, d, status):
        admin_model.set_dispute_status(d["dispute_id"], status)
        self.notify(f"Dispute #{d['dispute_id']} → {status}.", "success")
        self.refresh()

    # =====================================================================
    # PAYOUTS
    # =====================================================================
    def _page_payouts(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Payout Approvals",
                      "Approve or reject seller and rider withdrawals")
        payouts = admin_model.all_payouts()
        if not payouts:
            self._empty(inner, "No payout requests.")
            return
        for p in payouts:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"Payout #{p['payout_id']}  ·  {p['full_name']} "
                     f"({p['role']})", font=FONTS["h3"]).pack(side="left")
            tb.Label(top, text=f"Rs {p['amount']:,.0f}", font=FONTS["h3"],
                     foreground=COLORS["primary"]).pack(side="right")
            # Meta row: status pill + date on the left, actions on the right —
            # all on one line so there is never a disconnected empty band.
            meta = tb.Frame(c); meta.pack(fill="x", pady=(PAD_S, 0))
            pill(meta, p["status"].title(), status=p["status"]).pack(side="left")
            tb.Label(meta, text="  ·  " + str(p["requested_at"])[:16],
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(side="left")
            if p["status"] == "pending":
                tb.Button(meta, text="Approve", bootstyle="success",
                          command=lambda p=p: self._set_payout(p, "approved")).pack(
                              side="right")
                tb.Button(meta, text="Reject", bootstyle="danger-outline",
                          command=lambda p=p: self._set_payout(p, "rejected")).pack(
                              side="right", padx=(0, PAD_S))

    def _set_payout(self, p, status):
        admin_model.set_payout_status(p["payout_id"], status)
        self.notify(f"Payout #{p['payout_id']} → {status}.", "success")
        self.refresh()

    # =====================================================================
    # ANNOUNCEMENTS
    # =====================================================================
    def _page_announce(self, parent):
        inner = self.scroll_page(parent)
        head = tb.Frame(inner); head.pack(fill="x")
        section_title(head, "Announcements", "Platform-wide messages")
        tb.Button(head, text="+ New Announcement", bootstyle="success",
                  command=self._announce_modal).pack(side="right")
        items = admin_model.all_announcements()
        if not items:
            self._empty(inner, "No announcements yet.")
            return
        for a in items:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text="📢  " + a["title"], font=FONTS["h3"]).pack(side="left")
            tb.Button(top, text="Delete", bootstyle="danger-outline",
                      command=lambda a=a: self._del_announce(a)).pack(side="right")
            tb.Label(c, text=a["body"], font=FONTS["body"], wraplength=640,
                     justify="left").pack(anchor="w", pady=(PAD_S, 0))
            tb.Label(c, text=a["created_at"][:16], font=FONTS["small"],
                     foreground=COLORS["muted"]).pack(anchor="w")

    def _announce_modal(self):
        dlg = Modal(self.app.root, "New Announcement", width=480, height=400)
        title = Field(dlg.body, "Title"); title.pack(fill="x", pady=PAD_S)
        body = Field(dlg.body, "Message", kind="text"); body.pack(fill="x", pady=PAD_S)

        def save():
            ok, msg = validators.validate_all(
                validators.validate_required(title.get(), "Title"),
                validators.validate_required(body.get(), "Message"))
            if not ok:
                self.notify(msg, "warning"); return
            admin_model.add_announcement(title.get(), body.get())
            self.notify("Announcement published.", "success")
            dlg.destroy(); self.refresh()
        tb.Button(dlg.body, text="Publish", bootstyle="success",
                  command=save).pack(anchor="e", pady=PAD_M)

    def _del_announce(self, a):
        if not confirm(self.app.root, f"Delete '{a['title']}'?"):
            return
        admin_model.delete_announcement(a["announcement_id"])
        self.notify("Announcement deleted.", "info")
        self.refresh()

    # =====================================================================
    # COUPONS & FLASH
    # =====================================================================
    def _page_promos(self, parent):
        inner = self.scroll_page(parent)
        head = tb.Frame(inner); head.pack(fill="x")
        section_title(head, "Coupons & Flash", "Platform-wide coupon management")
        tb.Button(head, text="+ New Coupon", bootstyle="success",
                  command=self._coupon_modal).pack(side="right")
        coupons = admin_model.all_coupons()
        card = Card(inner); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["ID", "Code", "Discount %", "Min Order",
                               "Scope", "Active"],
                        widths={"ID": 40, "Code": 120, "Discount %": 90,
                                "Min Order": 110, "Scope": 120, "Active": 70},
                        height=12)
        tbl.pack(fill="both", expand=True, pady=(0, PAD_S))
        tbl.load([(c["coupon_id"], c["code"], f"{c['discount_pct']}%",
                   f"Rs {c['min_amount']:,.0f}",
                   "Platform" if c["shop_id"] is None else f"Shop {c['shop_id']}",
                   "Yes" if c["is_active"] else "No") for c in coupons])
        tb.Button(card, text="Toggle Active (selected)", bootstyle="info",
                  command=lambda: self._toggle_coupon(tbl)).pack(side="left")

    def _toggle_coupon(self, tbl):
        sel = tbl.selected()
        if not sel:
            self.notify("Select a coupon first.", "warning"); return
        admin_model.toggle_coupon(sel[0])
        self.notify("Coupon toggled.", "success")
        self.refresh()

    def _coupon_modal(self):
        dlg = Modal(self.app.root, "New Platform Coupon", width=440, height=360)
        code = Field(dlg.body, "Coupon code"); code.pack(fill="x", pady=PAD_S)
        pct = Field(dlg.body, "Discount %", default="10", width=12)
        pct.pack(anchor="w", pady=PAD_S)
        minamt = Field(dlg.body, "Minimum order (Rs)", default="0", width=14)
        minamt.pack(anchor="w", pady=PAD_S)

        def save():
            ok, msg = validators.validate_all(
                validators.validate_required(code.get(), "Code"),
                validators.validate_positive_int(pct.get(), "Discount"),
                validators.validate_positive_number(minamt.get(), "Minimum"))
            if not ok:
                self.notify(msg, "warning"); return
            okc, m = admin_model.add_coupon(code.get().upper(), int(pct.get()),
                                            float(minamt.get()), None)
            self.notify(m, "success" if okc else "danger")
            if okc:
                dlg.destroy(); self.refresh()
        tb.Button(dlg.body, text="Create Coupon", bootstyle="success",
                  command=save).pack(anchor="e", pady=PAD_M)

    # =====================================================================
    # REFERRALS
    # =====================================================================
    def _page_referrals(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Referral Tracking", "Who invited whom, and rewards")
        refs = admin_model.all_referrals()
        if not refs:
            self._empty(inner, "No referrals recorded.")
            return
        card = Card(inner); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["ID", "Referrer", "Referred", "Reward Points", "Date"],
                        widths={"ID": 40, "Referrer": 180, "Referred": 180,
                                "Reward Points": 110, "Date": 150}, height=14)
        tbl.pack(fill="both", expand=True)
        tbl.load([(r["referral_id"], r["referrer"], r["referred"],
                   r["reward_points"], r["created_at"][:16]) for r in refs])

    # =====================================================================
    # AUDIT LOG
    # =====================================================================
    def _page_audit(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Audit Log",
                      "Every significant action recorded for traceability")
        entries = admin_model.audit_entries()
        card = Card(inner); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["ID", "User", "Action", "Entity", "Details", "Time"],
                        widths={"ID": 40, "User": 140, "Action": 100,
                                "Entity": 90, "Details": 220, "Time": 150},
                        height=16)
        tbl.pack(fill="both", expand=True)
        tbl.load([(e["audit_id"], e["full_name"] or "system", e["action"],
                   e["entity"], e["details"], e["created_at"][:16])
                  for e in entries])

    # --------------------------------------------------------------- helpers
    def _empty(self, parent, message):
        box = tb.Frame(parent); box.pack(fill="both", expand=True, pady=PAD_L)
        tb.Label(box, text="📭", font=("Segoe UI", 40)).pack()
        tb.Label(box, text=message, font=FONTS["body"],
                 foreground=COLORS["muted"]).pack(pady=PAD_S)
