#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ketoko Print Service — Status GUI
Cross-platform: Windows (tested), Linux (not tested), macOS (not tested)
"""

import json
import os
import sys
import socket
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SERVICE_URL = "http://127.0.0.1:5488"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_printer_cfg():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)["printer"]


def get_local_ips():
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip and ip != "127.0.0.1":
                ips.append(ip)
    except Exception:
        pass
    return list(dict.fromkeys(ips)) or ["127.0.0.1"]


def get_printers():
    if sys.platform == "win32":
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [p[2] for p in printers]
        except Exception:
            return []
    else:  # Linux / macOS — not tested
        try:
            out = subprocess.run(["lpstat", "-a"], capture_output=True, text=True).stdout
            return [line.split()[0] for line in out.splitlines() if line.strip()]
        except Exception:
            return []


def check_service():
    try:
        import urllib.request
        with urllib.request.urlopen(f"{SERVICE_URL}/status", timeout=2) as r:
            data = json.loads(r.read())
            return data["ret"][0]["num"] == 0
    except Exception:
        return False


def do_testprint():
    try:
        import urllib.request
        req = urllib.request.Request(f"{SERVICE_URL}/testprint", method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return data["ret"][0]["num"] == 0, data["ret"][0].get("msg", "")
    except Exception as e:
        return False, str(e)


# ── Window ────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ketoko POS Print Service")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        w, h = 420, 360
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build()
        self._refresh()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg="#1565C0", height=48)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Ketoko POS Print Service",
                 font=("Segoe UI", 12, "bold"), fg="white", bg="#1565C0").pack(
                 side="left", padx=14, pady=10)

        # Status
        self._status_frame = tk.Frame(self, bg="#e8f5e9", bd=1, relief="solid")
        self._status_frame.pack(fill="x", padx=12, pady=(10, 4))
        self._dot = tk.Label(self._status_frame, text="●", font=("Segoe UI", 12),
                             fg="#4CAF50", bg="#e8f5e9")
        self._dot.pack(side="left", padx=(8, 4), pady=5)
        self._status_lbl = tk.Label(self._status_frame, text="Memeriksa...",
                                    font=("Segoe UI", 9), bg="#e8f5e9")
        self._status_lbl.pack(side="left", pady=5)

        # Info rows
        info = tk.Frame(self, bg="#f5f5f5")
        info.pack(fill="x", padx=12, pady=4)

        def row(parent, label, var):
            f = tk.Frame(parent, bg="#f5f5f5")
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, font=("Segoe UI", 9), fg="#555",
                     bg="#f5f5f5", width=14, anchor="w").pack(side="left")
            tk.Label(f, textvariable=var, font=("Segoe UI", 9, "bold"),
                     fg="#1a1a1a", bg="#f5f5f5", anchor="w").pack(side="left")

        self._ip_var   = tk.StringVar(value="-")
        self._port_var = tk.StringVar(value="5488")

        row(info, "IP Lokal",     self._ip_var)
        row(info, "Service Port", self._port_var)

        # Printer selector
        prow = tk.Frame(self, bg="#f5f5f5")
        prow.pack(fill="x", padx=12, pady=4)
        tk.Label(prow, text="Printer:", font=("Segoe UI", 9), fg="#555",
                 bg="#f5f5f5", width=14, anchor="w").pack(side="left")
        self._printer_var = tk.StringVar()
        self._printer_cb  = ttk.Combobox(prow, textvariable=self._printer_var,
                                         state="readonly", width=26,
                                         font=("Segoe UI", 9))
        self._printer_cb.pack(side="left")
        tk.Button(prow, text="Simpan", font=("Segoe UI", 9),
                  bg="#1565C0", fg="white", relief="flat", padx=10, pady=2,
                  cursor="hand2", command=self._on_save_printer).pack(side="left", padx=(6, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=8)

        # Buttons
        btn = tk.Frame(self, bg="#f5f5f5")
        btn.pack(pady=4)

        tk.Button(btn, text="Test Print",
                  font=("Segoe UI", 10), bg="#2E7D32", fg="white",
                  relief="flat", padx=20, pady=6, cursor="hand2",
                  command=self._on_test).pack(side="left", padx=6)

        tk.Button(btn, text="Refresh",
                  font=("Segoe UI", 10), bg="#616161", fg="white",
                  relief="flat", padx=20, pady=6, cursor="hand2",
                  command=self._refresh).pack(side="left", padx=6)

        # Watermark
        tk.Label(self, text="by xbnn29", font=("Segoe UI", 7),
                 fg="#bdbdbd", bg="#f5f5f5").pack(side="bottom", pady=6)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _refresh(self):
        # IPs
        self._ip_var.set("  |  ".join(get_local_ips()))

        # Populate printer dropdown
        printers = get_printers()
        self._printer_cb.config(values=printers)
        try:
            cfg = load_printer_cfg()
            if sys.platform == "win32":
                current = cfg.get("usb_device_windows", "")
            elif sys.platform.startswith("linux"):
                current = cfg.get("usb_device_linux", "")
            else:
                current = cfg.get("usb_device_mac", "")
            if current and current in printers:
                self._printer_var.set(current)
            elif printers:
                self._printer_var.set(printers[0])
        except Exception:
            if printers:
                self._printer_var.set(printers[0])

        # Service status (async)
        def _check():
            ok = check_service()
            self.after(0, lambda: self._set_status(ok))
            self.after(6000, self._poll)

        threading.Thread(target=_check, daemon=True).start()

    def _poll(self):
        def _check():
            ok = check_service()
            self.after(0, lambda: self._set_status(ok))
            self.after(6000, self._poll)
        threading.Thread(target=_check, daemon=True).start()

    def _set_status(self, ok: bool):
        if ok:
            self._status_frame.config(bg="#e8f5e9")
            self._dot.config(fg="#4CAF50", bg="#e8f5e9")
            self._status_lbl.config(text="Service aktif — port 5488", fg="#2E7D32", bg="#e8f5e9")
        else:
            self._status_frame.config(bg="#ffebee")
            self._dot.config(fg="#e53935", bg="#ffebee")
            self._status_lbl.config(text="Service tidak aktif", fg="#c62828", bg="#ffebee")

    def _on_save_printer(self):
        name = self._printer_var.get()
        if not name:
            return
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                full = json.load(f)
            if sys.platform == "win32":
                full["printer"]["usb_device_windows"] = name
            elif sys.platform.startswith("linux"):
                full["printer"]["usb_device_linux"] = name
            else:
                full["printer"]["usb_device_mac"] = name
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(full, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Berhasil", f"Printer disimpan:\n{name}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal simpan:\n{e}")

    def _on_test(self):
        self._status_lbl.config(text="Mengirim test print...")
        self.update()

        def _run():
            ok, msg = do_testprint()
            self.after(0, lambda: messagebox.showinfo(
                "Test Print",
                "Test print berhasil!" if ok else f"Gagal: {msg}"
            ))
            self.after(0, self._refresh)

        threading.Thread(target=_run, daemon=True).start()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().mainloop()
