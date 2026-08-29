# =============================================================================
# BazaarBridge Pro  -  Application Entry Point
# CS-220 Database Systems  |  NUST SEECS
# Student: Mustafa Shahid  |  Class: BSCS-14B  |  CMS ID: 500889
# -----------------------------------------------------------------------------
# This is the single launch point for the whole application. Running
# `python main.py` will:
#   1. Make sure the database exists and the schema is loaded.
#   2. Seed rich sample data the very first time (if the database is empty).
#   3. Open the login screen.
#   4. Route each user to the correct dashboard after they sign in.
# The whole app is wrapped in safe error handling so the user never sees a
# raw Python traceback.
# =============================================================================

import utils.tkfix  # noqa: F401  (must precede ttkbootstrap widget use)
import sys
import traceback

import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox

# --- internal modules -------------------------------------------------------
from utils.theme import BASE_THEME
from database.db_manager import db
from database import seed as seed_module

from views.login_view import LoginView
from views.buyer_dashboard import BuyerDashboard
from views.seller_dashboard import SellerDashboard
from views.delivery_dashboard import DeliveryDashboard
from views.admin_dashboard import AdminDashboard


# Maps the role stored in the database to the dashboard class that serves it.
DASHBOARDS = {
    "buyer": BuyerDashboard,
    "seller": SellerDashboard,
    "delivery": DeliveryDashboard,
    "admin": AdminDashboard,
}


class BazaarBridgeApp:
    """The top-level application controller.

    Owns the main window, the currently signed-in user, and the currently
    shown screen. Every dashboard talks back to this object through a small,
    fixed contract: ``root``, ``on_login``, ``logout`` and ``update_badge``.
    """

    def __init__(self):
        """Build the main window and prepare the database before any UI shows."""
        # Prepare the data layer first so the login screen has something to talk to.
        self._prepare_database()

        # Create the main themed window.
        self.root = tb.Window(themename=BASE_THEME)
        self.root.title("BazaarBridge Pro  -  Pakistan's Local Marketplace")

        # Normalise the font scaling factor. ttkbootstrap makes the process
        # DPI-aware on Windows, which enlarges fonts on 125%/150% displays while
        # fixed-width panels stay the same — causing text to clip. Pinning the
        # scaling keeps every screen laid out exactly as designed at any DPI.
        try:
            self.root.tk.call("tk", "scaling", 1.333)
        except Exception:
            pass

        self.root.geometry("1500x920")
        self.root.minsize(1180, 740)
        self._center_window(1500, 920)
        # Open maximised so every screen has full room to breathe (Windows).
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.attributes("-zoomed", True)
            except Exception:
                pass

        # Global safety net: any unhandled exception raised inside a Tk callback
        # (a button click, a bound event, an `after` job) is routed here so the
        # user always sees a clean, friendly toast instead of a raw traceback,
        # and the application keeps running rather than crashing.
        self.root.report_callback_exception = self._handle_callback_exception

        # Track the logged-in user and the live screen so we can swap them cleanly.
        self.user = None
        self.current_view = None

        # A graceful "X" / close handler.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start on the login screen.
        self.show_login()

    # ------------------------------------------------------------------ setup
    def _prepare_database(self):
        """Ensure the schema is loaded and seed sample data on first run."""
        try:
            db.initialize_schema()
            # Only seed when the database is brand new (no users yet) so we
            # never duplicate data on subsequent launches.
            if not db.table_has_rows("users"):
                seed_module.seed()
        except Exception:
            # If anything goes wrong this early, show it plainly and stop,
            # because the app cannot run without its database.
            traceback.print_exc()
            try:
                Messagebox.show_error(
                    "The application could not prepare its database and needs to close.",
                    "Startup Error",
                )
            except Exception:
                pass
            sys.exit(1)

    def _center_window(self, width, height):
        """Place the window in the middle of the screen."""
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # --------------------------------------------------------------- contract
    def show_login(self):
        """Swap whatever is on screen for a fresh login view."""
        self._swap(LoginView(self.root, self))

    def on_login(self, user):
        """Called by the login view once credentials check out.

        Stores the user and opens the dashboard that matches their role.
        """
        self.user = user
        dashboard_cls = DASHBOARDS.get(user["role"])
        if dashboard_cls is None:
            # Should never happen because roles are constrained in the schema,
            # but we fail softly instead of crashing.
            self.notify_error("This account has an unknown role and cannot be opened.")
            self.logout()
            return
        try:
            self._swap(dashboard_cls(self.root, self, user))
        except Exception:
            traceback.print_exc()
            self.notify_error("Something went wrong opening your dashboard.")
            self.logout()

    def logout(self):
        """Forget the current user and return to the login screen."""
        self.user = None
        self.show_login()

    def update_badge(self):
        """Refresh notification badges.

        Each dashboard manages its own header badge, so at the application
        level this is intentionally a no-op hook. It exists because every
        dashboard calls ``app.update_badge()`` and relies on it being present.
        """
        return None

    # ----------------------------------------------------------------- helpers
    def _swap(self, new_view):
        """Destroy the current screen and show the new one full-window."""
        old = self.current_view
        self.current_view = new_view
        new_view.pack(fill="both", expand=True)
        if old is not None:
            old.destroy()

    def notify_error(self, message):
        """Show a friendly error dialog without ever leaking a traceback."""
        try:
            Messagebox.show_error(message, "BazaarBridge Pro")
        except Exception:
            print("Error:", message)

    def _handle_callback_exception(self, exc_type, exc_value, exc_tb):
        """
        Catch-all for exceptions raised inside Tk callbacks (button clicks,
        bound events, `after` jobs). Logs the technical detail to the console
        for debugging and shows the user a calm, friendly toast — the app never
        crashes and never displays a raw error.
        """
        try:
            traceback.print_exception(exc_type, exc_value, exc_tb)
        except Exception:
            pass
        try:
            from views.components import toast
            toast(self.root,
                  "Something didn't work as expected. Please try again.",
                  "danger")
        except Exception:
            # Last-resort fallback if even the toast cannot be shown.
            try:
                self.notify_error("Something didn't work as expected. "
                                  "Please try again.")
            except Exception:
                pass

    def _on_close(self):
        """Close the database connection cleanly, then exit."""
        try:
            db.close()
        except Exception:
            pass
        self.root.destroy()

    # -------------------------------------------------------------------- run
    def _maximise(self):
        """Maximise the window. Called after the window is mapped so it works
        reliably on Windows (calling it during __init__ is often ignored)."""
        for attempt in ("zoomed", "-zoomed"):
            try:
                if attempt == "zoomed":
                    self.root.state("zoomed")
                else:
                    self.root.attributes("-zoomed", True)
                return
            except Exception:
                continue

    def run(self):
        """Start the Tk event loop."""
        # Maximise once the window has been mapped (more reliable than doing it
        # during construction, which Windows frequently ignores).
        self.root.after(40, self._maximise)
        self.root.mainloop()


def main():
    """Construct and launch the application with a top-level safety net."""
    try:
        app = BazaarBridgeApp()
        app.run()
    except Exception:
        # Absolute last line of defence: print a clean message instead of a
        # scary traceback if something unexpected escapes everything else.
        traceback.print_exc()
        print("\nBazaarBridge Pro had to close unexpectedly.")


if __name__ == "__main__":
    main()
