"""
views/base_dashboard.py
================================================================================
Shared dashboard shell used by all four role dashboards (buyer, seller, delivery,
admin). It wires together the navy Sidebar, the top HeaderBar and a swappable
content area so each concrete dashboard only has to declare its nav items and
build its individual pages. Keeping this in one place is what guarantees the
identical layout, spacing and navigation behaviour on every screen and removes
all code duplication between the four dashboards.
================================================================================
"""

import tkinter as tk
import ttkbootstrap as tb

from views.components import Sidebar, HeaderBar, toast, ScrollFrame, Modal, pill
from utils.theme import COLORS, FONTS, PAD_S, PAD_L, PAD_M
from models import user_model


class BaseDashboard(tb.Frame):
    """
    Base class for every role dashboard.

    A subclass must define:
        NAV       -> list of (key, icon, label) tuples for the sidebar
        ROLE_LABEL-> short text shown in the header role badge
        ACCENT    -> accent colour for avatar + badge
    and implement build_page(key, parent) which fills `parent` with that page.
    """

    NAV = []
    ROLE_LABEL = "USER"
    ACCENT = COLORS["primary"]

    def __init__(self, master, app, user):
        super().__init__(master)
        self.app = app          # reference to the root application (for logout/route)
        self.user = user        # logged-in user dict
        self.pack(fill="both", expand=True)

        # ----- Sidebar (fixed navy navigation on the left) -----
        self.sidebar = Sidebar(
            self, brand=self.ROLE_LABEL.title(),
            items=self.NAV, on_select=self._on_nav, on_logout=self._logout)
        self.sidebar.pack(side="left", fill="y")

        # ----- Right side: header on top, content below -----
        right = tk.Frame(self, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True)

        self.header = HeaderBar(right, user, self.ROLE_LABEL, self.ACCENT,
                                on_bell=self._open_notifications)
        self.header.pack(fill="x")
        tk.Frame(right, bg=COLORS["border"], height=1).pack(fill="x")
        self._update_bell()

        # Container that holds the currently active page.
        self.content = tk.Frame(right, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True)

        # Select the first real nav item by default (skip section headers).
        first = next((k for k, ic, lbl in self.NAV if k), None)
        if first:
            self.sidebar.select(first)

    # ------------------------------------------------------------------ nav
    def _on_nav(self, key):
        """Clear the content area and build the requested page."""
        for w in self.content.winfo_children():
            w.destroy()
        # Update the header title to the human label of this nav item.
        label = next((lbl for k, ic, lbl in self.NAV if k == key), "Dashboard")
        self.header.set_title(label)
        try:
            self.build_page(key, self.content)
        except Exception as exc:                       # never show a raw traceback
            self._error_page(self.content, exc)

    def build_page(self, key, parent):
        """Override in subclass to populate `parent` for the given nav key."""
        raise NotImplementedError

    # ------------------------------------------------------- helper builders
    def scroll_page(self, parent):
        """
        Standard padded, scrollable page body. Returns the inner frame that
        pages should add their widgets to (already padded on all sides).
        """
        sf = ScrollFrame(parent)
        sf.pack(fill="both", expand=True)
        inner = tk.Frame(sf.body, bg=COLORS["bg"])
        inner.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_L)
        return inner

    def refresh(self):
        """Rebuild the current page (used after data changes)."""
        self._update_bell()
        if self.sidebar.active:
            self._on_nav(self.sidebar.active)

    def notify(self, message, kind="success"):
        """Show a toast bound to the root window."""
        toast(self.app.root, message, kind)

    # ----------------------------------------------------- notification centre
    def _update_bell(self):
        """Refresh the header bell's unread-count badge."""
        try:
            self.header.set_badge(user_model.unread_count(self.user["user_id"]))
        except Exception:
            pass

    def _open_notifications(self):
        """Open the notification centre modal for the current user."""
        try:
            notes = user_model.get_notifications(self.user["user_id"])
        except Exception:
            notes = []
        dlg = Modal(self.app.root, "Notifications", width=560, height=560,
                    accent=self.ACCENT)
        head = tk.Frame(dlg.body, bg=COLORS["card"])
        head.pack(fill="x", pady=(0, PAD_S))
        unread = sum(1 for n in notes if not n["is_read"])
        tk.Label(head, text=f"{len(notes)} total · {unread} unread",
                 font=FONTS["small"], fg=COLORS["muted"], bg=COLORS["card"]).pack(side="left")

        def mark_all():
            user_model.mark_notifications_read(self.user["user_id"])
            self._update_bell()
            dlg.destroy()
            self.notify("All notifications marked as read.", "info")

        tb.Button(head, text="Mark all read", bootstyle="outline-primary",
                  command=mark_all).pack(side="right")

        sf = ScrollFrame(dlg.body)
        sf.pack(fill="both", expand=True)
        body = tk.Frame(sf.body, bg=COLORS["card"])
        body.pack(fill="both", expand=True)
        if not notes:
            tk.Label(body, text="You're all caught up — no notifications yet.",
                     font=FONTS["body"], fg=COLORS["muted"], bg=COLORS["card"]).pack(
                         anchor="w", pady=PAD_M)
        for n in notes[:60]:
            row = tk.Frame(body, bg=COLORS["card"])
            row.pack(fill="x", pady=2)
            dot = COLORS["primary"] if not n["is_read"] else COLORS["border_d"]
            tk.Frame(row, bg=dot, width=8, height=8).pack(side="left", padx=(2, PAD_S), pady=6)
            txt = tk.Frame(row, bg=COLORS["card"])
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=n["message"], font=FONTS["body"], bg=COLORS["card"],
                     fg=COLORS["text"], wraplength=440, justify="left").pack(anchor="w")
            tk.Label(txt, text=str(n["created_at"])[:16], font=FONTS["tiny"],
                     bg=COLORS["card"], fg=COLORS["faint"]).pack(anchor="w")
            tk.Frame(body, bg=COLORS["border"], height=1).pack(fill="x", pady=(2, 0))

    # ------------------------------------------------------------- internals
    def _error_page(self, parent, exc):
        """Friendly fallback if a page fails to build (no raw traceback)."""
        box = tk.Frame(parent, bg=COLORS["bg"])
        box.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_L)
        tk.Label(box, text="⚠️  Something went wrong loading this page.",
                 font=("Segoe UI", 13, "bold"), fg=COLORS["danger"],
                 bg=COLORS["bg"]).pack(anchor="w")
        tk.Label(box, text=str(exc), font=("Segoe UI", 10),
                 fg=COLORS["muted"], bg=COLORS["bg"], wraplength=600,
                 justify="left").pack(anchor="w", pady=(PAD_M, 0))

    def _logout(self):
        """Return to the login screen."""
        self.app.logout()
