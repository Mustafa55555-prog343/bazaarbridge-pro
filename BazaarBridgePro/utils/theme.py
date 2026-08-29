"""
utils/theme.py
================================================================================
Central design system for BazaarBridge Pro.

Every colour, font, spacing token and elevation rule lives here so the entire
application shares one coherent visual language: the same navy/indigo palette,
the same type scale, the same rhythm of whitespace on every screen. Views never
hard-code a colour or a pixel value — they pull from these tokens. That single
rule is what keeps the UI looking deliberate and consistent end to end.
================================================================================
"""

# ttkbootstrap base theme we layer our own styling on top of.
BASE_THEME = "flatly"

# ------------------------------------------------------------------ colour system
# A refined navy + indigo identity. Cool neutrals for surfaces, saturated accents
# reserved for data and calls-to-action so the eye always knows where to look.
COLORS = {
    # brand / actions
    "primary":    "#4f46e5",   # indigo 600 — primary brand + CTA
    "primary_d":  "#4338ca",   # indigo 700 — hover / pressed
    "primary_l":  "#eef2ff",   # indigo 50  — tints, selected rows
    "secondary":  "#64748b",   # slate 500

    # semantic
    "success":    "#10b981",   # emerald 500
    "success_l":  "#ecfdf5",
    "info":       "#0ea5e9",   # sky 500
    "info_l":     "#f0f9ff",
    "warning":    "#f59e0b",   # amber 500
    "warning_l":  "#fffbeb",
    "danger":     "#ef4444",   # red 500
    "danger_l":   "#fef2f2",

    # structure
    "dark":       "#0f172a",   # slate 900
    "sidebar":    "#0f172a",   # deep navy sidebar
    "sidebar_d":  "#0b1120",   # sidebar footer / gradient bottom
    "sidebar_a":  "#4f46e5",   # active sidebar item fill
    "sidebar_h":  "#1e293b",   # sidebar hover
    "sidebar_t":  "#94a3b8",   # sidebar inactive text
    "sidebar_tb": "#e2e8f0",   # sidebar bright text (brand/active)

    # surfaces
    "bg":         "#f1f5f9",   # app background (slate 100)
    "bg_alt":     "#e9eef5",   # alternate band
    "card":       "#ffffff",
    "card_alt":   "#f8fafc",   # zebra rows, subtle panels
    "text":       "#1e293b",   # slate 800 — primary text
    "text_soft":  "#334155",
    "muted":      "#64748b",   # slate 500 — secondary text
    "faint":      "#94a3b8",   # slate 400 — tertiary
    "border":     "#e2e8f0",   # hairline borders
    "border_d":   "#cbd5e1",   # stronger borders
}

# Accent ramp for stat cards / chart series — distinct, harmonious hues.
CARD_ACCENTS = ["#4f46e5", "#10b981", "#0ea5e9", "#f59e0b", "#ef4444", "#8b5cf6",
                "#ec4899", "#14b8a6"]

# Two-stop gradients (top-left -> bottom-right) for premium stat cards / hero.
GRADIENTS = {
    "indigo":  ("#6366f1", "#4338ca"),
    "emerald": ("#34d399", "#059669"),
    "sky":     ("#38bdf8", "#0284c7"),
    "amber":   ("#fbbf24", "#d97706"),
    "rose":    ("#fb7185", "#e11d48"),
    "violet":  ("#a78bfa", "#7c3aed"),
    "slate":   ("#334155", "#0f172a"),
    "teal":    ("#2dd4bf", "#0d9488"),
}

# Ordered gradient keys so dashboards can map their KPI cards consistently.
GRADIENT_ORDER = ["indigo", "emerald", "sky", "amber", "rose", "violet", "teal", "slate"]

# Status pill colours (bg tint, fg text) keyed by domain status.
STATUS_STYLES = {
    "pending":    ("#fffbeb", "#b45309"),
    "accepted":   ("#eef2ff", "#4338ca"),
    "assigned":   ("#f0f9ff", "#0369a1"),
    "picked_up":  ("#f0f9ff", "#0369a1"),
    "in_transit": ("#eef2ff", "#4338ca"),
    "delivered":  ("#ecfdf5", "#047857"),
    "cancelled":  ("#fef2f2", "#b91c1c"),
    "rejected":   ("#fef2f2", "#b91c1c"),
    "returned":   ("#fff7ed", "#c2410c"),
    "approved":   ("#ecfdf5", "#047857"),
    "flagged":    ("#fff7ed", "#c2410c"),
    "open":       ("#fffbeb", "#b45309"),
    "resolved":   ("#ecfdf5", "#047857"),
    "paid":       ("#ecfdf5", "#047857"),
    "active":     ("#ecfdf5", "#047857"),
    "inactive":   ("#f1f5f9", "#475569"),
}

# ------------------------------------------------------------------ type hierarchy
FONT_FAMILY = "Segoe UI"            # default Windows 11 UI font
FONTS = {
    "display": (FONT_FAMILY, 30, "bold"),
    "h1":      (FONT_FAMILY, 23, "bold"),
    "h2":      (FONT_FAMILY, 17, "bold"),
    "h3":      (FONT_FAMILY, 13, "bold"),
    "body":    (FONT_FAMILY, 11),
    "body_b":  (FONT_FAMILY, 11, "bold"),
    "small":   (FONT_FAMILY, 9),
    "small_b": (FONT_FAMILY, 9, "bold"),
    "tiny":    (FONT_FAMILY, 8),
    "stat":    (FONT_FAMILY, 27, "bold"),
    "brand":   (FONT_FAMILY, 18, "bold"),
    "sidebar": (FONT_FAMILY, 11),
    "sidebar_b": (FONT_FAMILY, 11, "bold"),
}

# ------------------------------------------------------------------ spacing tokens
PAD_XS = 4
PAD_S = 8
PAD_M = 16
PAD_L = 24
PAD_XL = 32
PAD_XXL = 48
RADIUS = 14            # logical corner radius used by drawn (canvas) elements

# ------------------------------------------------------------------ matplotlib
def apply_matplotlib_style():
    """Configure matplotlib globally so embedded charts feel native to the app."""
    import matplotlib
    matplotlib.use("TkAgg")          # Tk backend so figures embed in Tk widgets
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor":  COLORS["card"],
        "axes.facecolor":    COLORS["card"],
        "axes.edgecolor":    COLORS["border"],
        "axes.linewidth":    0.8,
        "axes.labelcolor":   COLORS["muted"],
        "axes.grid":         True,
        "axes.axisbelow":    True,
        "grid.color":        COLORS["border"],
        "grid.linewidth":    0.7,
        "grid.alpha":        0.7,
        "xtick.color":       COLORS["muted"],
        "ytick.color":       COLORS["muted"],
        "xtick.labelsize":   8.5,
        "ytick.labelsize":   8.5,
        "text.color":        COLORS["text"],
        "font.family":       "DejaVu Sans",
        "font.size":         9,
        "axes.titlesize":    11.5,
        "axes.titleweight":  "bold",
        "axes.titlecolor":   COLORS["text"],
        "axes.titlepad":     12,
        "figure.autolayout": True,
    })


def gradient_for(index):
    """Return the (start, end) gradient tuple for a positional index."""
    key = GRADIENT_ORDER[index % len(GRADIENT_ORDER)]
    return GRADIENTS[key]


def accent_for(index):
    """Return a solid accent colour for a positional index."""
    return CARD_ACCENTS[index % len(CARD_ACCENTS)]


def status_style(status):
    """Return (bg, fg) for a status pill, defaulting to a neutral slate."""
    return STATUS_STYLES.get((status or "").lower(), ("#f1f5f9", "#475569"))
