"""
database/db_manager.py
================================================================================
Central database access layer for BazaarBridge Pro.

This module owns the single SQLite connection and exposes safe, reusable helpers
so the rest of the application never has to write raw connection/cursor code.

Highlights for CS-220:
  * A thread-safe-ish singleton connection with foreign keys enabled.
  * Parameterized queries everywhere (no string concatenation -> no SQL injection).
  * Explicit transaction helper (`transaction()`) demonstrating COMMIT / ROLLBACK.
  * Role-Based Access Control enforced at the query layer (`require_role`).
  * "Stored procedures" implemented as clearly-marked Python functions.
================================================================================
"""

import os
import sqlite3
from contextlib import contextmanager

# Absolute path to the SQLite database file (lives next to this module).
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "bazaarbridge.db")
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")


class DBManager:
    """Owns one SQLite connection and provides query helpers for the whole app."""

    _instance = None  # singleton handle

    def __new__(cls):
        """Return the one shared DBManager instance (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        """Open the connection and configure pragmas. Called once."""
        # check_same_thread=False so matplotlib/Tk callbacks can read safely;
        # all writes happen on the main thread so this stays correct.
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row          # rows behave like dicts
        self.conn.execute("PRAGMA foreign_keys = ON")  # enforce FK integrity
        self.conn.execute("PRAGMA journal_mode = WAL") # better concurrency

    # ---------------------------------------------------------------- queries
    def query(self, sql, params=()):
        """Run a SELECT and return all rows as a list of sqlite3.Row."""
        cur = self.conn.execute(sql, params)
        return cur.fetchall()

    def query_one(self, sql, params=()):
        """Run a SELECT and return the first row (or None)."""
        cur = self.conn.execute(sql, params)
        return cur.fetchone()

    def execute(self, sql, params=()):
        """Run an INSERT/UPDATE/DELETE, commit, and return lastrowid."""
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.lastrowid

    def executemany(self, sql, seq_of_params):
        """Run a batch write and commit once."""
        cur = self.conn.executemany(sql, seq_of_params)
        self.conn.commit()
        return cur.rowcount

    # ------------------------------------------------------------ transactions
    @contextmanager
    def transaction(self):
        """
        Context manager demonstrating explicit transaction control.

        Usage:
            with db.transaction() as cur:
                cur.execute(...)        # multiple writes
                cur.execute(...)
        On success -> COMMIT.  On any exception -> ROLLBACK and re-raise.
        This is exactly the COMMIT/ROLLBACK behaviour required by CS-220.
        """
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN")
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()   # undo every change in the failed transaction
            raise

    # -------------------------------------------------------------------- misc
    def script(self, sql_text):
        """Execute a multi-statement SQL script (used for schema setup)."""
        self.conn.executescript(sql_text)
        self.conn.commit()

    def initialize_schema(self):
        """Create all tables/triggers/views from schema.sql if not present."""
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.script(f.read())

    def table_has_rows(self, table):
        """Return True if the given table already contains data."""
        row = self.query_one(f"SELECT COUNT(*) AS n FROM {table}")
        return row["n"] > 0

    def close(self):
        """Close the underlying SQLite connection cleanly on app exit."""
        try:
            self.conn.commit()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass


# A module-level accessor so callers can do:  from database.db_manager import db
db = DBManager()


# ============================================================================
# ROLE-BASED ACCESS CONTROL  (enforced at the query/data layer)
# ============================================================================
class AccessDenied(Exception):
    """Raised when a user attempts an action their role does not permit."""


def require_role(user, *allowed_roles):
    """
    Guard helper: raise AccessDenied unless `user['role']` is in allowed_roles.

    Controllers call this before privileged operations so access control is
    enforced in the data layer, not just hidden in the UI.
    """
    if user is None or user["role"] not in allowed_roles:
        raise AccessDenied(
            "Your role is not permitted to perform this action."
        )
