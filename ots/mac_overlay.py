"""Native macOS window tuning for Tkinter overlays (best effort).

Goal: keep overlay visible to user while reducing capture/share visibility.
Requires pyobjc on macOS; safely no-ops elsewhere.
"""

from __future__ import annotations


def tune_tk_overlay_for_macos(tk_root) -> bool:
    try:
        import platform

        if platform.system() != "Darwin":
            return False

        import objc  # noqa: F401
        from AppKit import (
            NSApp,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowSharingNone,
        )

        app = NSApp()
        if app is None:
            return False

        # Tk bridge is imperfect; we tune all app windows, then rely on overlay being top-most.
        for w in app.windows() or []:
            try:
                behavior = NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
                w.setCollectionBehavior_(behavior)
                w.setLevel_(3)
                # Key line: request exclusion from window sharing/capture APIs.
                if hasattr(w, "setSharingType_"):
                    w.setSharingType_(NSWindowSharingNone)
            except Exception:
                pass
        return True
    except Exception:
        return False
