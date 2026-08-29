"""
utils/tkfix.py
================================================================================
ttkbootstrap re-skins standard tkinter widgets: its constructor wrapper applies
the active theme's colours to every plain tk widget *after* it is built, which
silently overrides any explicit ``bg`` / ``fg`` passed at construction. The
wrapper, however, honours an ``autostyle=False`` flag that tells ttkbootstrap to
leave the widget alone.

This module installs a tiny, idempotent shim around the pure-tk widget classes:
whenever a widget is constructed with explicit colour options, it injects
``autostyle=False`` so those colours are preserved. Widgets created without
colour options are untouched and keep ttkbootstrap's themed defaults. ttk /
ttkbootstrap widgets are never affected.

Import this once before any widget is built (main.py and the shared components
module both do).
================================================================================
"""

import tkinter as tk

# Ensure ttkbootstrap has already wrapped the tk widget constructors before we
# wrap them ourselves, so our shim sits *outside* ttkbootstrap's wrapper and the
# injected autostyle flag is consumed correctly.
import ttkbootstrap as _tb  # noqa: F401

# Colour options whose presence means the caller wants an explicit colour kept.
_COLOR_OPTS = (
    "bg", "fg", "background", "foreground",
    "activebackground", "activeforeground",
    "highlightbackground", "highlightcolor",
    "insertbackground", "selectbackground", "selectforeground",
    "disabledforeground", "readonlybackground",
)

_INSTALLED = False


def install():
    """Preserve explicit colours on pure-tk widgets under ttkbootstrap. Idempotent."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    for cls in (tk.Label, tk.Frame, tk.Canvas, tk.Toplevel,
                tk.Button, tk.Entry, tk.Text):
        original_init = cls.__init__

        def _make(orig):
            def __init__(self, *args, **kwargs):
                # If the caller specified colours and hasn't already chosen an
                # autostyle behaviour, opt out of ttkbootstrap's re-styling so
                # the explicit colours survive.
                if "autostyle" not in kwargs and any(k in kwargs for k in _COLOR_OPTS):
                    kwargs["autostyle"] = False
                try:
                    orig(self, *args, **kwargs)
                except TypeError:
                    # A non-ttkbootstrap-wrapped constructor won't accept
                    # autostyle; fall back gracefully.
                    kwargs.pop("autostyle", None)
                    orig(self, *args, **kwargs)
            return __init__

        cls.__init__ = _make(original_init)


# Install on import.
install()
