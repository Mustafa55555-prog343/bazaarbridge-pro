"""
utils/security.py
================================================================================
Password hashing helpers. Passwords are NEVER stored in plaintext: we store a
salted SHA-256 hash. This is intentionally simple (no external dependency) but
demonstrates the correct principle of never persisting raw credentials.
================================================================================
"""

import hashlib
import os

# A fixed application salt combined with a per-call component keeps the demo
# deterministic for the seeded accounts while still salting the hash.
_APP_SALT = "BazaarBridgePro::CS220::NUST"


def hash_password(password):
    """Return a salted SHA-256 hex digest of the given password string."""
    salted = (_APP_SALT + password).encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def verify_password(password, stored_hash):
    """Return True if `password` hashes to the stored hash."""
    return hash_password(password) == stored_hash
