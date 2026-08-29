"""
views/seller_dashboard.py
================================================================================
The Seller experience. Pages: Overview (KPIs + revenue chart), Products (full
CRUD), Orders (accept/reject/fulfil), Inventory (low-stock + bulk update),
Analytics (best-sellers + category breakdown charts), Promotions (flash sales +
coupons), Reviews, Payouts and Shop Profile.

Everything funnels through the model layer; UI actions are wrapped so a raw
traceback is never shown, and forms are validated with friendly messages.
================================================================================
"""

import tkinter as tk
import ttkbootstrap as tb

from views.base_dashboard import BaseDashboard
from views.components import (Card, stat_row, section_title, Field, Modal,
                              DataTable, confirm, stars, pill, field_column, humanize)
from views import charts
from models import product_model, order_model, analytics_model, admin_model, user_model
from utils import validators
from utils.theme import COLORS, FONTS, PAD_S, PAD_M, PAD_L, CARD_ACCENTS


class SellerDashboard(BaseDashboard):
    """Dashboard shown to users with the 'seller' role."""

    ROLE_LABEL = "SELLER"
    ACCENT = COLORS["success"]
    NAV = [
        (None, None, "Store"),
        ("overview",  "📊", "Overview"),
        ("products",  "📦", "My Products"),
        ("inventory", "📥", "Inventory"),
        ("shop",      "🏪", "Shop Profile"),
        (None, None, "Sales"),
        ("orders",    "🧾", "Orders"),
        ("analytics", "📈", "Analytics"),
        ("promos",    "🎯", "Promotions"),
        (None, None, "Customers"),
        ("reviews",   "⭐", "Reviews"),
        ("messages",  "💬", "Messages"),
        ("payouts",   "💰", "Payouts"),
    ]

    def __init__(self, master, app, user):
        # Resolve the seller's shop once for the whole dashboard.
        self.shop = product_model.shop_for_seller(user["user_id"])
        super().__init__(master, app, user)

    def build_page(self, key, parent):
        if not self.shop:
            self._no_shop(parent)
            return
        {
            "overview": self._page_overview, "products": self._page_products,
            "orders": self._page_orders, "inventory": self._page_inventory,
            "analytics": self._page_analytics, "promos": self._page_promos,
            "reviews": self._page_reviews, "payouts": self._page_payouts,
            "messages": self._page_messages, "shop": self._page_shop,
        }[key](parent)

    def _no_shop(self, parent):
        box = self.scroll_page(parent)
        section_title(box, "No shop found",
                      "Your seller account has no shop record yet.")

    # =====================================================================
    # OVERVIEW
    # =====================================================================
    def _page_overview(self, parent):
        inner = self.scroll_page(parent)
        t = analytics_model.seller_totals(self.shop["shop_id"])
        section_title(inner, f"Welcome, {self.shop['shop_name']}",
                      "Your shop performance at a glance")
        stat_row(inner, [
            {"title": "Total Revenue", "value": f"Rs {t['revenue']:,.0f}",
             "icon": "💵", "accent": CARD_ACCENTS[1]},
            {"title": "This Month", "value": f"Rs {t['month_revenue']:,.0f}",
             "icon": "📅", "accent": CARD_ACCENTS[0]},
            {"title": "Total Orders", "value": t["orders"], "icon": "🧾",
             "accent": CARD_ACCENTS[2]},
            {"title": "Pending", "value": t["pending"], "icon": "⏳",
             "accent": CARD_ACCENTS[3]},
        ])
        stat_row(inner, [
            {"title": "Products Listed", "value": t["products"], "icon": "📦",
             "accent": CARD_ACCENTS[5]},
            {"title": "Available Balance", "value": f"Rs {t['balance']:,.0f}",
             "icon": "🏦", "accent": CARD_ACCENTS[1]},
            {"title": "Shop Rating", "value": stars(self.shop["rating"]),
             "icon": "⭐", "accent": CARD_ACCENTS[3]},
            {"title": "Verified",
             "value": "Yes ✔" if self.shop["is_verified"] else "Pending",
             "icon": "🛡️", "accent": CARD_ACCENTS[2]},
        ])

        # Revenue over time chart.
        chart_card = Card(inner); chart_card.pack(fill="x", pady=(PAD_M, 0))
        section_title(chart_card, "Revenue Over Time")
        series = analytics_model.seller_revenue_over_time(self.shop["shop_id"])
        days = [r["day"][5:] for r in series]
        vals = [r["revenue"] for r in series]
        charts.line_chart(chart_card, days, vals, ylabel="Rs",
                          color=COLORS["success"]).pack(fill="x")

    # =====================================================================
    # PRODUCTS (CRUD)
    # =====================================================================
    def _page_products(self, parent):
        inner = self.scroll_page(parent)
        head = tb.Frame(inner); head.pack(fill="x")
        section_title(head, "My Products", "Add, edit or remove products")
        tb.Button(head, text="+ Add Product", bootstyle="success",
                  command=lambda: self._product_modal(None)).pack(side="right")

        products = product_model.seller_products(self.shop["shop_id"])
        if not products:
            self._empty(inner, "No products yet. Add your first product.")
            return
        tbl = DataTable(inner, ["ID", "Name", "Category", "Price", "Stock",
                               "Status", "Rating"],
                        widths={"ID": 40, "Name": 220, "Category": 120,
                                "Price": 90, "Stock": 60, "Status": 90,
                                "Rating": 70}, height=14)
        tbl.pack(fill="both", expand=True, pady=(0, PAD_S))
        tbl.load([(p["product_id"], p["name"], p["category"],
                   f"Rs {p['price']:,.0f}", p["stock"], humanize(p["status"]),
                   f"{p['rating']:.1f}") for p in products])

        btns = tb.Frame(inner); btns.pack(fill="x")
        tb.Button(btns, text="Edit Selected", bootstyle="info",
                  command=lambda: self._edit_selected(tbl, products)).pack(side="left")
        tb.Button(btns, text="Delete Selected", bootstyle="danger",
                  command=lambda: self._delete_selected(tbl)).pack(side="left", padx=PAD_S)

    def _edit_selected(self, tbl, products):
        sel = tbl.selected()
        if not sel:
            self.notify("Select a product first.", "warning"); return
        prod = next((p for p in products if p["product_id"] == sel[0]), None)
        self._product_modal(dict(prod) if prod else None)

    def _delete_selected(self, tbl):
        sel = tbl.selected()
        if not sel:
            self.notify("Select a product first.", "warning"); return
        if not confirm(self.app.root, f"Delete '{sel[1]}'? This cannot be undone."):
            return
        product_model.delete_product(sel[0])
        self.notify("Product deleted.", "info")
        self.refresh()

    def _product_modal(self, prod):
        cats = user_model.get_categories()
        cmap = {c["name"]: c["category_id"] for c in cats}
        title = "Edit Product" if prod else "Add Product"
        dlg = Modal(self.app.root, title, width=500, height=600)
        b = dlg.body
        name = Field(b, "Product name", default=prod["name"] if prod else "")
        name.pack(fill="x", pady=PAD_S)
        cur_cat = next((c["name"] for c in cats
                        if prod and c["category_id"] == prod["category_id"]),
                       cats[0]["name"])
        catf = Field(b, "Category", kind="combo", values=list(cmap.keys()),
                     default=cur_cat, width=30)
        catf.pack(anchor="w", pady=PAD_S)
        desc = Field(b, "Description", kind="text",
                     default=prod["description"] if prod else "")
        desc.pack(fill="x", pady=PAD_S)
        row = tb.Frame(b); row.pack(fill="x", pady=PAD_S)
        price = Field(row, "Price (Rs)", default=prod["price"] if prod else "", width=14)
        price.pack(side="left", padx=(0, PAD_S))
        stock = Field(row, "Stock", default=prod["stock"] if prod else "", width=12)
        stock.pack(side="left", padx=(0, PAD_S))
        low = Field(row, "Low-stock at",
                    default=prod["low_stock_at"] if prod else "5", width=12)
        low.pack(side="left")

        def save():
            ok, msg = validators.validate_all(
                validators.validate_required(name.get(), "Name"),
                validators.validate_positive_number(price.get(), "Price"),
                validators.validate_positive_int(stock.get(), "Stock"),
                validators.validate_positive_int(low.get(), "Low-stock"))
            if not ok:
                self.notify(msg, "warning"); return
            cid = cmap[catf.get()]
            if prod:
                product_model.update_product(prod["product_id"], cid, name.get(),
                                             desc.get(), float(price.get()),
                                             int(stock.get()), int(low.get()))
                self.notify("Product updated.", "success")
            else:
                product_model.add_product(self.shop["shop_id"], cid, name.get(),
                                          desc.get(), float(price.get()),
                                          int(stock.get()), int(low.get()))
                self.notify("Product added.", "success")
            dlg.destroy(); self.refresh()

        tb.Button(b, text="Save Product", bootstyle="success",
                  command=save).pack(anchor="e", pady=PAD_M)

    # =====================================================================
    # ORDERS
    # =====================================================================
    def _page_orders(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Incoming Orders", "Accept, reject and fulfil orders — individually or in bulk")
        orders = [dict(o) for o in order_model.shop_orders(self.shop["shop_id"])]
        if not orders:
            self._empty(inner, "No orders yet.")
            return

        pending = [o for o in orders if o["status"] == "pending"]
        accepted = [o for o in orders if o["status"] == "accepted"]

        # ---- Bulk action bar ----
        bulk = Card(inner); bulk.pack(fill="x", pady=(0, PAD_S))
        brow = tb.Frame(bulk); brow.pack(fill="x")
        tb.Label(brow, text="⚡ Bulk actions", font=FONTS["h3"]).pack(side="left")
        tb.Label(brow, text=f"{len(pending)} pending · {len(accepted)} accepted",
                 font=FONTS["small"], foreground=COLORS["muted"]).pack(side="left", padx=PAD_M)
        tb.Button(brow, text=f"Accept all pending ({len(pending)})",
                  bootstyle="success" if pending else "secondary",
                  command=lambda: self._bulk_status(pending, "accepted"),
                  state="normal" if pending else "disabled").pack(side="right")
        tb.Button(brow, text=f"Assign all accepted ({len(accepted)})",
                  bootstyle="primary" if accepted else "secondary",
                  command=lambda: self._bulk_status(accepted, "assigned"),
                  state="normal" if accepted else "disabled").pack(side="right", padx=(0, PAD_S))

        for o in orders:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"Order #{o['order_id']}  ·  {o['buyer_name']}",
                     font=FONTS["h3"]).pack(side="left")
            self._status_badge(top, o["status"]).pack(side="right")
            tb.Label(c, text=f"{o['item_count']} item(s)  ·  Rs {o['total']:,.0f}"
                     f"  ·  {o['placed_at'][:16]}", font=FONTS["small"],
                     foreground=COLORS["muted"]).pack(anchor="w", pady=(2, PAD_S))

            act = tb.Frame(c); act.pack(fill="x")
            tb.Button(act, text="View Items", bootstyle="info-outline",
                      command=lambda o=o: self._items_modal(o)).pack(side="left")
            if o["status"] == "pending":
                tb.Button(act, text="Accept", bootstyle="success",
                          command=lambda o=o: self._set_status(o, "accepted")).pack(
                              side="right")
                tb.Button(act, text="Reject", bootstyle="danger-outline",
                          command=lambda o=o: self._set_status(o, "rejected")).pack(
                              side="right", padx=(0, PAD_S))
            elif o["status"] == "accepted":
                tb.Button(act, text="Mark Ready (Assign)", bootstyle="primary",
                          command=lambda o=o: self._set_status(o, "assigned")).pack(
                              side="right")

    def _bulk_status(self, orders, status):
        """Apply a status change to a batch of orders in one click."""
        if not orders:
            self.notify("Nothing to update.", "warning"); return
        count = 0
        for o in orders:
            try:
                order_model.set_order_status(o["order_id"], status)
                count += 1
            except Exception:
                pass
        self.notify(f"{count} order(s) → {status}.", "success")
        self.refresh()

    def _set_status(self, o, status):
        order_model.set_order_status(o["order_id"], status)
        self.notify(f"Order #{o['order_id']} → {status}.", "success")
        self.refresh()

    def _items_modal(self, o):
        dlg = Modal(self.app.root, f"Order #{o['order_id']} Items", width=480, height=420)
        items = order_model.order_items(o["order_id"])
        tbl = DataTable(dlg.body, ["Product", "Qty", "Unit Price", "Line Total"],
                        widths={"Product": 200, "Qty": 50, "Unit Price": 90,
                                "Line Total": 90}, height=8)
        tbl.pack(fill="both", expand=True)
        tbl.load([(i["name"], i["quantity"], f"Rs {i['unit_price']:,.0f}",
                   f"Rs {i['unit_price'] * i['quantity']:,.0f}") for i in items])

    # =====================================================================
    # INVENTORY
    # =====================================================================
    def _page_inventory(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Inventory Management",
                      "Monitor low stock and update quantities in bulk")
        low = product_model.low_stock_products(self.shop["shop_id"])
        if low:
            warn = Card(inner); warn.pack(fill="x", pady=(0, PAD_M))
            tb.Label(warn, text=f"⚠️  {len(low)} product(s) at or below low-stock level",
                     font=FONTS["h3"], foreground=COLORS["danger"]).pack(anchor="w")

        products = product_model.seller_products(self.shop["shop_id"])
        card = Card(inner); card.pack(fill="both", expand=True)
        section_title(card, "Update Stock")
        self._stock_fields = {}
        hdr = tb.Frame(card); hdr.pack(fill="x", pady=(0, PAD_S))
        tb.Label(hdr, text="Product", font=FONTS["small"], foreground=COLORS["muted"],
                 width=34, anchor="w").pack(side="left")
        tb.Label(hdr, text="Current", font=FONTS["small"], foreground=COLORS["muted"],
                 width=10, anchor="w").pack(side="left")
        tb.Label(hdr, text="New stock", font=FONTS["small"],
                 foreground=COLORS["muted"], anchor="w").pack(side="left")
        for p in products:
            r = tb.Frame(card); r.pack(fill="x", pady=2)
            flag = "🔴 " if p["stock"] <= p["low_stock_at"] else ""
            tb.Label(r, text=flag + p["name"], font=FONTS["body"], width=34,
                     anchor="w").pack(side="left")
            tb.Label(r, text=str(p["stock"]), font=FONTS["body"], width=10,
                     anchor="w").pack(side="left")
            f = Field(r, "", default=p["stock"], width=10)
            f.pack(side="left")
            self._stock_fields[p["product_id"]] = f
        tb.Button(card, text="Save All Stock", bootstyle="primary",
                  command=self._save_stock).pack(anchor="w", pady=PAD_M)

    def _save_stock(self):
        updated = 0
        for pid, f in self._stock_fields.items():
            ok, _ = validators.validate_positive_int(f.get(), "Stock")
            if ok:
                product_model.set_stock(pid, int(f.get()))
                updated += 1
        self.notify(f"Updated stock for {updated} product(s).", "success")
        self.refresh()

    # =====================================================================
    # ANALYTICS
    # =====================================================================
    def _page_analytics(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Sales Analytics",
                      "Best-sellers and category performance")

        best = analytics_model.seller_best_products(self.shop["shop_id"])
        left = Card(inner); left.pack(fill="x", pady=(0, PAD_M))
        section_title(left, "Best-Selling Products")
        if best:
            charts.bar_chart(left, [b["name"][:22] for b in best],
                             [b["units_sold"] for b in best],
                             xlabel="Units sold", color=COLORS["success"],
                             horizontal=True).pack(fill="x")
        else:
            tb.Label(left, text="No sales data yet.", foreground=COLORS["muted"]).pack()

        cat = analytics_model.seller_category_breakdown(self.shop["shop_id"])
        right = Card(inner); right.pack(fill="x")
        section_title(right, "Sales by Category")
        if cat:
            charts.pie_chart(right, [c["category"] for c in cat],
                             [c["units"] for c in cat]).pack(fill="x")
        else:
            tb.Label(right, text="No category sales yet.",
                     foreground=COLORS["muted"]).pack()

    # =====================================================================
    # PROMOTIONS (flash + coupons)
    # =====================================================================
    def _page_promos(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Promotions", "Run flash sales and create coupons")

        # ---- Flash sales ----
        flash_card = Card(inner); flash_card.pack(fill="x", pady=(0, PAD_M))
        section_title(flash_card, "Flash Sale Manager")
        products = product_model.seller_products(self.shop["shop_id"])
        for p in products:
            r = tb.Frame(flash_card); r.pack(fill="x", pady=3)
            tb.Label(r, text=p["name"], font=FONTS["body"], width=30,
                     anchor="w").pack(side="left")
            tb.Label(r, text=f"Rs {p['price']:,.0f}", font=FONTS["small"],
                     foreground=COLORS["muted"], width=12).pack(side="left")
            if p["is_flash"]:
                tb.Label(r, text=f"⚡ Rs {p['flash_price']:,.0f}", font=FONTS["small"],
                         foreground=COLORS["danger"], width=14).pack(side="left")
                tb.Button(r, text="End Flash", bootstyle="secondary-outline",
                          command=lambda p=p: self._end_flash(p)).pack(side="right")
            else:
                pf = Field(r, "", default=round(p["price"] * 0.8), width=10)
                pf.pack(side="left")
                tb.Button(r, text="Start Flash", bootstyle="danger-outline",
                          command=lambda p=p, pf=pf: self._start_flash(p, pf)).pack(
                              side="right")

        # ---- Coupons ----
        coup_card = Card(inner); coup_card.pack(fill="x")
        head = tb.Frame(coup_card); head.pack(fill="x")
        section_title(head, "My Coupons")
        tb.Button(head, text="+ New Coupon", bootstyle="success-outline",
                  command=self._coupon_modal).pack(side="right")
        coupons = [c for c in admin_model.all_coupons()
                   if c["shop_id"] == self.shop["shop_id"]]
        if not coupons:
            tb.Label(coup_card, text="No coupons yet.",
                     foreground=COLORS["muted"]).pack(anchor="w", pady=PAD_S)
        for c in coupons:
            r = tb.Frame(coup_card); r.pack(fill="x", pady=3)
            tb.Label(r, text=f"🎟️ {c['code']}  ·  {c['discount_pct']}% off"
                     f"  ·  min Rs {c['min_amount']:,.0f}", font=FONTS["body"]).pack(side="left")
            state = "Active" if c["is_active"] else "Inactive"
            tb.Label(r, text=state, font=FONTS["small"],
                     foreground=COLORS["success"] if c["is_active"] else COLORS["muted"]).pack(
                         side="right")

    def _start_flash(self, p, pf):
        ok, msg = validators.validate_positive_number(pf.get(), "Flash price")
        if not ok:
            self.notify(msg, "warning"); return
        fp = float(pf.get())
        if fp >= p["price"]:
            self.notify("Flash price must be below the normal price.", "warning"); return
        product_model.set_flash(p["product_id"], True, fp)
        self.notify(f"Flash sale started for {p['name']}.", "success")
        self.refresh()

    def _end_flash(self, p):
        product_model.set_flash(p["product_id"], False, None)
        self.notify("Flash sale ended.", "info")
        self.refresh()

    def _coupon_modal(self):
        dlg = Modal(self.app.root, "New Coupon", width=440, height=360)
        code = Field(dlg.body, "Coupon code (e.g. SAVE10)"); code.pack(fill="x", pady=PAD_S)
        pct = Field(dlg.body, "Discount %", default="10", width=12); pct.pack(anchor="w", pady=PAD_S)
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
                                            float(minamt.get()), self.shop["shop_id"])
            self.notify(m, "success" if okc else "danger")
            if okc:
                dlg.destroy(); self.refresh()
        tb.Button(dlg.body, text="Create Coupon", bootstyle="success",
                  command=save).pack(anchor="e", pady=PAD_M)

    # =====================================================================
    # REVIEWS
    # =====================================================================
    def _page_reviews(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Customer Reviews", "Feedback across all your products")
        products = product_model.seller_products(self.shop["shop_id"])
        any_rev = False
        for p in products:
            revs = product_model.get_reviews(p["product_id"])
            if not revs:
                continue
            any_rev = True
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            tb.Label(c, text=f"{p['name']}  ·  {stars(p['rating'])} "
                     f"({p['review_count']})", font=FONTS["h3"]).pack(anchor="w")
            for r in revs[:5]:
                rr = tb.Frame(c); rr.pack(fill="x", pady=2)
                tb.Label(rr, text=f"{stars(r['rating'])}  {r['full_name']}",
                         font=FONTS["small"], foreground=COLORS["warning"]).pack(anchor="w")
                if r["comment"]:
                    tb.Label(rr, text=r["comment"], font=FONTS["small"],
                             wraplength=620, justify="left").pack(anchor="w")
        if not any_rev:
            self._empty(inner, "No reviews on your products yet.")

    # =====================================================================
    # MESSAGES  — customer inquiries sent to this shop
    # =====================================================================
    def _page_messages(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "💬 Customer Messages",
                      "Inquiries from shoppers interested in your products")
        msgs = order_model.shop_messages(self.shop["shop_id"])
        if not msgs:
            self._empty(inner, "No customer messages yet.")
            return
        for m in msgs:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=m["buyer_name"], font=FONTS["h3"]).pack(side="left")
            tb.Label(top, text=str(m["created_at"])[:16], font=FONTS["small"],
                     foreground=COLORS["muted"]).pack(side="right")
            tb.Label(c, text=m["buyer_email"], font=FONTS["small"],
                     foreground=COLORS["primary"]).pack(anchor="w", pady=(1, PAD_S))
            tb.Label(c, text=m["body"], font=FONTS["body"], wraplength=860,
                     justify="left").pack(anchor="w")
            act = tb.Frame(c); act.pack(fill="x", pady=(PAD_S, 0))
            tb.Button(act, text="Reply", bootstyle="primary-outline",
                      command=lambda m=m: self._reply_modal(m)).pack(side="left")

    def _reply_modal(self, m):
        """Compose a reply that is delivered to the buyer as a notification."""
        dlg = Modal(self.app.root, f"Reply to {m['buyer_name']}",
                    width=520, height=360, accent=self.ACCENT)
        body = Field(dlg.body, "Your reply", kind="text", width=52)
        body.pack(fill="x", pady=(0, PAD_M))

        def send():
            text = body.get()
            if not text:
                self.notify("Please write a message first.", "warning")
                return
            try:
                user_model.add_notification(
                    m["buyer_id"],
                    f"Reply from {self.shop['shop_name']}: {text}")
            except Exception:
                pass
            dlg.destroy()
            self.notify("Reply sent to the customer.", "success")

        tb.Button(dlg.body, text="Send Reply", bootstyle="primary",
                  command=send).pack(anchor="e")

    # =====================================================================
    # PAYOUTS
    # =====================================================================
    def _page_payouts(self, parent):
        inner = self.scroll_page(parent)
        t = analytics_model.seller_totals(self.shop["shop_id"])
        section_title(inner, "Payouts", "Request withdrawals of your balance")
        stat_row(inner, [
            {"title": "Available Balance", "value": f"Rs {t['balance']:,.0f}",
             "icon": "🏦", "accent": CARD_ACCENTS[1]},
        ])
        card = Card(inner); card.pack(fill="x", pady=(PAD_M, 0))
        section_title(card, "Request a Payout")
        amt = Field(card, "Amount (Rs)", width=18); amt.pack(anchor="w", pady=PAD_S)

        def req():
            ok, msg = validators.validate_positive_number(amt.get(), "Amount")
            if not ok:
                self.notify(msg, "warning"); return
            value = float(amt.get())
            if value <= 0 or value > t["balance"]:
                self.notify("Amount must be positive and within your balance.",
                            "warning"); return
            admin_model.request_payout(self.user["user_id"], value)
            self.notify("Payout requested. Awaiting admin approval.", "success")
            self.refresh()
        tb.Button(card, text="Request Payout", bootstyle="success",
                  command=req).pack(anchor="w", pady=PAD_S)

        hist = [p for p in admin_model.all_payouts()
                if p["user_id"] == self.user["user_id"]]
        hcard = Card(inner); hcard.pack(fill="both", expand=True, pady=(PAD_M, 0))
        section_title(hcard, "Payout History")
        if not hist:
            tb.Label(hcard, text="No payout requests yet.",
                     foreground=COLORS["muted"]).pack(anchor="w")
        else:
            tbl = DataTable(hcard, ["ID", "Amount", "Status", "Requested"],
                            widths={"ID": 50, "Amount": 120, "Status": 100,
                                    "Requested": 160}, height=8)
            tbl.pack(fill="both", expand=True)
            tbl.load([(p["payout_id"], f"Rs {p['amount']:,.0f}", p["status"],
                       p["requested_at"][:16]) for p in hist])

    # =====================================================================
    # SHOP PROFILE
    # =====================================================================
    def _page_shop(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Shop Profile", "Your storefront details")

        # Banner preview with chosen colour.
        banner = tk.Frame(inner, bg=self.shop["banner_color"] or COLORS["primary"],
                          height=90)
        banner.pack(fill="x", pady=(0, PAD_M)); banner.pack_propagate(False)
        tk.Label(banner, text="🏪  " + self.shop["shop_name"],
                 font=("Segoe UI", 18, "bold"), fg="white",
                 bg=self.shop["banner_color"] or COLORS["primary"]).pack(
                     side="left", padx=PAD_L, pady=PAD_L)

        card = Card(inner); card.pack(fill="x")
        col = field_column(card, width=520)
        name = Field(col, "Shop name", default=self.shop["shop_name"])
        name.pack(fill="x", pady=PAD_S)
        desc = Field(col, "Description", kind="text",
                     default=self.shop["description"])
        desc.pack(fill="x", pady=PAD_S)
        colors = ["#4e73df", "#1cc88a", "#36b9cc", "#f6c23e", "#e74a3b", "#6f42c1"]
        colf = Field(col, "Banner colour", kind="combo", values=colors,
                     default=self.shop["banner_color"] or colors[0])
        colf.pack(fill="x", pady=PAD_S)

        def save():
            if not name.get():
                self.notify("Shop name is required.", "warning"); return
            from database.db_manager import db
            db.execute("UPDATE shops SET shop_name=?, description=?, banner_color=? "
                       "WHERE shop_id=?",
                       (name.get(), desc.get(), colf.get(), self.shop["shop_id"]))
            self.shop = product_model.shop_for_seller(self.user["user_id"])
            self.notify("Shop profile updated.", "success")
            self.refresh()
        tb.Button(col, text="Save Shop", bootstyle="primary",
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
