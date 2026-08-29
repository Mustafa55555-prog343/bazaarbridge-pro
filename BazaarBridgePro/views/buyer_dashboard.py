"""
views/buyer_dashboard.py
================================================================================
The Buyer experience. Pages: Browse (live search + filters), Flash Sale,
Recommendations, Cart + Checkout, Orders (with tracking, cancel, return),
Wishlist, Compare, Notifications and Profile/Addresses.

Every action is wrapped so the UI never shows a raw traceback, every form is
validated, and all data flows through the model layer (which uses transactions,
triggers and joins under the hood).
================================================================================
"""

import tkinter as tk
import ttkbootstrap as tb

from views.base_dashboard import BaseDashboard
from views.components import (Card, stat_row, section_title, Field, Modal,
                              ProductCard, card_grid, stars, confirm, toast,
                              DataTable, pill, field_column)
from models import product_model, order_model, user_model, analytics_model
from views import charts
from utils import validators
from utils.theme import COLORS, FONTS, PAD_S, PAD_M, PAD_L, CARD_ACCENTS


class BuyerDashboard(BaseDashboard):
    """Dashboard shown to users with the 'buyer' role."""

    ROLE_LABEL = "BUYER"
    ACCENT = COLORS["primary"]
    NAV = [
        (None, None, "Shop"),
        ("browse",   "🛒", "Browse Products"),
        ("flash",    "⚡", "Flash Sale"),
        ("recommend","✨", "For You"),
        ("compare",  "⚖️", "Compare"),
        ("wishlist", "❤️", "Wishlist"),
        (None, None, "My Account"),
        ("cart",     "🧺", "My Cart"),
        ("orders",   "📦", "My Orders"),
        ("spending", "📈", "Spending"),
        ("alerts",   "🔔", "Notifications"),
        ("profile",  "👤", "Profile"),
    ]

    def __init__(self, master, app, user):
        self._compare_ids = []
        super().__init__(master, app, user)

    # ------------------------------------------------------------- routing
    def build_page(self, key, parent):
        builder = {
            "browse": self._page_browse, "flash": self._page_flash,
            "recommend": self._page_recommend, "cart": self._page_cart,
            "orders": self._page_orders, "wishlist": self._page_wishlist,
            "compare": self._page_compare, "alerts": self._page_alerts,
            "spending": self._page_spending, "profile": self._page_profile,
        }[key]
        builder(parent)

    # =====================================================================
    # BROWSE
    # =====================================================================
    def _page_browse(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Browse the Marketplace",
                      "Search and filter products from sellers across Pakistan")

        # ---- Filter bar ----
        bar = Card(inner)
        bar.pack(fill="x", pady=(0, PAD_M))
        row1 = tb.Frame(bar); row1.pack(fill="x")
        self.f_search = Field(row1, "Search", width=26)
        self.f_search.pack(side="left", padx=(0, PAD_S))

        cats = [("All categories", None)] + [(c["name"], c["category_id"])
                                             for c in user_model.get_categories()]
        cities = [("All cities", None)] + [(c["name"], c["city_id"])
                                          for c in user_model.get_cities()]
        self._cat_map = dict(cats); self._city_map = dict(cities)
        self.f_cat = Field(row1, "Category", kind="combo",
                           values=[c[0] for c in cats], default="All categories", width=18)
        self.f_cat.pack(side="left", padx=(0, PAD_S))
        self.f_city = Field(row1, "City", kind="combo",
                            values=[c[0] for c in cities], default="All cities", width=16)
        self.f_city.pack(side="left", padx=(0, PAD_S))

        row2 = tb.Frame(bar); row2.pack(fill="x", pady=(PAD_S, 0))
        self.f_min = Field(row2, "Min price", width=12); self.f_min.pack(side="left", padx=(0, PAD_S))
        self.f_max = Field(row2, "Max price", width=12); self.f_max.pack(side="left", padx=(0, PAD_S))
        self.f_rating = Field(row2, "Min seller rating", kind="combo",
                              values=["Any", "3", "4", "4.5"], default="Any", width=14)
        self.f_rating.pack(side="left", padx=(0, PAD_S))
        btnbox = tb.Frame(row2); btnbox.pack(side="left", padx=(PAD_S, 0), pady=(PAD_M, 0))
        tb.Button(btnbox, text="Apply Filters", bootstyle="primary",
                  command=lambda: self._render_browse(inner)).pack(side="left")
        tb.Button(btnbox, text="Reset", bootstyle="secondary",
                  command=lambda: self._reset_browse(inner)).pack(side="left", padx=(PAD_S, 0))
        self.f_search.widget.bind("<Return>", lambda e: self._render_browse(inner))

        self._browse_holder = tb.Frame(inner)
        self._browse_holder.pack(fill="both", expand=True, pady=(PAD_M, 0))
        self._render_browse(inner)

    def _reset_browse(self, inner):
        self.f_search.set(""); self.f_cat.set("All categories")
        self.f_city.set("All cities"); self.f_min.set(""); self.f_max.set("")
        self.f_rating.set("Any")
        self._render_browse(inner)

    def _render_browse(self, inner):
        for w in self._browse_holder.winfo_children():
            w.destroy()
        try:
            min_p = float(self.f_min.get()) if self.f_min.get() else None
            max_p = float(self.f_max.get()) if self.f_max.get() else None
        except ValueError:
            self.notify("Price filters must be numbers.", "warning"); return
        rating = None if self.f_rating.get() == "Any" else float(self.f_rating.get())
        products = product_model.browse_products(
            search=self.f_search.get(),
            category_id=self._cat_map.get(self.f_cat.get()),
            city_id=self._city_map.get(self.f_city.get()),
            min_price=min_p, max_price=max_p, min_rating=rating)

        tb.Label(self._browse_holder, text=f"{len(products)} product(s) found",
                 font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w",
                 pady=(0, PAD_S))
        if not products:
            self._empty(self._browse_holder, "No products match your filters.")
            return
        card_grid(self._browse_holder, [dict(p) for p in products],
                  lambda cell, p: ProductCard(
                      cell, p, on_open=self._open_product,
                      action_label="Add to Cart",
                      on_action=self._add_to_cart).pack(fill="both", expand=True),
                  columns=4)

    # =====================================================================
    # FLASH SALE
    # =====================================================================
    def _page_flash(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "⚡ Flash Sale", "Limited-time deals — grab them before the timer runs out")
        products = [dict(p) for p in product_model.flash_sale_products()]
        if not products:
            self._empty(inner, "No flash deals right now. Check back soon!")
            return

        def build_flash_cell(cell, p):
            wrap = tb.Frame(cell, bootstyle="light")
            wrap.pack(fill="both", expand=True)
            # Live countdown banner above each product card.
            timer = tk.Label(wrap, text="", font=("Segoe UI", 10, "bold"),
                             bg=COLORS["danger"], fg="white", pady=4)
            timer.pack(fill="x")
            self._start_countdown(timer, p.get("flash_ends_at"))
            ProductCard(wrap, p, on_open=self._open_product,
                        action_label="Add to Cart",
                        on_action=self._add_to_cart).pack(fill="both", expand=True)

        card_grid(inner, products, build_flash_cell, columns=4)

    def _start_countdown(self, label, ends_at):
        """Tick a flash-sale countdown label every second until it expires."""
        from datetime import datetime
        try:
            end = datetime.strptime(str(ends_at), "%Y-%m-%d %H:%M:%S") if ends_at else None
        except ValueError:
            end = None

        def tick():
            if not label.winfo_exists():
                return                         # page was navigated away — stop
            if not end:
                label.configure(text="⚡ Limited time only")
                return
            remaining = end - datetime.now()
            secs = int(remaining.total_seconds())
            if secs <= 0:
                label.configure(text="⌛ Deal ended", bg=COLORS["muted"])
                return
            h, rem = divmod(secs, 3600)
            m, s = divmod(rem, 60)
            d, h = divmod(h, 24)
            txt = f"⏳ {d}d {h:02d}:{m:02d}:{s:02d}" if d else f"⏳ {h:02d}:{m:02d}:{s:02d}"
            label.configure(text=txt + " left")
            label.after(1000, tick)
        tick()

    # =====================================================================
    # RECOMMENDATIONS
    # =====================================================================
    def _page_recommend(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "✨ Recommended For You",
                      "Picked from categories you've shopped and wishlisted")
        products = [dict(p) for p in
                    product_model.recommended_for(self.user["user_id"])]
        if not products:
            self._empty(inner, "Browse a few products and we'll tailor picks for you.")
            return
        card_grid(inner, products,
                  lambda cell, p: ProductCard(
                      cell, p, on_open=self._open_product,
                      action_label="Add to Cart",
                      on_action=self._add_to_cart).pack(fill="both", expand=True),
                  columns=4)

    # =====================================================================
    # CART + CHECKOUT
    # =====================================================================
    def _page_cart(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "My Cart", "Review items and check out securely")
        cart = [dict(i) for i in order_model.get_cart(self.user["user_id"])]
        if not cart:
            self._empty(inner, "Your cart is empty. Browse products to add items.")
            return

        subtotal = sum(i["line_total"] for i in cart)
        for item in cart:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            row = tb.Frame(c); row.pack(fill="x")
            info = tb.Frame(row); info.pack(side="left", fill="x", expand=True)
            tb.Label(info, text=item["name"], font=FONTS["h3"]).pack(anchor="w")
            tb.Label(info, text=f"{item['shop_name']}  ·  Rs {item['unit_price']:,.0f} each",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w")

            qty = tb.Frame(row); qty.pack(side="left", padx=PAD_L)
            tb.Button(qty, text="−", width=3, bootstyle="secondary-outline",
                      command=lambda i=item: self._change_qty(i, -1)).pack(side="left")
            tb.Label(qty, text=str(item["quantity"]), font=FONTS["h3"],
                     width=3, anchor="center").pack(side="left")
            tb.Button(qty, text="+", width=3, bootstyle="secondary-outline",
                      command=lambda i=item: self._change_qty(i, 1)).pack(side="left")

            tb.Label(row, text=f"Rs {item['line_total']:,.0f}", font=FONTS["h3"],
                     foreground=COLORS["primary"], width=12,
                     anchor="e").pack(side="left", padx=PAD_M)
            tb.Button(row, text="Remove", bootstyle="danger-outline",
                      command=lambda i=item: self._remove_cart(i)).pack(side="left")

        # ---- Summary / checkout panel ----
        summary = Card(inner); summary.pack(fill="x", pady=(PAD_L, 0))
        section_title(summary, "Order Summary")
        addresses = user_model.get_addresses(self.user["user_id"])
        self._addr_map = {f"{a['label']} — {a['line1']}": a["address_id"]
                          for a in addresses}
        arow = tb.Frame(summary); arow.pack(fill="x", pady=PAD_S)
        if addresses:
            self.f_addr = Field(arow, "Deliver to", kind="combo",
                                values=list(self._addr_map.keys()),
                                default=list(self._addr_map.keys())[0], width=40)
            self.f_addr.pack(side="left")
        else:
            tb.Label(arow, text="⚠️ Add a delivery address in Profile first.",
                     foreground=COLORS["danger"]).pack(side="left")

        crow = tb.Frame(summary); crow.pack(fill="x", pady=PAD_S)
        self.f_coupon = Field(crow, "Coupon code", width=20)
        self.f_coupon.pack(side="left", padx=(0, PAD_S))
        tb.Button(crow, text="Apply", bootstyle="info-outline",
                  command=lambda: self._apply_coupon(cart)).pack(side="left", pady=(PAD_M, 0))

        # ---- Loyalty redemption (1 point = Rs 1) ----
        pts = self.user.get("loyalty_points", 0)
        self._redeem = 0
        lrow = tb.Frame(summary); lrow.pack(fill="x", pady=PAD_S)
        self.f_redeem = Field(lrow, f"Redeem loyalty points (you have {pts:,})",
                              kind="spin", width=18, default=0)
        self.f_redeem.widget.configure(to=int(pts))
        self.f_redeem.pack(side="left", padx=(0, PAD_S))
        tb.Button(lrow, text="Apply Points", bootstyle="warning-outline",
                  command=lambda: self._apply_points(cart)).pack(side="left", pady=(PAD_M, 0))

        self._discount = 0
        self._totals_box = tb.Frame(summary); self._totals_box.pack(fill="x", pady=PAD_S)
        self._render_totals(subtotal)

        tb.Button(summary, text="Place Order", bootstyle="success",
                  command=lambda: self._checkout(addresses)).pack(anchor="e", pady=(PAD_M, 0))

    def _render_totals(self, subtotal):
        for w in self._totals_box.winfo_children():
            w.destroy()
        delivery = 150
        redeem = getattr(self, "_redeem", 0)
        total = max(0, subtotal - self._discount - redeem) + delivery
        rows = [("Subtotal", subtotal, False), ("Discount", -self._discount, False)]
        if redeem:
            rows.append(("Loyalty points", -redeem, False))
        rows += [("Delivery", delivery, False), ("Total", total, True)]
        for label, val, bold in rows:
            r = tb.Frame(self._totals_box); r.pack(fill="x", pady=1)
            font = FONTS["h3"] if bold else FONTS["body"]
            tb.Label(r, text=label, font=font).pack(side="left")
            tb.Label(r, text=f"Rs {val:,.0f}", font=font,
                     foreground=COLORS["primary"] if bold else COLORS["text"]).pack(side="right")

    def _apply_points(self, cart):
        """Validate and apply a loyalty-point redemption to the order total."""
        subtotal = sum(i["line_total"] for i in cart)
        try:
            want = int(self.f_redeem.get() or 0)
        except ValueError:
            self.notify("Enter a whole number of points.", "warning"); return
        available = int(self.user.get("loyalty_points", 0))
        cap = max(0, subtotal - self._discount)
        self._redeem = max(0, min(want, available, cap))
        if want > available:
            self.notify(f"You only have {available:,} points.", "warning")
        elif self._redeem:
            self.notify(f"Applied {self._redeem:,} points (Rs {self._redeem:,} off).", "success")
        self._render_totals(subtotal)

    def _apply_coupon(self, cart):
        code = self.f_coupon.get()
        if not code:
            return
        subtotal = sum(i["line_total"] for i in cart)
        shop_id = cart[0]["shop_id"]
        coupon, msg = order_model.validate_coupon(code, subtotal, shop_id)
        if not coupon:
            self._discount = 0
            self.notify(msg, "warning")
        else:
            self._discount = round(subtotal * coupon["discount_pct"] / 100)
            self.notify(msg, "success")
        self._render_totals(subtotal)

    def _change_qty(self, item, delta):
        new_q = item["quantity"] + delta
        if new_q <= 0:
            order_model.remove_cart_item(item["cart_item_id"])
        elif new_q > item["stock"]:
            self.notify(f"Only {item['stock']} in stock.", "warning")
            return
        else:
            order_model.update_cart_quantity(item["cart_item_id"], new_q)
        self.refresh()

    def _remove_cart(self, item):
        order_model.remove_cart_item(item["cart_item_id"])
        self.notify("Removed from cart.", "info")
        self.refresh()

    def _checkout(self, addresses):
        try:
            if not addresses:
                self.notify("Please add a delivery address first.", "warning")
                return
            address_id = self._addr_map[self.f_addr.get()]
            code = self.f_coupon.get() or None
            redeem = getattr(self, "_redeem", 0)
            ok, msg, ids = order_model.checkout(self.user["user_id"], address_id, code, redeem)
            self.notify(msg, "success" if ok else "danger")
            if ok:
                # Refresh the in-memory user so the new points balance shows.
                fresh = user_model.get_user(self.user["user_id"])
                if fresh:
                    self.user["loyalty_points"] = fresh["loyalty_points"]
                self._redeem = 0
                self.refresh()
        except Exception:
            self.notify("Checkout could not be completed.", "danger")

    # =====================================================================
    # ORDERS
    # =====================================================================
    _STATUS_STEPS = ["pending", "accepted", "assigned", "picked_up",
                     "in_transit", "delivered"]

    def _page_orders(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "My Orders", "Track, cancel or return your orders")
        orders = [dict(o) for o in order_model.buyer_orders(self.user["user_id"])]
        if not orders:
            self._empty(inner, "You haven't placed any orders yet.")
            return
        for o in orders:
            c = Card(inner); c.pack(fill="x", pady=PAD_S)
            top = tb.Frame(c); top.pack(fill="x")
            tb.Label(top, text=f"Order #{o['order_id']}  ·  {o['shop_name']}",
                     font=FONTS["h3"]).pack(side="left")
            self._status_badge(top, o["status"]).pack(side="right")

            tb.Label(c, text=f"{o['item_count']} item(s)  ·  Placed {o['placed_at'][:16]}",
                     font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w",
                     pady=(2, PAD_S))

            # Status tracker (skip for cancelled/returned/rejected).
            if o["status"] in self._STATUS_STEPS:
                self._tracker(c, o["status"])

            actions = tb.Frame(c); actions.pack(fill="x", pady=(PAD_S, 0))
            tb.Label(actions, text=f"Total: Rs {o['total']:,.0f}", font=FONTS["h3"],
                     foreground=COLORS["primary"]).pack(side="left")
            tb.Button(actions, text="View Items", bootstyle="info-outline",
                      command=lambda o=o: self._order_items_modal(o)).pack(side="right")
            if o["status"] in ("pending", "accepted"):
                tb.Button(actions, text="Cancel", bootstyle="danger-outline",
                          command=lambda o=o: self._cancel_order(o)).pack(
                              side="right", padx=(0, PAD_S))
            if o["status"] == "delivered":
                tb.Button(actions, text="Return", bootstyle="warning-outline",
                          command=lambda o=o: self._return_modal(o)).pack(
                              side="right", padx=(0, PAD_S))
                tb.Button(actions, text="Review", bootstyle="success-outline",
                          command=lambda o=o: self._review_modal(o)).pack(
                              side="right", padx=(0, PAD_S))

    def _tracker(self, parent, status):
        """Horizontal step tracker for the order lifecycle."""
        idx = self._STATUS_STEPS.index(status)
        track = tb.Frame(parent); track.pack(fill="x", pady=PAD_S)
        labels = ["Placed", "Accepted", "Assigned", "Picked Up", "In Transit", "Delivered"]
        for i, lbl in enumerate(labels):
            done = i <= idx
            dot = tk.Canvas(track, width=22, height=22, highlightthickness=0,
                            bg=COLORS["card"])
            col = COLORS["success"] if done else COLORS["border"]
            dot.create_oval(3, 3, 19, 19, fill=col, outline="")
            if done:
                dot.create_text(11, 11, text="✓", fill="white",
                                font=("Segoe UI", 9, "bold"))
            dot.grid(row=0, column=i * 2, padx=0)
            tb.Label(track, text=lbl, font=("Segoe UI", 8),
                     foreground=COLORS["text"] if done else COLORS["muted"]).grid(
                         row=1, column=i * 2)
            if i < len(labels) - 1:
                line = tk.Frame(track, height=3,
                                bg=COLORS["success"] if i < idx else COLORS["border"])
                line.grid(row=0, column=i * 2 + 1, sticky="ew")
                track.columnconfigure(i * 2 + 1, weight=1)

    def _order_items_modal(self, o):
        dlg = Modal(self.app.root, f"Order #{o['order_id']} Items", width=480, height=420)
        items = order_model.order_items(o["order_id"])
        tbl = DataTable(dlg.body, ["Product", "Qty", "Unit Price", "Line Total"],
                        widths={"Product": 200, "Qty": 50, "Unit Price": 90,
                                "Line Total": 90}, height=8)
        tbl.pack(fill="both", expand=True)
        tbl.load([(i["name"], i["quantity"], f"Rs {i['unit_price']:,.0f}",
                   f"Rs {i['unit_price'] * i['quantity']:,.0f}") for i in items])

    def _cancel_order(self, o):
        if not confirm(self.app.root, f"Cancel order #{o['order_id']}?"):
            return
        ok, msg = order_model.cancel_order(o["order_id"], self.user["user_id"])
        self.notify(msg, "success" if ok else "warning")
        self.refresh()

    def _return_modal(self, o):
        dlg = Modal(self.app.root, f"Return Order #{o['order_id']}", width=460, height=320)
        reason = Field(dlg.body, "Reason for return", kind="text", width=44)
        reason.pack(fill="x", pady=PAD_S)

        def submit():
            if not reason.get():
                self.notify("Please describe the reason.", "warning"); return
            ok, msg = order_model.request_return(o["order_id"], self.user["user_id"],
                                                 reason.get())
            self.notify(msg, "success" if ok else "warning")
            dlg.destroy(); self.refresh()
        tb.Button(dlg.body, text="Submit Return", bootstyle="warning",
                  command=submit).pack(anchor="e", pady=PAD_M)

    def _review_modal(self, o):
        items = order_model.order_items(o["order_id"])
        dlg = Modal(self.app.root, f"Review — Order #{o['order_id']}", width=480, height=420)
        prod_map = {i["name"]: i["product_id"] for i in items}
        pf = Field(dlg.body, "Product", kind="combo", values=list(prod_map.keys()),
                   default=list(prod_map.keys())[0], width=44)
        pf.pack(fill="x", pady=PAD_S)
        rf = Field(dlg.body, "Rating", kind="combo", values=["5", "4", "3", "2", "1"],
                   default="5", width=10)
        rf.pack(anchor="w", pady=PAD_S)
        cf = Field(dlg.body, "Comment", kind="text", width=44)
        cf.pack(fill="x", pady=PAD_S)

        def submit():
            pid = prod_map[pf.get()]
            ok, msg = product_model.add_review(self.user["user_id"], pid,
                                               int(rf.get()), cf.get())
            self.notify(msg, "success" if ok else "warning")
            dlg.destroy()
        tb.Button(dlg.body, text="Submit Review", bootstyle="success",
                  command=submit).pack(anchor="e", pady=PAD_M)

    # =====================================================================
    # WISHLIST
    # =====================================================================
    def _page_wishlist(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "My Wishlist", "Products you've saved for later")
        items = [dict(p) for p in product_model.get_wishlist(self.user["user_id"])]
        if not items:
            self._empty(inner, "Your wishlist is empty. Tap the heart on any product.")
            return
        card_grid(inner, items,
                  lambda cell, p: ProductCard(
                      cell, p, on_open=self._open_product,
                      action_label="Add to Cart",
                      on_action=self._add_to_cart).pack(fill="both", expand=True),
                  columns=4)

    # =====================================================================
    # COMPARE
    # =====================================================================
    def _page_compare(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "Compare Products",
                      "Add products from their detail page to compare side by side")
        if not self._compare_ids:
            self._empty(inner, "No products selected. Open a product and tap 'Compare'.")
            return
        rows = product_model.compare_products(self._compare_ids)
        attrs = [("Name", "name"), ("Category", "category"), ("Shop", "shop_name"),
                 ("Price", "price"), ("Rating", "rating"), ("Stock", "stock")]
        card = Card(inner); card.pack(fill="x")
        grid = tb.Frame(card); grid.pack(fill="x")
        tb.Label(grid, text="Attribute", font=FONTS["h3"]).grid(row=0, column=0,
                 sticky="w", padx=PAD_M, pady=PAD_S)
        for j, p in enumerate(rows):
            tb.Label(grid, text=p["name"], font=FONTS["h3"],
                     foreground=COLORS["primary"]).grid(row=0, column=j + 1,
                     sticky="w", padx=PAD_M, pady=PAD_S)
        for i, (label, key) in enumerate(attrs[1:], start=1):
            tb.Label(grid, text=label, font=FONTS["body"],
                     foreground=COLORS["muted"]).grid(row=i, column=0, sticky="w",
                     padx=PAD_M, pady=4)
            for j, p in enumerate(rows):
                val = p[key]
                if key == "price":
                    val = f"Rs {val:,.0f}"
                elif key == "rating":
                    val = stars(val)
                tb.Label(grid, text=str(val), font=FONTS["body"]).grid(
                    row=i, column=j + 1, sticky="w", padx=PAD_M, pady=4)
        tb.Button(inner, text="Clear Comparison", bootstyle="secondary",
                  command=self._clear_compare).pack(anchor="w", pady=PAD_M)

    def _clear_compare(self):
        self._compare_ids = []
        self.notify("Comparison cleared.", "info")
        self.refresh()

    # =====================================================================
    # NOTIFICATIONS
    # =====================================================================
    def _page_alerts(self, parent):
        inner = self.scroll_page(parent)
        head = tb.Frame(inner); head.pack(fill="x")
        section_title(head, "Notifications", "Order updates and alerts")
        tb.Button(head, text="Mark all read", bootstyle="secondary-outline",
                  command=self._mark_read).pack(side="right")
        notes = user_model.get_notifications(self.user["user_id"])
        if not notes:
            self._empty(inner, "No notifications yet.")
            return
        for n in notes:
            c = Card(inner); c.pack(fill="x", pady=4)
            row = tb.Frame(c); row.pack(fill="x")
            dot = "🔵" if not n["is_read"] else "⚪"
            tb.Label(row, text=dot, font=("Segoe UI", 10)).pack(side="left", padx=(0, PAD_S))
            tb.Label(row, text=n["message"], font=FONTS["body"],
                     wraplength=620, justify="left").pack(side="left")
            tb.Label(row, text=n["created_at"][:16], font=FONTS["small"],
                     foreground=COLORS["muted"]).pack(side="right")

    def _mark_read(self):
        user_model.mark_notifications_read(self.user["user_id"])
        self.app.update_badge()
        self.refresh()

    # =====================================================================
    # =====================================================================
    # SPENDING  — the buyer's personal spending analytics
    # =====================================================================
    def _page_spending(self, parent):
        inner = self.scroll_page(parent)
        section_title(inner, "📈 My Spending",
                      "Track where your money goes across BazaarBridge")
        s = analytics_model.buyer_spending(self.user["user_id"])

        stat_row(inner, [
            {"title": "Total Spent", "value": f"Rs {s['spent']:,.0f}", "icon": "💸",
             "gradient": "indigo"},
            {"title": "Orders", "value": f"{s['orders']:,}", "icon": "📦",
             "gradient": "emerald"},
            {"title": "Avg Order", "value": f"Rs {s['avg_order']:,.0f}", "icon": "🧾",
             "gradient": "sky"},
            {"title": "Loyalty Points", "value": f"{s['loyalty']:,}", "icon": "⭐",
             "gradient": "amber"},
        ])

        if not s["monthly"] and not s["by_cat"]:
            self._empty(inner, "No spending yet. Place an order to see your analytics here.")
            return

        two = tb.Frame(inner); two.pack(fill="x")
        two.columnconfigure(0, weight=3, uniform="sp")
        two.columnconfigure(1, weight=2, uniform="sp")

        left = Card(two); left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        section_title(left, "Monthly Spending")
        if s["monthly"]:
            _mn = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            def _mlabel(m):
                try:
                    y, mo = str(m).split("-")
                    return f"{_mn[int(mo)]} {y[2:]}"
                except Exception:
                    return str(m)
            charts.line_chart(left, [_mlabel(m["month"]) for m in s["monthly"]],
                              [m["spent"] for m in s["monthly"]], ylabel="Rs",
                              xlabel="Month", color=COLORS["primary"]).pack(fill="x")
        else:
            tb.Label(left, text="No data yet.", foreground=COLORS["muted"]).pack(anchor="w")

        right = Card(two); right.grid(row=0, column=1, sticky="nsew", padx=(PAD_S, 0))
        section_title(right, "By Category")
        if s["by_cat"]:
            top = s["by_cat"][:8]
            charts.pie_chart(right, [c["category"] for c in top],
                             [c["spent"] for c in top]).pack(fill="x")
        else:
            tb.Label(right, text="No data yet.", foreground=COLORS["muted"]).pack(anchor="w")

        # Category breakdown table
        if s["by_cat"]:
            tbl_card = Card(inner); tbl_card.pack(fill="both", expand=True, pady=(PAD_M, 0))
            section_title(tbl_card, "Spending Breakdown")
            table = DataTable(tbl_card, ["Category", "Spent", "Share"],
                              widths={"Category": 260, "Spent": 140, "Share": 120},
                              height=min(10, len(s["by_cat"])))
            table.pack(fill="both", expand=True)
            total = sum(c["spent"] for c in s["by_cat"]) or 1
            table.load([(c["category"], f"Rs {c['spent']:,.0f}",
                         f"{c['spent']/total*100:.1f}%") for c in s["by_cat"]])

    # =====================================================================
    # PROFILE + ADDRESSES + LOYALTY
    # =====================================================================
    def _page_profile(self, parent):
        inner = self.scroll_page(parent)
        u = user_model.get_user(self.user["user_id"])
        section_title(inner, "My Profile", "Manage your details, addresses and loyalty")

        stat_row(inner, [
            {"title": "Loyalty Points", "value": u["loyalty_points"], "icon": "⭐",
             "accent": CARD_ACCENTS[3]},
            {"title": "Saved Addresses",
             "value": len(user_model.get_addresses(self.user["user_id"])),
             "icon": "📍", "accent": CARD_ACCENTS[1]},
            {"title": "Orders Placed",
             "value": len(order_model.buyer_orders(self.user["user_id"])),
             "icon": "📦", "accent": CARD_ACCENTS[2]},
        ])

        # ---- Editable details ----
        card = Card(inner); card.pack(fill="x", pady=(PAD_M, 0))
        section_title(card, "Personal Details")
        col = field_column(card)
        self.p_name = Field(col, "Full name", default=u["full_name"])
        self.p_name.pack(fill="x", pady=PAD_S)
        self.p_phone = Field(col, "Phone", default=u["phone"] or "")
        self.p_phone.pack(fill="x", pady=PAD_S)
        cities = user_model.get_cities()
        self._pcity_map = {c["name"]: c["city_id"] for c in cities}
        cur_city = next((c["name"] for c in cities if c["city_id"] == u["city_id"]),
                        cities[0]["name"])
        self.p_city = Field(col, "City", kind="combo",
                            values=list(self._pcity_map.keys()), default=cur_city)
        self.p_city.pack(fill="x", pady=PAD_S)
        tb.Button(col, text="Save Changes", bootstyle="primary",
                  command=self._save_profile).pack(anchor="w", pady=(PAD_M, PAD_S))

        # ---- Change password ----
        pwcard = Card(inner); pwcard.pack(fill="x", pady=(PAD_M, 0))
        section_title(pwcard, "Change Password")
        pwcol = field_column(pwcard)
        self.p_pwd = Field(pwcol, "New password", kind="password")
        self.p_pwd.pack(fill="x", pady=PAD_S)
        tb.Button(pwcol, text="Update Password", bootstyle="warning",
                  command=self._change_pwd).pack(anchor="w", pady=(PAD_M, PAD_S))

        # ---- Addresses ----
        acard = Card(inner); acard.pack(fill="x", pady=(PAD_M, 0))
        head = tb.Frame(acard); head.pack(fill="x")
        section_title(head, "Saved Addresses")
        tb.Button(head, text="+ Add Address", bootstyle="success-outline",
                  command=self._add_address_modal).pack(side="right")
        for a in user_model.get_addresses(self.user["user_id"]):
            r = tb.Frame(acard); r.pack(fill="x", pady=4)
            tb.Label(r, text=f"📍 {a['label']}: {a['line1']}", font=FONTS["body"]).pack(side="left")
            tb.Button(r, text="Delete", bootstyle="danger-outline",
                      command=lambda a=a: self._del_address(a)).pack(side="right")

    def _save_profile(self):
        ok, msg = validators.validate_all(
            validators.validate_required(self.p_name.get(), "Full name"),
            validators.validate_phone(self.p_phone.get()))
        if not ok:
            self.notify(msg, "warning"); return
        user_model.update_profile(self.user["user_id"], self.p_name.get(),
                                  self.p_phone.get(),
                                  self._pcity_map[self.p_city.get()])
        self.user["full_name"] = self.p_name.get()
        self.notify("Profile updated.", "success")

    def _change_pwd(self):
        ok, msg = validators.validate_password(self.p_pwd.get())
        if not ok:
            self.notify(msg, "warning"); return
        user_model.change_password(self.user["user_id"], self.p_pwd.get())
        self.notify("Password updated.", "success")
        self.p_pwd.set("")

    def _add_address_modal(self):
        dlg = Modal(self.app.root, "Add Address", width=460, height=360)
        label = Field(dlg.body, "Label (e.g. Home, Office)"); label.pack(fill="x", pady=PAD_S)
        line1 = Field(dlg.body, "Address line"); line1.pack(fill="x", pady=PAD_S)
        cities = user_model.get_cities()
        cmap = {c["name"]: c["city_id"] for c in cities}
        cityf = Field(dlg.body, "City", kind="combo", values=list(cmap.keys()),
                      default=cities[0]["name"], width=24)
        cityf.pack(anchor="w", pady=PAD_S)

        def save():
            ok, msg = validators.validate_all(
                validators.validate_required(label.get(), "Label"),
                validators.validate_required(line1.get(), "Address line"))
            if not ok:
                self.notify(msg, "warning"); return
            user_model.add_address(self.user["user_id"], label.get(), line1.get(),
                                   cmap[cityf.get()])
            self.notify("Address added.", "success")
            dlg.destroy(); self.refresh()
        tb.Button(dlg.body, text="Save Address", bootstyle="success",
                  command=save).pack(anchor="e", pady=PAD_M)

    def _del_address(self, a):
        user_model.delete_address(a["address_id"])
        self.notify("Address removed.", "info")
        self.refresh()

    # =====================================================================
    # SHARED: product detail modal + cart/wishlist actions
    # =====================================================================
    def _open_product(self, product_id):
        p = product_model.get_product(product_id)
        if not p:
            self.notify("Product not found.", "danger"); return
        dlg = Modal(self.app.root, p["name"], width=560, height=620)
        body = dlg.body

        tk.Frame(body, bg=CARD_ACCENTS[product_id % len(CARD_ACCENTS)],
                 height=6).pack(fill="x")
        tb.Label(body, text=p["name"], font=FONTS["h2"]).pack(anchor="w", pady=(PAD_S, 2))
        tb.Label(body, text=f"{p['category']}  ·  {p['shop_name']}"
                 + ("  ✔ Verified" if p["is_verified"] else ""),
                 font=FONTS["small"], foreground=COLORS["muted"]).pack(anchor="w")

        price_row = tb.Frame(body); price_row.pack(anchor="w", pady=PAD_S)
        if p["is_flash"] and p["flash_price"]:
            tb.Label(price_row, text=f"Rs {p['flash_price']:,.0f}", font=FONTS["h2"],
                     foreground=COLORS["danger"]).pack(side="left")
            tb.Label(price_row, text=f"Rs {p['price']:,.0f}", font=FONTS["body"],
                     foreground=COLORS["muted"]).pack(side="left", padx=PAD_S)
        else:
            tb.Label(price_row, text=f"Rs {p['price']:,.0f}", font=FONTS["h2"],
                     foreground=COLORS["primary"]).pack(side="left")

        tb.Label(body, text=f"{stars(p['rating'])}  ({p['review_count']} reviews)",
                 font=FONTS["body"], foreground=COLORS["warning"]).pack(anchor="w")
        stock_txt = "Out of stock" if p["stock"] <= 0 else f"{p['stock']} in stock"
        tb.Label(body, text=stock_txt, font=FONTS["small"],
                 foreground=COLORS["success"] if p["stock"] > 0 else COLORS["danger"]).pack(
                     anchor="w", pady=(0, PAD_S))
        tb.Label(body, text=p["description"] or "No description provided.",
                 font=FONTS["body"], wraplength=500, justify="left").pack(anchor="w",
                 pady=PAD_S)

        btns = tb.Frame(body); btns.pack(fill="x", pady=PAD_S)
        tb.Button(btns, text="🛒 Add to Cart", bootstyle="primary",
                  command=lambda: (self._add_to_cart(product_id), dlg.destroy())).pack(side="left")
        in_wl = product_model.in_wishlist(self.user["user_id"], product_id)
        tb.Button(btns, text="❤️ Wishlist" if not in_wl else "💔 Unwishlist",
                  bootstyle="danger-outline",
                  command=lambda: (self._toggle_wishlist(product_id), dlg.destroy())).pack(
                      side="left", padx=PAD_S)
        tb.Button(btns, text="⚖️ Compare", bootstyle="info-outline",
                  command=lambda: self._add_compare(product_id)).pack(side="left")

        # Reviews list.
        section_title(body, "Customer Reviews")
        revs = product_model.get_reviews(product_id)
        if not revs:
            tb.Label(body, text="No reviews yet.", font=FONTS["small"],
                     foreground=COLORS["muted"]).pack(anchor="w")
        for r in revs[:6]:
            rr = tb.Frame(body); rr.pack(fill="x", pady=2)
            tb.Label(rr, text=f"{stars(r['rating'])}  {r['full_name']}",
                     font=FONTS["small"], foreground=COLORS["warning"]).pack(anchor="w")
            if r["comment"]:
                tb.Label(rr, text=r["comment"], font=FONTS["small"],
                         wraplength=480, justify="left",
                         foreground=COLORS["text"]).pack(anchor="w")

    def _add_to_cart(self, product_id):
        ok, msg = order_model.add_to_cart(self.user["user_id"], product_id, 1)
        self.notify(msg, "success" if ok else "warning")
        self.app.update_badge()

    def _toggle_wishlist(self, product_id):
        added = product_model.toggle_wishlist(self.user["user_id"], product_id)
        self.notify("Added to wishlist." if added else "Removed from wishlist.",
                    "success" if added else "info")

    def _add_compare(self, product_id):
        if product_id in self._compare_ids:
            self.notify("Already in comparison.", "info"); return
        if len(self._compare_ids) >= 3:
            self.notify("You can compare up to 3 products.", "warning"); return
        self._compare_ids.append(product_id)
        self.notify("Added to comparison. Open the Compare page.", "success")

    # --------------------------------------------------------------- helpers
    def _status_badge(self, parent, status):
        """A tinted status pill (shared component) for an order status."""
        return pill(parent, status.replace("_", " ").title(), status=status)

    def _empty(self, parent, message):
        box = tb.Frame(parent); box.pack(fill="both", expand=True, pady=PAD_L)
        tb.Label(box, text="📭", font=("Segoe UI", 40)).pack()
        tb.Label(box, text=message, font=FONTS["body"],
                 foreground=COLORS["muted"]).pack(pady=PAD_S)
