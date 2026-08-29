"""
utils/validators.py
================================================================================
Input-validation helpers used by every form in the application. Each function
returns a tuple (ok: bool, message: str). Controllers/views call these and show
the friendly message to the user when ok is False — so a user never sees a raw
Python error, only clear guidance.
================================================================================
"""

import re

# Basic but practical email pattern.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Pakistani phone numbers like 03XXXXXXXXX or +923XXXXXXXXX.
_PHONE_RE = re.compile(r"^(\+92|0)?3\d{9}$")


def validate_required(value, field="This field"):
    """Ensure a text value is present and not just whitespace."""
    if value is None or str(value).strip() == "":
        return False, f"{field} is required."
    return True, ""


def validate_email(value):
    """Validate an email address format."""
    if not value or not _EMAIL_RE.match(value.strip()):
        return False, "Please enter a valid email address."
    return True, ""


def validate_phone(value):
    """Validate a Pakistani mobile number (optional field allowed empty)."""
    if value is None or value.strip() == "":
        return True, ""  # phone is optional
    if not _PHONE_RE.match(value.strip()):
        return False, "Enter a valid phone like 03001234567."
    return True, ""


def validate_password(value):
    """Require at least 6 characters for a password."""
    if not value or len(value) < 6:
        return False, "Password must be at least 6 characters."
    return True, ""


def validate_positive_number(value, field="Value"):
    """Ensure the value parses to a number >= 0."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False, f"{field} must be a number."
    if num < 0:
        return False, f"{field} cannot be negative."
    return True, ""


def validate_positive_int(value, field="Value"):
    """Ensure the value parses to an integer >= 0."""
    try:
        num = int(value)
    except (TypeError, ValueError):
        return False, f"{field} must be a whole number."
    if num < 0:
        return False, f"{field} cannot be negative."
    return True, ""


def validate_all(*results):
    """
    Combine several (ok, message) results. Returns the first failure, or
    (True, "") if every check passed. Lets a form validate many fields cleanly.
    """
    for ok, msg in results:
        if not ok:
            return False, msg
    return True, ""
