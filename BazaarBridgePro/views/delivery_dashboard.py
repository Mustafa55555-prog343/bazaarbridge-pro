"""
views/delivery_dashboard.py
================================================================================
The Delivery Partner experience. Pages: Overview (KPIs + earnings chart),
Available Orders (claim queue), Active Deliveries (status stepper), History,
Earnings (chart + withdrawal request) and Vehicle/Zone profile.

The delivery lifecycle moves an order assigned → picked_up → in_transit →
delivered; the status-logging trigger records each change and notifies the buyer.
All UI actions are wrapped to avoid raw tracebacks.
================================================================================
"""

import tkinter as tk
import ttkbootstrap as tb

from views.base_dashboard import BaseDashboard
from views.components import (Card, stat_row, section_title, Field, DataTable,
                              confirm, stars, pill, field_column)
from views import charts
from models import order_model, analytics_model, admin_model, user_model
from utils import validators
from utils.theme import COLORS, FONTS, PAD_S, PAD_M, PAD_L, CARD_ACCENTS


class DeliveryDashboard(BaseDashboard):
    """Dashboard shown to users with the 'delivery' role."""

    ROLE_LABEL = "DELIVERY"
    ACCENT = COLORS["info"]
    NAV = [
        ("overview",  "📊", "Overview"),
        ("available", "📋", "Available Orders"),
        ("active",    "🚚", "Active Deliveries"),
        ("history",   "✅", "History"),
        ("earnings",  "💰", "Earnings"),
        ("vehicle",   "🛵", "Vehicle & Zone"),
    ]

    # Forward steps in a delivery's lifecycle.
    _FLOW = ["assigned", "picked_up", "in_transit", "delivered"]

    def __init__(self, master, app, user):
        self.partner = analytics_model.partner_for_user(user["user_id"])
        super().__init__(master, app, user)

    def build_page(self, key, parent):
        if not self.partner:
            box = self.scroll_page(parent)
            section_title(box, "No partner profile",
                          "Your delivery account has no partner record yet.")
            return
        {
            "overview": self._page_overview, "available": self._page_available,
            "active": self._page_active, "history": self._page_history,
            "earnings": self._page_earnings, "vehicle": self._page_vehicle,
        }[key](parent)

    # =====================================================================
    # OVERVIEW
    # =====================================================================
    def _page_overview(self, parent):
        inner = self.scroll_page(parent)
        t = analytics_model.partner_totals(self.partner["partner_id"])
        section_title(inner, f"Hello, {self.user['full_name'].split()[0]}",
                      f"Zone: {self.partner['zone']}  ·  "
                      f"Vehicle: {self.partner['vehicle_type'] or 'Not set'}")
        stat_row(inner, [
            {"title": "Delivered", "value": t["delivered"], "icon": "✅",
             "accent": CARD_ACCENTS[1]},
            {"title": "Active Now", "value": t["active"], "icon": "🚚",
             "accent": CARD_ACCENTS[2]},
            {"title": "Total Earnings", "value": f"Rs {t['earnings']:,.0f}",
             "icon": "💵", "accent": CARD_ACCENTS[0]},
            {"title": "Rating", "value": stars(t["rating"]), "icon": "⭐",
             "accent": CARD_ACCENTS[3]},
        ])

        chart_card = Card(inner); chart_card.pack(fill="x", pady=(PAD_M, 0))
        section_title(chart_card, "Daily Earnings")
        series = analytics_model.partner_daily_earnings(self.partner["partner_id"])
        days = [r["day"][5:] for r in series]
        vals = [r["earnings"] for r in series]
        charts.line_chart(chart_card, days, vals, ylabel="Rs",
                          color=COLORS["info"]).pack(fill="x")

    # =====================================================================
    # AVAILABLE ORDERS
    # =====================================================================
    def _page_available(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Available Orders",
                      f"Unassigned deliveries in {self.partner['zone']}")
        orders = [dict(o) for o in
                  analytics_model.available_orders(self.partner["zone_city_id"])]
        if not orders:
            self._empty(inner, "No available orders in your zone right now.")
            return
        for o in orders:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"Order #{o['order_id']}  ·  {o['shop_name']}",
                     font=FONTS["h3"]).pack(side="left")
            tb.Label(top, text=f"Fee: Rs {o['delivery_fee']:,.0f}", font=FONTS["h3"],
                     foreground=COLORS["success"]).pack(side="right")
            tb.Label(c, text=f"To: {o['buyer_name']}  ·  {o['buyer_city']}",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w")
            tb.Label(c, text=f"📍 {o['address_line'] or 'Address on file'}",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w",
                     pady=(0, PAD_S))
            tb.Button(c, text="Claim Delivery", bootstyle="primary",
                      command=lambda o=o: self._claim(o)).pack(anchor="e")

    def _claim(self, o):
        admin_model.claim_order(o["order_id"], self.partner["partner_id"])
        self.notify(f"You claimed order #{o['order_id']}.", "success")
        self.refresh()

    # =====================================================================
    # ACTIVE DELIVERIES
    # =====================================================================
    def _page_active(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Active Deliveries",
                      "Advance each delivery through its stages")
        orders = [dict(o) for o in
                  analytics_model.partner_active(self.partner["partner_id"])]
        if not orders:
            self._empty(inner, "No active deliveries. Claim one from Available Orders.")
            return
        for o in orders:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"Order #{o['order_id']}  ·  {o['shop_name']}",
                     font=FONTS["h3"]).pack(side="left")
            self._status_badge(top, o["status"]).pack(side="right")
            tb.Label(c, text=f"Deliver to: {o['buyer_name']}  ·  {o['buyer_city']}",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w")
            tb.Label(c, text=f"📍 {o['address_line'] or 'Address on file'}",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w",
                     pady=(0, PAD_S))

            self._delivery_stepper(c, o["status"])

            nxt = self._next_step(o["status"])
            if nxt:
                label = {"picked_up": "Mark Picked Up",
                         "in_transit": "Mark In Transit",
                         "delivered": "Mark Delivered"}[nxt]
                tb.Button(c, text=label, bootstyle="success",
                          command=lambda o=o, n=nxt: self._advance(o, n)).pack(
                              anchor="e", pady=(PAD_S, 0))

    def _delivery_stepper(self, parent, status):
        idx = self._FLOW.index(status)
        track = tb.Frame(parent); track.pack(fill="x", pady=PAD_S)
        labels = ["Assigned", "Picked Up", "In Transit", "Delivered"]
        for i, lbl in enumerate(labels):
            done = i <= idx
            dot = tk.Canvas(track, width=24, height=24, highlightthickness=0,
                            bg=COLORS["card"])
            col = COLORS["info"] if done else COLORS["border"]
            dot.create_oval(3, 3, 21, 21, fill=col, outline="")
            if done:
                dot.create_text(12, 12, text="✓", fill="white",
                                font=("Segoe UI", 10, "bold"))
            dot.grid(row=0, column=i * 2)
            tb.Label(track, text=lbl, font=("Segoe UI", 8),
                     foreground=COLORS["text"] if done else COLORS["muted"]).grid(
                         row=1, column=i * 2)
            if i < len(labels) - 1:
                line = tk.Frame(track, height=3,
                                bg=COLORS["info"] if i < idx else COLORS["border"])
                line.grid(row=0, column=i * 2 + 1, sticky="ew")
                track.columnconfigure(i * 2 + 1, weight=1)

    def _next_step(self, status):
        i = self._FLOW.index(status)
        return self._FLOW[i + 1] if i + 1 < len(self._FLOW) else None

    def _advance(self, o, nxt):
        order_model.set_order_status(o["order_id"], nxt)
        msg = "Delivery completed! Earnings credited." if nxt == "delivered" \
            else f"Order #{o['order_id']} → {nxt.replace('_', ' ')}."
        self.notify(msg, "success")
        self.refresh()

    # =====================================================================
    # HISTORY
    # =====================================================================
    def _page_history(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Delivery History", "Your completed deliveries")
        hist = analytics_model.partner_history(self.partner["partner_id"])
        if not hist:
            self._empty(inner, "No completed deliveries yet.")
            return
        card = Card(inner); card.pack(fill="both", expand=True)
        tbl = DataTable(card, ["Order", "Shop", "Buyer", "Earning", "Date"],
                        widths={"Order": 70, "Shop": 180, "Buyer": 160,
                                "Earning": 100, "Date": 150}, height=16)
        tbl.pack(fill="both", expand=True)
        tbl.load([(f"#{o['order_id']}", o["shop_name"], o["buyer_name"],
                   f"Rs {o['delivery_fee']:,.0f}", o["placed_at"][:16])
                  for o in hist])

    # =====================================================================
    # EARNINGS
    # =====================================================================
    def _page_earnings(self, parent):
        inner = self.scroll_page(parent)
        t = analytics_model.partner_totals(self.partner["partner_id"])
        section_title(inner, "Earnings", "Track and withdraw your earnings")
        stat_row(inner, [
            {"title": "Total Earned", "value": f"Rs {t['earnings']:,.0f}",
             "icon": "💵", "accent": CARD_ACCENTS[1]},
            {"title": "Available Balance", "value": f"Rs {t['balance']:,.0f}",
             "icon": "🏦", "accent": CARD_ACCENTS[0]},
            {"title": "Deliveries", "value": t["delivered"], "icon": "✅",
             "accent": CARD_ACCENTS[2]},
        ])

        chart_card = Card(inner); chart_card.pack(fill="x", pady=(PAD_M, 0))
        section_title(chart_card, "Daily Earnings")
        series = analytics_model.partner_daily_earnings(self.partner["partner_id"])
        charts.bar_chart(chart_card, [r["day"][5:] for r in series],
                         [r["earnings"] for r in series], ylabel="Rs",
                         color=COLORS["info"]).pack(fill="x")

        wcard = Card(inner); wcard.pack(fill="x", pady=(PAD_M, 0))
        section_title(wcard, "Request Withdrawal")
        amt = Field(wcard, "Amount (Rs)", width=18); amt.pack(anchor="w", pady=PAD_S)

        def withdraw():
            ok, msg = validators.validate_positive_number(amt.get(), "Amount")
            if not ok:
                self.notify(msg, "warning"); return
            value = float(amt.get())
            if value <= 0 or value > t["balance"]:
                self.notify("Amount must be positive and within your balance.",
                            "warning"); return
            admin_model.request_payout(self.user["user_id"], value)
            self.notify("Withdrawal requested. Awaiting admin approval.", "success")
            self.refresh()
        tb.Button(wcard, text="Request Withdrawal", bootstyle="success",
                  command=withdraw).pack(anchor="w", pady=PAD_S)

    # =====================================================================
    # VEHICLE & ZONE
    # =====================================================================
    def _page_vehicle(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Vehicle & Zone", "Update your vehicle and delivery zone")
        card = Card(inner); card.pack(fill="x")
        col = field_column(card)

        vtypes = ["Motorbike", "Car", "Bicycle", "Van", "Rickshaw"]
        vt = Field(col, "Vehicle type", kind="combo", values=vtypes,
                   default=self.partner["vehicle_type"] or vtypes[0])
        vt.pack(fill="x", pady=PAD_S)
        plate = Field(col, "Vehicle plate",
                      default=self.partner["vehicle_plate"] or "")
        plate.pack(fill="x", pady=PAD_S)
        cities = user_model.get_cities()
        cmap = {c["name"]: c["city_id"] for c in cities}
        cur = next((c["name"] for c in cities
                    if c["city_id"] == self.partner["zone_city_id"]), cities[0]["name"])
        zone = Field(col, "Delivery zone (city)", kind="combo",
                     values=list(cmap.keys()), default=cur)
        zone.pack(fill="x", pady=PAD_S)

        def save():
            if not plate.get():
                self.notify("Vehicle plate is required.", "warning"); return
            admin_model.update_vehicle(self.partner["partner_id"], vt.get(),
                                       plate.get(), cmap[zone.get()])
            self.partner = analytics_model.partner_for_user(self.user["user_id"])
            self.notify("Vehicle & zone updated.", "success")
            self.refresh()
        tb.Button(col, text="Save Changes", bootstyle="primary",
                  command=save).pack(anchor="w", pady=(PAD_M, PAD_S))

    # --------------------------------------------------------------- helpers
    def _status_badge(self, parent, status):
        """A tinted status pill (shared component) for an order status."""
        return pill(parent, status.replace("_", " ").title(), status=status)

    def _empty(self, parent, message):
        box = tb.Frame(parent); box.pack(fill="both", expand=True, pady=PAD_L)
        tb.Label(box, text="📭", font=("Segoe UI", 40)).pack()
        tb.Label(box, text=message, font=FONTS["body"],
                 foreground=COLORS["muted"]).pack(pady=PAD_S)
