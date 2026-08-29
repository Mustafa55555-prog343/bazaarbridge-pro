"""
views/components.py
================================================================================
Reusable UI building blocks shared by every dashboard so the whole application
speaks one visual language: gradient KPI cards, the navy sidebar with grouped
navigation, the top header bar with a live notification bell, scrollable card
grids, zebra-striped tables, status pills, toasts and modal dialogs.

Centralising these widgets is what removes alignment and spacing inconsistencies
— every screen is assembled from the exact same components and spacing tokens,
so nothing is ever one-off or slightly misaligned.
================================================================================
"""

import utils.tkfix  # noqa: F401  (installs tk colour shim on import)
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from utils.theme import (
    COLORS, FONTS, PAD_XS, PAD_S, PAD_M, PAD_L, PAD_XL, CARD_ACCENTS,
    GRADIENTS, GRADIENT_ORDER, status_style, accent_for,
)

FONT_FAMILY = "Segoe UI"


# ----------------------------------------------------------------------------
# Small drawing helpers
# ----------------------------------------------------------------------------
def _lerp(c1, c2, t):
    """Linearly interpolate between two #rrggbb colours (t in 0..1)."""
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 + (r2 - r1) * t); g = int(g1 + (g2 - g1) * t); b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def paint_gradient(canvas, w, h, start, end, vertical=True):
    """Paint a smooth two-stop gradient onto a tk.Canvas."""
    canvas.delete("grad")
    steps = max(1, (h if vertical else w))
    for i in range(steps):
        color = _lerp(start, end, i / steps)
        if vertical:
            canvas.create_line(0, i, w, i, fill=color, tags="grad")
        else:
            canvas.create_line(i, 0, i, h, fill=color, tags="grad")
    canvas.tag_lower("grad")


def gradient_banner(master, height=120, gradient="indigo"):
    """A full-width gradient banner canvas. Returns the canvas (draw text on it)."""
    start, end = GRADIENTS.get(gradient, GRADIENTS["indigo"])
    cv = tk.Canvas(master, height=height, highlightthickness=0, bd=0, bg=end)
    cv.pack(fill="x")

    def _redraw(_e=None):
        w = cv.winfo_width() or master.winfo_width() or 900
        paint_gradient(cv, w, height, start, end, vertical=False)
    cv.bind("<Configure>", _redraw)
    return cv


# ============================================================================
# CARD  — a white panel with a hairline border, the base for most content.
# ============================================================================
class Card(tb.Frame):
    """A padded white card container with a subtle border."""

    def __init__(self, master, padding=PAD_M, **kw):
        super().__init__(master, padding=padding, bootstyle="light", **kw)
        self.configure(relief="flat")


# ============================================================================
# STAT CARD  — premium gradient KPI tile: icon chip, big value, caption, trend.
# ============================================================================
class StatCard(tk.Frame):
    """A dashboard KPI card with a gradient face, icon chip and big value.

    Backwards compatible: StatCard(master, title, value, icon, accent). An
    optional ``subtitle`` and ``gradient`` (theme gradient key) can be supplied
    for a richer look.
    """

    def __init__(self, master, title, value, icon="📊", accent=None,
                 subtitle=None, gradient=None, **kw):
        super().__init__(master, bg=COLORS["card"], highlightthickness=0, **kw)
        accent = accent or COLORS["primary"]
        if gradient and gradient in GRADIENTS:
            g_start, g_end = GRADIENTS[gradient]
        else:
            g_start, g_end = _accent_gradient(accent)

        self._cw, self._ch = 240, 104
        self.cv = tk.Canvas(self, width=self._cw, height=self._ch,
                            highlightthickness=0, bd=0, bg=g_end)
        self.cv.pack(fill="both", expand=True)
        self._title, self._icon = title.upper(), icon
        self._subtitle = subtitle
        self._value = str(value)
        self._g = (g_start, g_end)
        self.cv.bind("<Configure>", self._draw)

    def _draw(self, _e=None):
        cv = self.cv
        w = cv.winfo_width() or self._cw
        h = cv.winfo_height() or self._ch
        g_start, g_end = self._g
        paint_gradient(cv, w, h, g_start, g_end, vertical=False)
        cv.delete("fg")
        chip = _lerp(g_start, "#ffffff", 0.22)
        cv.create_oval(w - 52, 16, w - 16, 52, fill=chip, outline="", tags="fg")
        cv.create_text(w - 34, 34, text=self._icon, font=(FONT_FAMILY, 15), tags="fg")
        cv.create_text(18, 22, text=self._title, anchor="w",
                       fill="#eef2ff", font=(FONT_FAMILY, 9, "bold"), tags="fg")
        # Auto-shrink the value font so long numbers never clip the icon chip.
        avail = max(60, (w - 70) - 18)            # space left of the icon chip
        size = 26
        item = cv.create_text(18, 54, text=self._value, anchor="w", fill="white",
                              font=(FONT_FAMILY, size, "bold"), tags="fg")
        while size > 13:
            bbox = cv.bbox(item)
            if bbox and (bbox[2] - bbox[0]) <= avail:
                break
            size -= 1
            cv.itemconfigure(item, font=(FONT_FAMILY, size, "bold"))
        if self._subtitle:
            cv.create_text(18, 84, text=self._subtitle, anchor="w",
                           fill="#dbeafe", font=(FONT_FAMILY, 8), tags="fg")

    def set_value(self, value):
        """Update the displayed value (used on data refresh)."""
        self._value = str(value)
        self._draw()


def _accent_gradient(accent):
    """Map a solid accent colour to a pleasing two-stop gradient."""
    table = {
        COLORS["primary"]: GRADIENTS["indigo"],
        COLORS["success"]: GRADIENTS["emerald"],
        COLORS["info"]:    GRADIENTS["sky"],
        COLORS["warning"]: GRADIENTS["amber"],
        COLORS["danger"]:  GRADIENTS["rose"],
    }
    if accent in table:
        return table[accent]
    return (_lerp(accent, "#ffffff", 0.18), _lerp(accent, "#000000", 0.20))


def stat_row(master, stats):
    """Build a horizontal row of evenly-sized StatCards.

    ``stats`` is a list of dicts: {title, value, icon, accent, subtitle}.
    Returns the container frame.
    """
    row = tb.Frame(master)
    row.pack(fill="x", pady=(0, PAD_M))
    for i, s in enumerate(stats):
        grad = GRADIENT_ORDER[i % len(GRADIENT_ORDER)]
        card = StatCard(row, s["title"], s["value"], s.get("icon", "📊"),
                        s.get("accent", CARD_ACCENTS[i % len(CARD_ACCENTS)]),
                        subtitle=s.get("subtitle"), gradient=s.get("gradient", grad))
        card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else PAD_S, 0))
        row.columnconfigure(i, weight=1, uniform="stat")
    return row


# ============================================================================
# SCROLLABLE FRAME  — vertical scrolling content area (for long lists/grids).
# ============================================================================
class ScrollFrame(tb.Frame):
    """A vertically scrollable frame; add children to `.body`."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=COLORS["bg"], bd=0)
        self.scroll = tb.Scrollbar(self, orient="vertical",
                                   command=self.canvas.yview, bootstyle="round")
        self.body = tb.Frame(self.canvas)

        self.body.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=self.scroll.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")


# ============================================================================
# SIDEBAR  — fixed deep-navy navigation with grouped icon + label items.
# ============================================================================
class Sidebar(tk.Frame):
    """Vertical navigation sidebar.

    ``items`` is a list of (key, icon, label). A tuple with a falsy key is
    rendered as a non-clickable section header so long navigations read as tidy
    groups instead of one long list.
    """

    def __init__(self, master, brand, items, on_select, on_logout):
        super().__init__(master, bg=COLORS["sidebar"], width=280)
        self.pack_propagate(False)
        self.on_select = on_select
        self.buttons = {}
        self._bars = {}

        brand_box = tk.Frame(self, bg=COLORS["sidebar"])
        brand_box.pack(fill="x", pady=(PAD_L, PAD_M), padx=PAD_M)
        tk.Label(brand_box, text="🛍️  BazaarBridge", font=(FONT_FAMILY, 13, "bold"),
                 fg=COLORS["sidebar_tb"], bg=COLORS["sidebar"], anchor="w",
                 wraplength=236, justify="left").pack(anchor="w", fill="x")
        tk.Label(brand_box, text=brand, font=(FONT_FAMILY, 9),
                 fg=COLORS["sidebar_t"], bg=COLORS["sidebar"], anchor="w").pack(
                     anchor="w", pady=(1, 0))

        tk.Frame(self, bg=COLORS["sidebar_h"], height=1).pack(
            fill="x", padx=PAD_L, pady=(0, PAD_S))

        nav_wrap = tk.Frame(self, bg=COLORS["sidebar"])
        nav_wrap.pack(fill="both", expand=True)

        for key, icon, label in items:
            if not key:
                tk.Label(nav_wrap, text=label.upper(), anchor="w",
                         font=(FONT_FAMILY, 8, "bold"), fg=COLORS["sidebar_t"],
                         bg=COLORS["sidebar"], padx=PAD_L).pack(
                             fill="x", pady=(PAD_M, 2))
                continue
            item = tk.Frame(nav_wrap, bg=COLORS["sidebar"])
            item.pack(fill="x", padx=PAD_S, pady=1)
            bar = tk.Frame(item, bg=COLORS["sidebar"], width=3)
            bar.pack(side="left", fill="y")
            btn = tk.Label(item, text=f"  {icon}  {label}", anchor="w",
                           font=FONTS["sidebar"], fg=COLORS["sidebar_t"],
                           bg=COLORS["sidebar"], padx=PAD_S, pady=9, cursor="hand2")
            btn.pack(side="left", fill="x", expand=True)
            for w in (btn, item):
                w.bind("<Button-1>", lambda e, k=key: self.select(k))
                w.bind("<Enter>", lambda e, k=key: self._hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self._hover(k, False))
            self.buttons[key] = btn
            self._bars[key] = bar

        logout = tk.Label(self, text="  🚪   Logout", anchor="w",
                          font=FONTS["sidebar"], fg="#fda4af",
                          bg=COLORS["sidebar"], padx=PAD_L, pady=11, cursor="hand2")
        logout.pack(side="bottom", fill="x", pady=(PAD_S, PAD_M))
        logout.bind("<Button-1>", lambda e: on_logout())
        logout.bind("<Enter>", lambda e: logout.configure(bg="#3a1f2a"))
        logout.bind("<Leave>", lambda e: logout.configure(bg=COLORS["sidebar"]))

        self.active = None

    def _hover(self, key, entering):
        if key == self.active:
            return
        self.buttons[key].configure(bg=COLORS["sidebar_h"] if entering else COLORS["sidebar"])

    def select(self, key):
        """Visually mark a nav item active and notify the dashboard."""
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(bg=COLORS["sidebar_a"], fg="white", font=FONTS["sidebar_b"])
                self._bars[k].configure(bg="#a5b4fc")
            else:
                btn.configure(bg=COLORS["sidebar"], fg=COLORS["sidebar_t"], font=FONTS["sidebar"])
                self._bars[k].configure(bg=COLORS["sidebar"])
        self.active = key
        self.on_select(key)


# ============================================================================
# HEADER BAR  — page title (left), notification bell + user identity (right).
# ============================================================================
class HeaderBar(tk.Frame):
    """Top header showing the page title, a notification bell and the user."""

    def __init__(self, master, user, role_label, accent, on_bell=None):
        super().__init__(master, bg=COLORS["card"], height=70)
        self.pack_propagate(False)
        self.user = user
        self._accent = accent
        self._on_bell = on_bell

        tk.Frame(self, bg=COLORS["border"], height=1).pack(side="bottom", fill="x")

        title_box = tk.Frame(self, bg=COLORS["card"])
        title_box.pack(side="left", padx=PAD_L)
        self.title_lbl = tk.Label(title_box, text="Dashboard", font=FONTS["h2"],
                                  fg=COLORS["text"], bg=COLORS["card"])
        self.title_lbl.pack(anchor="w", pady=(PAD_M, 0))
        self.sub_lbl = tk.Label(title_box, text="", font=FONTS["small"],
                                fg=COLORS["muted"], bg=COLORS["card"])
        self.sub_lbl.pack(anchor="w")

        right = tk.Frame(self, bg=COLORS["card"])
        right.pack(side="right", padx=PAD_L)

        initials = "".join([w[0] for w in user["full_name"].split()[:2]]).upper()
        avatar = tk.Canvas(right, width=42, height=42, bg=COLORS["card"],
                           highlightthickness=0)
        avatar.create_oval(2, 2, 40, 40, fill=accent, outline="")
        avatar.create_text(21, 21, text=initials, fill="white",
                           font=(FONT_FAMILY, 12, "bold"))
        avatar.pack(side="right", padx=(PAD_M, 0))

        info = tk.Frame(right, bg=COLORS["card"])
        info.pack(side="right")
        tk.Label(info, text=user["full_name"], font=FONTS["h3"],
                 fg=COLORS["text"], bg=COLORS["card"]).pack(anchor="e")
        badge = tk.Label(info, text=role_label, font=(FONT_FAMILY, 8, "bold"),
                         fg="white", bg=accent, padx=8, pady=1)
        badge.pack(anchor="e", pady=(2, 0))

        self.bell = tk.Canvas(right, width=40, height=40, bg=COLORS["card"],
                             highlightthickness=0, cursor="hand2")
        self.bell.pack(side="right", padx=(0, PAD_M))
        self.bell.bind("<Button-1>", lambda e: self._on_bell() if self._on_bell else None)
        self._badge_count = 0
        self._draw_bell()

    def _draw_bell(self):
        cv = self.bell
        cv.delete("all")
        cv.create_text(20, 21, text="🔔", font=(FONT_FAMILY, 16))
        if self._badge_count > 0:
            cv.create_oval(22, 4, 38, 20, fill=COLORS["danger"], outline="white")
            txt = "9+" if self._badge_count > 9 else str(self._badge_count)
            cv.create_text(30, 12, text=txt, fill="white", font=(FONT_FAMILY, 7, "bold"))

    def set_badge(self, count):
        """Update the unread notification count shown on the bell."""
        self._badge_count = count or 0
        self._draw_bell()

    def set_title(self, text, subtitle=""):
        """Update the page title (and optional subtitle) shown in the header."""
        self.title_lbl.configure(text=text)
        self.sub_lbl.configure(text=subtitle)


# ============================================================================
# SECTION TITLE
# ============================================================================
def section_title(master, text, subtitle=None):
    """A consistent section heading (+ optional subtitle) for content areas."""
    box = tb.Frame(master)
    box.pack(fill="x", pady=(0, PAD_M))
    tb.Label(box, text=text, font=FONTS["h2"], foreground=COLORS["text"]).pack(anchor="w")
    if subtitle:
        tb.Label(box, text=subtitle, font=FONTS["small"],
                 foreground=COLORS["muted"]).pack(anchor="w", pady=(2, 0))
    return box


# ============================================================================
# STATUS PILL  — a small coloured badge for an order/dispute status.
# ============================================================================
def pill(master, text, status=None, bg=None, fg=None):
    """Return a status pill label. Colours derive from the theme."""
    if status is not None:
        bg, fg = status_style(status)
    bg = bg or COLORS["primary_l"]
    fg = fg or COLORS["primary"]
    return tk.Label(master, text=f" {text} ", font=(FONT_FAMILY, 8, "bold"),
                    bg=bg, fg=fg, padx=8, pady=2)


_TABLE_STYLE_DONE = False


def _ensure_table_style():
    """Configure Treeview row height / fonts once for the whole app.

    ttkbootstrap renders each Treeview with a *bootstyle-specific* style name
    (e.g. ``primary.Treeview``) whose own row height (17px) overrides the base
    ``Treeview`` style — which is why rows look cramped if only the base style is
    set. We therefore configure the base style *and* every colour variant used
    across the app so rows are comfortably tall everywhere.
    """
    global _TABLE_STYLE_DONE
    if _TABLE_STYLE_DONE:
        return
    try:
        style = tb.Style.get_instance()
        row_h = 40
        body_font = (FONT_FAMILY, 10)
        head_font = (FONT_FAMILY, 10, "bold")
        for name in ("Treeview", "primary.Treeview", "info.Treeview",
                     "success.Treeview", "secondary.Treeview", "dark.Treeview",
                     "warning.Treeview", "danger.Treeview"):
            style.configure(name, rowheight=row_h, font=body_font,
                            background=COLORS["card"], fieldbackground=COLORS["card"],
                            borderwidth=0)
        for name in ("Treeview.Heading", "primary.Treeview.Heading",
                     "info.Treeview.Heading", "success.Treeview.Heading",
                     "secondary.Treeview.Heading", "dark.Treeview.Heading"):
            style.configure(name, font=head_font, padding=(10, 12))
        _TABLE_STYLE_DONE = True
    except Exception:
        pass


# ============================================================================
# DATA TABLE  — a styled, zebra-striped, sortable Treeview with a scrollbar.
# ============================================================================
# Column names whose values are numeric / money / counts and therefore read
# best right-aligned. Matched case-insensitively as whole names so that, e.g.,
# the left-aligned "Order" id column is never confused with "Min Order".
_NUMERIC_COLUMNS = {
    "price", "unit price", "total", "line total", "subtotal", "min order",
    "revenue", "amount", "spent", "share", "earning", "earnings", "balance",
    "stock", "new stock", "current", "units", "units sold", "qty", "quantity",
    "points", "reward points", "loyalty points", "discount", "discount %",
    "deliveries", "active", "rows", "count", "orders", "rating",
}


def _is_numeric_col(name):
    """Return True if a column should be right-aligned (numbers / money / %)."""
    n = str(name).strip().lower()
    if n in _NUMERIC_COLUMNS:
        return True
    # Fall back to keyword detection for any variant not listed explicitly,
    # while never matching the plain id-style "order" / "id" columns.
    if n in ("order", "id", "order id"):
        return False
    keywords = ("price", "total", "revenue", "amount", "spent", "earning",
                "balance", "points", "discount", "share")
    return any(k in n for k in keywords)


class DataTable(tb.Frame):
    """A reusable sortable table built on ttk.Treeview with zebra striping."""

    def __init__(self, master, columns, widths=None, height=12, bootstyle="primary"):
        super().__init__(master)
        _ensure_table_style()
        self._max_height = height
        widths = widths or {}
        self.tree = tb.Treeview(self, columns=columns, show="headings",
                                height=height, bootstyle=bootstyle)
        for col in columns:
            anchor = "e" if _is_numeric_col(col) else "w"
            # Match the heading anchor to the cell anchor so every header sits
            # directly above its column instead of floating in the centre.
            self.tree.heading(col, text=str(col), anchor=anchor,
                              command=lambda c=col: self._sort(c, False))
            self.tree.column(col, width=widths.get(col, 120), anchor=anchor,
                             minwidth=widths.get(col, 80), stretch=True)
        vsb = tb.Scrollbar(self, orient="vertical", command=self.tree.yview,
                           bootstyle="round")
        self.tree.configure(yscrollcommand=vsb.set)
        # Belt-and-suspenders: force a comfortable row height on this widget's
        # actual (possibly bootstyle-specific) style name.
        try:
            style = tb.Style.get_instance()
            sname = self.tree.cget("style") or "Treeview"
            style.configure(sname, rowheight=40, font=(FONT_FAMILY, 10))
        except Exception:
            pass
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("odd", background=COLORS["card"])
        self.tree.tag_configure("even", background=COLORS["card_alt"])

    def load(self, rows):
        """Replace all table rows with `rows` (list of tuples)."""
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            self.tree.insert("", "end", values=r,
                             tags=("even" if i % 2 else "odd",))
        # Size the table to its content (so short tables don't show empty rows)
        # while never exceeding the configured maximum, keeping the scrollbar
        # for longer data sets.
        try:
            self.tree.configure(height=max(1, min(self._max_height, len(rows))))
        except Exception:
            pass

    def selected(self):
        """Return the values of the selected row, or None."""
        sel = self.tree.selection()
        return self.tree.item(sel[0])["values"] if sel else None

    def _sort(self, col, reverse):
        """Sort the table by a column when its header is clicked."""
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(str(t[0]).replace(",", "").replace("Rs", "").strip() or 0),
                      reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
            self.tree.item(k, tags=("even" if idx % 2 else "odd",))
        self.tree.heading(col, command=lambda: self._sort(col, not reverse))


# ============================================================================
# TOAST  — small auto-dismissing message near the bottom of the window.
# ============================================================================
def toast(window, message, kind="success"):
    """Show a temporary toast notification. kind: success|danger|info|warning."""
    colors = {"success": COLORS["success"], "danger": COLORS["danger"],
              "info": COLORS["info"], "warning": COLORS["warning"]}
    icons = {"success": "✓", "danger": "✕", "info": "ℹ", "warning": "⚠"}
    bg = colors.get(kind, COLORS["success"])
    t = tk.Toplevel(window)
    t.overrideredirect(True)
    t.configure(bg=bg)
    inner = tk.Frame(t, bg=bg)
    inner.pack(padx=2, pady=2)
    tk.Label(inner, text=icons.get(kind, "✓"), bg=bg, fg="white",
             font=(FONT_FAMILY, 12, "bold")).pack(side="left", padx=(16, 6), pady=12)
    tk.Label(inner, text=message, bg=bg, fg="white", font=(FONT_FAMILY, 10, "bold"),
             padx=4, pady=12).pack(side="left", padx=(0, 18))
    t.update_idletasks()
    window.update_idletasks()
    x = window.winfo_rootx() + (window.winfo_width() - t.winfo_width()) // 2
    y = window.winfo_rooty() + window.winfo_height() - t.winfo_height() - 40
    t.geometry(f"+{max(x,0)}+{max(y,0)}")
    t.attributes("-topmost", True)
    t.after(2400, t.destroy)


# ============================================================================
# FORM FIELD  — a labelled entry / combobox row used on every form.
# ============================================================================
class Field(tb.Frame):
    """A labelled input. kind: 'entry' | 'password' | 'combo' | 'text' | 'spin'."""

    def __init__(self, master, label, kind="entry", values=None, default=None,
                 width=32, **kw):
        super().__init__(master, **kw)
        tb.Label(self, text=label, font=FONTS["small_b"],
                 foreground=COLORS["text_soft"]).pack(anchor="w", pady=(0, 3))
        self.kind = kind
        self.var = tk.StringVar(value="" if default is None else str(default))

        if kind == "combo":
            self.widget = tb.Combobox(self, textvariable=self.var,
                                      values=values or [], state="readonly",
                                      width=width - 2, bootstyle="primary")
        elif kind == "password":
            self.widget = tb.Entry(self, textvariable=self.var, show="•",
                                   width=width, bootstyle="primary")
        elif kind == "text":
            self.widget = tk.Text(self, height=4, width=width, font=FONTS["body"],
                                  relief="solid", bd=1, highlightthickness=1,
                                  highlightcolor=COLORS["primary"],
                                  highlightbackground=COLORS["border"], wrap="word")
        elif kind == "spin":
            self.widget = tb.Spinbox(self, textvariable=self.var, from_=0,
                                     to=999999, width=width - 2, bootstyle="primary")
        else:
            self.widget = tb.Entry(self, textvariable=self.var, width=width,
                                   bootstyle="primary")
        self.widget.pack(anchor="w", fill="x")

    def get(self):
        if self.kind == "text":
            return self.widget.get("1.0", "end").strip()
        return self.var.get().strip()

    def set(self, value):
        if self.kind == "text":
            self.widget.delete("1.0", "end")
            self.widget.insert("1.0", value or "")
        else:
            self.var.set("" if value is None else str(value))


def field_column(parent, width=460):
    """
    Return a fixed-width left-aligned column for form fields.

    All fields packed into the returned frame with ``fill="x"`` render at the
    same width (``width`` px) and stay left-aligned, so entry boxes, combos and
    spinboxes line up perfectly instead of stretching to different widths.
    """
    holder = tb.Frame(parent)
    holder.pack(anchor="w", fill="x")
    holder.columnconfigure(0, minsize=width, weight=0)
    holder.columnconfigure(1, weight=1)           # spacer absorbs extra width
    col = tb.Frame(holder)
    col.grid(row=0, column=0, sticky="ew")
    return col


def humanize(text):
    """Turn a raw status/enum string into a friendly label.

    ``picked_up`` -> ``Picked Up``,  ``in_transit`` -> ``In Transit``,
    ``approved`` -> ``Approved``. Safe on empty / None input.
    """
    if not text:
        return ""
    return str(text).replace("_", " ").strip().title()


def stars(rating):
    """Return a star string for a 0-5 rating, e.g. 4.3 -> '★★★★☆'."""
    try:
        r = int(round(float(rating)))
    except (TypeError, ValueError):
        r = 0
    r = max(0, min(5, r))
    return "★" * r + "☆" * (5 - r)


# ============================================================================
# PRODUCT CARD  — a compact product tile used in browse / flash / wishlist grids.
# ============================================================================
class ProductCard(tb.Frame):
    """A product tile: badges, name, price (flash strike-through), rating, actions."""

    def __init__(self, master, product, on_open, action_label="View",
                 on_action=None, **kw):
        super().__init__(master, padding=0, bootstyle="light", **kw)
        p = product
        accent = accent_for(p["product_id"])

        strip = tk.Frame(self, bg=accent, height=6)
        strip.pack(fill="x")

        badge_row = tb.Frame(self, bootstyle="light")
        badge_row.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))
        if p.get("is_flash") and p.get("flash_price"):
            try:
                pct = round((1 - p["flash_price"] / p["price"]) * 100)
            except Exception:
                pct = 0
            tk.Label(badge_row, text=f"⚡ FLASH -{pct}%", bg=COLORS["danger"],
                     fg="white", font=(FONT_FAMILY, 8, "bold"), padx=6, pady=1).pack(side="left")
        if p.get("is_verified"):
            tk.Label(badge_row, text="✔ Verified", bg=COLORS["success_l"],
                     fg=COLORS["success"], font=(FONT_FAMILY, 8, "bold"),
                     padx=6, pady=1).pack(side="left", padx=(4, 0))

        body = tb.Frame(self, bootstyle="light")
        body.pack(fill="both", expand=True, padx=PAD_M, pady=(PAD_S, PAD_M))

        tb.Label(body, text=p["name"], font=FONTS["h3"], bootstyle="inverse-light",
                 foreground=COLORS["text"], wraplength=190,
                 justify="left").pack(anchor="w")
        tb.Label(body, text=p.get("category", ""), font=FONTS["small"],
                 foreground=COLORS["muted"], bootstyle="light").pack(anchor="w", pady=(1, 0))

        price_row = tb.Frame(body, bootstyle="light")
        price_row.pack(anchor="w", fill="x", pady=(PAD_S, 0))
        if p.get("is_flash") and p.get("flash_price"):
            tb.Label(price_row, text=f"Rs {p['flash_price']:,.0f}",
                     font=(FONT_FAMILY, 14, "bold"), foreground=COLORS["danger"],
                     bootstyle="light").pack(side="left")
            tb.Label(price_row, text=f"Rs {p['price']:,.0f}", font=FONTS["small"],
                     foreground=COLORS["muted"], bootstyle="light").pack(side="left", padx=(6, 0))
        else:
            tb.Label(price_row, text=f"Rs {p['price']:,.0f}",
                     font=(FONT_FAMILY, 14, "bold"), foreground=COLORS["primary"],
                     bootstyle="light").pack(side="left")

        meta = tb.Frame(body, bootstyle="light")
        meta.pack(anchor="w", fill="x", pady=(3, PAD_S))
        tb.Label(meta, text=stars(p.get("rating", 0)), font=(FONT_FAMILY, 10),
                 foreground=COLORS["warning"], bootstyle="light").pack(side="left")
        rc = p.get("review_count", 0)
        if rc:
            tb.Label(meta, text=f" ({rc})", font=FONTS["tiny"],
                     foreground=COLORS["muted"], bootstyle="light").pack(side="left")
        stock = p.get("stock", 0)
        stock_txt = "Out of stock" if stock <= 0 else f"{stock} in stock"
        tb.Label(meta, text=f"  ·  {stock_txt}", font=FONTS["small"],
                 foreground=COLORS["muted"] if stock > 0 else COLORS["danger"],
                 bootstyle="light").pack(side="left")

        btns = tb.Frame(body, bootstyle="light")
        btns.pack(anchor="w", fill="x", pady=(PAD_XS, 0))
        tb.Button(btns, text="Details", bootstyle="outline-primary",
                  command=lambda: on_open(p["product_id"])).pack(side="left")
        if on_action:
            tb.Button(btns, text=action_label, bootstyle="primary",
                      command=lambda: on_action(p["product_id"])).pack(
                          side="left", padx=(PAD_S, 0))


def card_grid(parent, items, builder, columns=4):
    """Lay out `items` into an evenly spaced grid, calling builder(cell, item)."""
    grid = tb.Frame(parent)
    grid.pack(fill="both", expand=True)
    for c in range(columns):
        grid.columnconfigure(c, weight=1, uniform="grid")
    for i, item in enumerate(items):
        cell = tb.Frame(grid)
        cell.grid(row=i // columns, column=i % columns, sticky="nsew",
                  padx=PAD_S, pady=PAD_S)
        builder(cell, item)
    return grid


# ============================================================================
# MODAL DIALOG  — a centred popup used for product detail, forms, confirms.
# ============================================================================
class Modal(tk.Toplevel):
    """A centred modal window with a gradient title bar and a body frame."""

    def __init__(self, parent, title, width=540, height=580, accent=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=COLORS["card"])
        self.transient(parent)
        self.resizable(False, False)
        accent = accent or COLORS["primary"]
        g1, g2 = _accent_gradient(accent)

        header = tk.Canvas(self, height=54, highlightthickness=0, bd=0, bg=g2)
        header.pack(fill="x")

        def _ph(_e=None):
            w = header.winfo_width() or width
            paint_gradient(header, w, 54, g1, g2, vertical=False)
            header.delete("ht")
            header.create_text(PAD_L, 27, text=title, anchor="w", fill="white",
                               font=(FONT_FAMILY, 13, "bold"), tags="ht")
            header.create_text(w - PAD_L, 27, text="✕", anchor="e", fill="white",
                               font=(FONT_FAMILY, 13, "bold"), tags="ht")
        header.bind("<Configure>", _ph)
        header.bind("<Button-1>",
                    lambda e: self.destroy() if e.x > (self.winfo_width() - 40) else None)

        self.body = tk.Frame(self, bg=COLORS["card"])
        self.body.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_L)

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(px, 0)}+{max(py, 0)}")
        self.grab_set()


def confirm(parent, message):
    """Simple yes/no confirmation modal. Returns True if confirmed."""
    result = {"ok": False}
    dlg = Modal(parent, "Please Confirm", width=420, height=210, accent=COLORS["danger"])
    tk.Label(dlg.body, text=message, font=FONTS["body"], bg=COLORS["card"],
             fg=COLORS["text"], wraplength=360, justify="left").pack(
                 anchor="w", pady=(0, PAD_L))
    row = tk.Frame(dlg.body, bg=COLORS["card"])
    row.pack(fill="x")

    def yes():
        result["ok"] = True
        dlg.destroy()

    tb.Button(row, text="Cancel", bootstyle="secondary",
              command=dlg.destroy).pack(side="right")
    tb.Button(row, text="Confirm", bootstyle="danger",
              command=yes).pack(side="right", padx=(0, PAD_S))
    dlg.wait_window()
    return result["ok"]
