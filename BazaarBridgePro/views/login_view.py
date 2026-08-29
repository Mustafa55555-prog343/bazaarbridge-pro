"""
views/login_view.py
================================================================================
The entry screen for BazaarBridge Pro: a split-panel login + registration form.
Left panel is a branded navy hero; the right panel hosts the auth form inside a
clean white card. On a successful login the app routes the user to the
dashboard for their role.

All input is validated with friendly messages and every action is wrapped so a
bad entry can never crash the application.
================================================================================
"""

import tkinter as tk
import ttkbootstrap as tb

from models import user_model
from utils import validators
from utils.theme import COLORS, FONTS, PAD_S, PAD_M, PAD_L, PAD_XL
from views.components import Field, toast

CARD = None  # set from COLORS at import-time below
CARD = "#ffffff"


class LoginView(tb.Frame):
    """Split-screen authentication view (login + registration tabs)."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.pack(fill="both", expand=True)

        # ---------- Left hero panel (branding) ----------
        hero = tk.Frame(self, bg=COLORS["sidebar"], width=480)
        hero.pack(side="left", fill="both")
        hero.pack_propagate(False)

        wrap = tk.Frame(hero, bg=COLORS["sidebar"])
        wrap.place(relx=0.5, rely=0.5, anchor="center", width=400)
        tk.Label(wrap, text="🛍️", font=("Segoe UI", 52),
                 bg=COLORS["sidebar"], fg="white").pack()
        tk.Label(wrap, text="BazaarBridge Pro", font=("Segoe UI", 25, "bold"),
                 bg=COLORS["sidebar"], fg="white", wraplength=400).pack(pady=(PAD_M, 0))
        tk.Label(wrap, text="Pakistan's Digital Marketplace",
                 font=("Segoe UI", 12), bg=COLORS["sidebar"], wraplength=400,
                 fg=COLORS["sidebar_t"]).pack(pady=(PAD_S, PAD_XL))
        for line in ["Connecting local sellers with buyers nationwide",
                     "Dedicated delivery partner workflow",
                     "Powerful admin analytics & control"]:
            row = tk.Frame(wrap, bg=COLORS["sidebar"])
            row.pack(anchor="w", fill="x", pady=3)
            tk.Label(row, text="✓", font=("Segoe UI", 12, "bold"),
                     bg=COLORS["sidebar"], fg=COLORS["success"]).pack(side="left",
                                                                      anchor="n")
            tk.Label(row, text="  " + line, font=("Segoe UI", 10),
                     bg=COLORS["sidebar"], fg=COLORS["sidebar_t"], wraplength=360,
                     justify="left").pack(side="left", fill="x")

        # Subtle footer anchoring the hero visually.
        tk.Label(hero, text="Powered by Python · SQLite · ttkbootstrap",
                 font=("Segoe UI", 8), bg=COLORS["sidebar"],
                 fg=COLORS["sidebar_t"]).place(relx=0.5, rely=0.97,
                                               anchor="center")

        # ---------- Right form panel ----------
        right = tk.Frame(self, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True)

        # The auth form sits on a white card: a bordered container that gives
        # the form structure and keeps every themed widget (whose default
        # background is white) perfectly seamless.
        self.card = tk.Frame(right, bg=CARD, highlightthickness=1,
                             highlightbackground=COLORS["border"])
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=470)
        self.form_wrap = tk.Frame(self.card, bg=CARD)
        self.form_wrap.pack(fill="both", expand=True, padx=36, pady=32)

        self._build_login()

    # ------------------------------------------------------------ LOGIN form
    def _build_login(self):
        """Render the login form."""
        self._clear()
        f = self.form_wrap
        tk.Label(f, text="Welcome back", font=FONTS["h1"], bg=CARD,
                 fg=COLORS["text"]).pack(anchor="w")
        tk.Label(f, text="Sign in to your BazaarBridge account",
                 font=FONTS["body"], bg=CARD,
                 fg=COLORS["muted"]).pack(anchor="w", pady=(0, PAD_L))

        self.email = Field(f, "Email", default="admin@bazaar.pk")
        self.email.pack(fill="x", pady=PAD_S)
        self.pwd = Field(f, "Password", kind="password", default="password")
        self.pwd.pack(fill="x", pady=PAD_S)

        tb.Button(f, text="Sign In", bootstyle="primary",
                  command=self._do_login).pack(fill="x", ipady=4,
                                               pady=(PAD_L, PAD_S))
        self.email.widget.bind("<Return>", lambda e: self._do_login())
        self.pwd.widget.bind("<Return>", lambda e: self._do_login())

        sw = tk.Frame(f, bg=CARD)
        sw.pack(fill="x", pady=(PAD_S, 0))
        tk.Label(sw, text="New to BazaarBridge?", font=FONTS["small"],
                 bg=CARD, fg=COLORS["muted"]).pack(side="left")
        link = tk.Label(sw, text="  Create an account",
                        font=("Segoe UI", 9, "bold"),
                        bg=CARD, fg=COLORS["primary"], cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: self._build_register())

        # Demo credentials hint with a slim accent bar — instantly explorable.
        hint_row = tk.Frame(f, bg=CARD)
        hint_row.pack(fill="x", pady=(PAD_L, 0))
        tk.Frame(hint_row, bg=COLORS["primary"], width=3).pack(side="left",
                                                               fill="y")
        hint = tk.Frame(hint_row, bg="#eef1fb")
        hint.pack(side="left", fill="both", expand=True)
        tk.Label(hint, text="Demo logins (password: password)",
                 font=("Segoe UI", 9, "bold"), bg="#eef1fb",
                 fg=COLORS["primary"]).pack(anchor="w", padx=PAD_M,
                                            pady=(PAD_S, 2))
        for who in ["admin@bazaar.pk  ·  Admin",
                    "bilal.ahmed@seller.pk  ·  Seller",
                    "ahmed.raza@buyer.pk  ·  Buyer",
                    "junaid.rider@rider.pk  ·  Delivery"]:
            tk.Label(hint, text="•  " + who, font=("Segoe UI", 9), bg="#eef1fb",
                     fg=COLORS["text"]).pack(anchor="w", padx=PAD_M)
        tk.Frame(hint, bg="#eef1fb", height=PAD_S).pack()

    def _do_login(self):
        """Validate credentials and route to the proper dashboard."""
        try:
            email, pwd = self.email.get(), self.pwd.get()
            ok, msg = validators.validate_all(
                validators.validate_required(email, "Email"),
                validators.validate_required(pwd, "Password"),
            )
            if not ok:
                toast(self.app.root, msg, "warning")
                return
            user = user_model.authenticate(email, pwd)
            if not user:
                toast(self.app.root, "Invalid email or password.", "danger")
                return
            if not user["is_active"]:
                toast(self.app.root, "This account is deactivated.", "danger")
                return
            self.app.on_login(user)
        except Exception:
            toast(self.app.root, "Could not sign in. Please try again.", "danger")

    # --------------------------------------------------------- REGISTER form
    def _build_register(self):
        """Render the registration form."""
        self._clear()
        f = self.form_wrap
        tk.Label(f, text="Create your account", font=FONTS["h1"],
                 bg=CARD, fg=COLORS["text"]).pack(anchor="w")
        tk.Label(f, text="Join BazaarBridge as a buyer, seller or rider",
                 font=FONTS["body"], bg=CARD,
                 fg=COLORS["muted"]).pack(anchor="w", pady=(0, PAD_L))

        self.cities = user_model.get_cities()
        city_names = [c["name"] for c in self.cities]

        self.r_name = Field(f, "Full name"); self.r_name.pack(fill="x", pady=PAD_S)
        self.r_email = Field(f, "Email"); self.r_email.pack(fill="x", pady=PAD_S)
        self.r_phone = Field(f, "Phone (03XXXXXXXXX)")
        self.r_phone.pack(fill="x", pady=PAD_S)

        rowf = tk.Frame(f, bg=CARD); rowf.pack(fill="x", pady=PAD_S)
        self.r_role = Field(rowf, "I am a", kind="combo",
                            values=["Buyer", "Seller", "Delivery Partner"],
                            default="Buyer", width=18)
        self.r_role.pack(side="left", expand=True, fill="x", padx=(0, PAD_S))
        self.r_city = Field(rowf, "City", kind="combo", values=city_names,
                            default=city_names[0] if city_names else "", width=18)
        self.r_city.pack(side="left", expand=True, fill="x")

        self.r_pwd = Field(f, "Password (min 6 chars)", kind="password")
        self.r_pwd.pack(fill="x", pady=PAD_S)

        tb.Button(f, text="Create Account", bootstyle="success",
                  command=self._do_register).pack(fill="x", ipady=4,
                                                  pady=(PAD_L, PAD_S))

        sw = tk.Frame(f, bg=CARD); sw.pack(fill="x")
        tk.Label(sw, text="Already have an account?", font=FONTS["small"],
                 bg=CARD, fg=COLORS["muted"]).pack(side="left")
        link = tk.Label(sw, text="  Sign in", font=("Segoe UI", 9, "bold"),
                        bg=CARD, fg=COLORS["primary"], cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: self._build_login())

    def _do_register(self):
        """Validate and create a new account, then return to login."""
        try:
            name = self.r_name.get(); email = self.r_email.get()
            phone = self.r_phone.get(); pwd = self.r_pwd.get()
            role_map = {"Buyer": "buyer", "Seller": "seller",
                        "Delivery Partner": "delivery"}
            role = role_map.get(self.r_role.get(), "buyer")
            ok, msg = validators.validate_all(
                validators.validate_required(name, "Full name"),
                validators.validate_email(email),
                validators.validate_phone(phone),
                validators.validate_password(pwd),
            )
            if not ok:
                toast(self.app.root, msg, "warning")
                return
            city = next((c for c in self.cities if c["name"] == self.r_city.get()),
                        self.cities[0])
            uid, err = user_model.register_user(name, email, pwd, role,
                                                city["city_id"], phone)
            if not uid:
                toast(self.app.root, err, "danger")
                return
            toast(self.app.root, "Account created! Please sign in.", "success")
            self._build_login()
            self.email.set(email)
        except Exception:
            toast(self.app.root, "Could not create account. Try again.", "danger")

    # --------------------------------------------------------------- helpers
    def _clear(self):
        for w in self.form_wrap.winfo_children():
            w.destroy()
