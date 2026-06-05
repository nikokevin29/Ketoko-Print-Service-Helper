#!/usr/bin/env python3
"""
Ketoko POS Print Service — cross-platform replacement for KetokoPrnSvc.exe
Supports: Linux, macOS (Intel & Apple Silicon), Windows
"""

import base64
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import logging
from datetime import datetime
from flask import Flask, request, Response

# ── Platform detection ────────────────────────────────────────────────────────
PLATFORM = sys.platform          # linux / darwin / win32
ARCH     = platform.machine()    # x86_64 / arm64 / AMD64

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE    = os.path.join(BASE_DIR, "requests.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

app = Flask(__name__)


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)["printer"]


def ok(data=""):
    return json.dumps({"number": 0, "data": data})


def err(msg):
    return json.dumps({"number": 1, "data": msg})


# ── Print backends ────────────────────────────────────────────────────────────

def print_usb_linux(data: bytes, device: str) -> None:
    """Write raw ESC/POS bytes directly to USB device node."""
    with open(device, "wb") as f:
        f.write(data)


def print_usb_mac(data: bytes, printer_name: str) -> None:
    """Send raw bytes via CUPS on macOS (built-in)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        subprocess.run(
            ["lpr", "-P", printer_name, "-o", "raw", tmp_path],
            check=True,
        )
    finally:
        os.unlink(tmp_path)


def print_usb_windows(data: bytes, printer_name: str) -> None:
    """Send raw bytes via win32print (pywin32)."""
    try:
        import win32print
        h = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(h, 1, ("Receipt", None, "RAW"))
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, data)
            win32print.EndPagePrinter(h)
            win32print.EndDocPrinter(h)
        finally:
            win32print.ClosePrinter(h)
    except ImportError:
        raise RuntimeError("pywin32 not installed. Run: pip install pywin32")


def print_network(data: bytes, ip: str, port: int) -> None:
    """Send raw ESC/POS to network printer (port 9100 / JetDirect)."""
    with socket.create_connection((ip, port), timeout=5) as s:
        s.sendall(data)


def send_to_printer(data: bytes, cfg: dict) -> None:
    tipe = cfg.get("tipe_koneksi", "1")

    if tipe == "2":
        ip   = cfg["ip_address"]
        port = int(cfg.get("ip_address_port", 9100))
        log.info(f"Print → network {ip}:{port} ({len(data)} bytes)")
        print_network(data, ip, port)

    elif tipe == "1":
        if PLATFORM.startswith("linux"):
            device = cfg.get("usb_device_linux", "/dev/usb/lp0")
            log.info(f"Print → USB Linux {device} ({len(data)} bytes)")
            print_usb_linux(data, device)

        elif PLATFORM == "darwin":
            name = cfg.get("usb_device_mac", "")
            if not name:
                raise RuntimeError("usb_device_mac belum diisi di config.json")
            log.info(f"Print → USB macOS CUPS '{name}' ({len(data)} bytes)")
            print_usb_mac(data, name)

        elif PLATFORM == "win32":
            name = cfg.get("usb_device_windows", "")
            if not name:
                raise RuntimeError("usb_device_windows belum diisi di config.json")
            log.info(f"Print → USB Windows '{name}' ({len(data)} bytes)")
            print_usb_windows(data, name)

        else:
            raise RuntimeError(f"Platform tidak didukung: {PLATFORM}")

    else:
        raise RuntimeError(f"tipe_koneksi '{tipe}' belum didukung (Phase 3: BT)")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/readconf", methods=["POST", "OPTIONS"])
def readconf():
    if request.method == "OPTIONS":
        return Response(status=200)
    try:
        cfg  = load_config()
        # Kirim nama device sesuai platform yang sedang berjalan
        if PLATFORM.startswith("linux"):
            usb_val = cfg.get("usb_device_linux", "/dev/usb/lp0")
        elif PLATFORM == "darwin":
            usb_val = cfg.get("usb_device_mac", "")
        else:
            usb_val = cfg.get("usb_device_windows", "")

        data = [
            {"confname": "PRT_TIPE_KONEKSI",     "confvalue": cfg["tipe_koneksi"]},
            {"confname": "PRT_USB_DEVICE",        "confvalue": usb_val},
            {"confname": "PRT_IP_ADDRESS",        "confvalue": cfg["ip_address"]},
            {"confname": "PRT_IP_ADDRESS_PORT",   "confvalue": cfg["ip_address_port"]},
            {"confname": "PRT_BT_PRINTER_ADDRESS","confvalue": cfg["bt_address"]},
            {"confname": "PRT_BT_PRINTER_NAME",   "confvalue": cfg["bt_name"]},
            {"confname": "PRT_UKURAN_KERTAS",     "confvalue": cfg["ukuran_kertas"]},
            {"confname": "PRT_JML_PRINT_NOTA",    "confvalue": cfg["jml_print_nota"]},
            {"confname": "PRT_JML_BARIS_KOSONG",  "confvalue": cfg["jml_baris_kosong"]},
            {"confname": "PRT_AUTOCUTTER",        "confvalue": cfg["autocutter"]},
            {"confname": "PRT_CASHDRAWER",        "confvalue": cfg["cashdrawer"]},
            {"confname": "PRT_LOGO_AKTIF",        "confvalue": cfg["logo_aktif"]},
            {"confname": "PRT_ALIGN_HEADER",      "confvalue": cfg["align_header"]},
            {"confname": "PRT_ALIGN_FOOTER",      "confvalue": cfg["align_footer"]},
            {"confname": "PRT_OPSI_BARIS",        "confvalue": cfg["opsi_baris"]},
            {"confname": "PRT_OPSI_PELSES",       "confvalue": cfg["opsi_pelses"]},
            {"confname": "PRT_KETERANGAN",        "confvalue": cfg["keterangan"]},
        ]
        log.info("readconf → OK")
        return Response(ok(data), mimetype="text/plain")
    except Exception as e:
        log.error(f"readconf error: {e}")
        return Response(err(str(e)), mimetype="text/plain")


@app.route("/print",     methods=["POST", "OPTIONS"])
@app.route("/printusb",  methods=["POST", "OPTIONS"])
@app.route("/printnet",  methods=["POST", "OPTIONS"])
@app.route("/printbt",   methods=["POST", "OPTIONS"])
def handle_print():
    if request.method == "OPTIONS":
        return Response(status=200)

    endpoint  = request.path
    raw       = request.get_data(as_text=True)
    form_data = request.form.get("data_print", "")

    log.info(f"[PRINT] endpoint={endpoint}")

    # Selalu log untuk discovery
    with open(os.path.join(BASE_DIR, "captured_print.log"), "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Time:     {datetime.now()}\n")
        f.write(f"Platform: {PLATFORM} / {ARCH}\n")
        f.write(f"Endpoint: {endpoint}\n")
        f.write(f"data_print:\n{form_data[:2000]}\n")

    if not form_data:
        return Response(ok("Logged (no data)"), mimetype="text/plain")

    try:
        data_bytes = base64.b64decode(form_data)
        cfg        = load_config()
        send_to_printer(data_bytes, cfg)
        return Response(ok("Print berhasil"), mimetype="text/plain")
    except Exception as e:
        log.warning(f"Print skipped: {e}")
        return Response(ok(f"Logged ({e})"), mimetype="text/plain")


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/<path:path>",             methods=["GET", "POST", "OPTIONS"])
def catch_all(path):
    raw = request.get_data(as_text=True)
    log.info(f"[UNKNOWN] /{path} | body={raw[:300]}")
    return Response(ok(""), mimetype="text/plain")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info(f"Ketoko Print Service — platform={PLATFORM} arch={ARCH}")
    log.info(f"Listening on http://127.0.0.1:5488")
    app.run(host="127.0.0.1", port=5488, debug=False)
