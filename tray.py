#!/usr/bin/env python3
"""
Ketoko Print Service — Windows System Tray Launcher
Runs the Flask service in a background thread and shows a tray icon.
"""

import sys
import os
import threading
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Tray icon ─────────────────────────────────────────────────────────────────

def _make_icon():
    """Generate a simple printer icon as PIL Image."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Printer body
    d.rectangle([8, 20, 56, 44], fill=(60, 130, 200))
    # Paper tray top
    d.rectangle([16, 12, 48, 24], fill=(80, 160, 220))
    # Paper output
    d.rectangle([18, 40, 46, 54], fill=(240, 240, 240))
    # Paper lines
    d.rectangle([22, 44, 42, 45], fill=(180, 180, 180))
    d.rectangle([22, 48, 38, 49], fill=(180, 180, 180))
    return img


def _open_status():
    webbrowser.open("http://127.0.0.1:5488/status")


def _run_tray(stop_event):
    try:
        import pystray
        from pystray import MenuItem as Item

        icon_img = _make_icon()

        def on_quit(icon, item):
            stop_event.set()
            icon.stop()

        menu = pystray.Menu(
            Item("Ketoko Print Service", None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Lihat Status", lambda icon, item: _open_status()),
            Item("Keluar", on_quit),
        )

        icon = pystray.Icon(
            "KetokoPrint",
            icon_img,
            "Ketoko Print Service — aktif di port 5488",
            menu,
        )
        icon.run()
    except Exception as e:
        print(f"[TRAY] Error: {e}")
        stop_event.set()


# ── Service thread ─────────────────────────────────────────────────────────────

def _run_service(stop_event):
    """Import and start the Flask app. Blocks until stop_event is set."""
    # Suppress Flask banner — redirect to log file
    import logging
    import service as svc

    # Run Flask in a daemon thread so it dies when main exits
    flask_thread = threading.Thread(
        target=lambda: svc.app.run(host="127.0.0.1", port=5488, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    stop_event.wait()   # Block until quit from tray


# ── Auto-start registry helper ────────────────────────────────────────────────

def _register_autostart():
    """Add tray.py to Windows startup registry (HKCU)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        py_exe = sys.executable
        script = os.path.join(BASE_DIR, "tray.py")
        value = f'"{py_exe}" "{script}"'
        winreg.SetValueEx(key, "KetokoPrintService", 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        print(f"[AUTOSTART] Registered: {value}")
    except Exception as e:
        print(f"[AUTOSTART] Failed: {e}")


def _unregister_autostart():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, "KetokoPrintService")
        winreg.CloseKey(key)
        print("[AUTOSTART] Removed from startup")
    except Exception as e:
        print(f"[AUTOSTART] {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--register-autostart" in sys.argv:
        _register_autostart()
        sys.exit(0)
    if "--unregister-autostart" in sys.argv:
        _unregister_autostart()
        sys.exit(0)

    stop_event = threading.Event()

    # Start Flask service in thread
    svc_thread = threading.Thread(target=_run_service, args=(stop_event,), daemon=True)
    svc_thread.start()

    # Run tray in main thread (required by most OS tray implementations)
    _run_tray(stop_event)
