#!/usr/bin/env python3
"""
Ketoko POS Print Service - Linux replacement for Windows KetokoPrnSvc.exe
Phase 1: Discovery mode — logs all requests, implements /readconf
"""

import json
import os
import subprocess
import sys
import logging
from datetime import datetime
from flask import Flask, request, Response

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "requests.log")

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
    """Format response sesuai pola Ketoko: {number: 0, data: ...}"""
    return json.dumps({"number": 0, "data": data})


def err(msg):
    return json.dumps({"number": 1, "data": msg})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/readconf", methods=["POST", "OPTIONS"])
def readconf():
    if request.method == "OPTIONS":
        return Response(status=200)
    try:
        cfg = load_config()
        data = [
            {"confname": "PRT_TIPE_KONEKSI",    "confvalue": cfg["tipe_koneksi"]},
            {"confname": "PRT_USB_DEVICE",       "confvalue": cfg["usb_device"]},
            {"confname": "PRT_IP_ADDRESS",       "confvalue": cfg["ip_address"]},
            {"confname": "PRT_IP_ADDRESS_PORT",  "confvalue": cfg["ip_address_port"]},
            {"confname": "PRT_BT_PRINTER_ADDRESS","confvalue": cfg["bt_address"]},
            {"confname": "PRT_BT_PRINTER_NAME",  "confvalue": cfg["bt_name"]},
            {"confname": "PRT_UKURAN_KERTAS",    "confvalue": cfg["ukuran_kertas"]},
            {"confname": "PRT_JML_PRINT_NOTA",   "confvalue": cfg["jml_print_nota"]},
            {"confname": "PRT_JML_BARIS_KOSONG", "confvalue": cfg["jml_baris_kosong"]},
            {"confname": "PRT_AUTOCUTTER",       "confvalue": cfg["autocutter"]},
            {"confname": "PRT_CASHDRAWER",       "confvalue": cfg["cashdrawer"]},
            {"confname": "PRT_LOGO_AKTIF",       "confvalue": cfg["logo_aktif"]},
            {"confname": "PRT_ALIGN_HEADER",     "confvalue": cfg["align_header"]},
            {"confname": "PRT_ALIGN_FOOTER",     "confvalue": cfg["align_footer"]},
            {"confname": "PRT_OPSI_BARIS",       "confvalue": cfg["opsi_baris"]},
            {"confname": "PRT_OPSI_PELSES",      "confvalue": cfg["opsi_pelses"]},
            {"confname": "PRT_KETERANGAN",       "confvalue": cfg["keterangan"]},
        ]
        log.info("readconf → OK")
        return Response(ok(data), mimetype="text/plain")
    except Exception as e:
        log.error(f"readconf error: {e}")
        return Response(err(str(e)), mimetype="text/plain")


@app.route("/print", methods=["POST", "OPTIONS"])
@app.route("/printusb", methods=["POST", "OPTIONS"])
@app.route("/printnet", methods=["POST", "OPTIONS"])
@app.route("/printbt", methods=["POST", "OPTIONS"])
def handle_print():
    """Tangkap semua kemungkinan endpoint print — log data_print untuk discovery."""
    if request.method == "OPTIONS":
        return Response(status=200)

    endpoint = request.path
    raw = request.get_data(as_text=True)
    form_data = request.form.get("data_print", "")

    log.info(f"[DISCOVERY] endpoint={endpoint}")
    log.info(f"[DISCOVERY] raw_body={raw[:500]}")
    log.info(f"[DISCOVERY] data_print={form_data[:500]}")

    # Simpan ke file untuk analisis
    with open(os.path.join(BASE_DIR, "captured_print.log"), "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Time: {datetime.now()}\n")
        f.write(f"Endpoint: {endpoint}\n")
        f.write(f"data_print:\n{form_data}\n")

    cfg = load_config()
    usb_device = cfg.get("usb_device", "/dev/usb/lp0")

    if form_data and os.path.exists(usb_device):
        try:
            import base64
            data_bytes = base64.b64decode(form_data)
            with open(usb_device, "wb") as printer:
                printer.write(data_bytes)
            log.info(f"Sent {len(data_bytes)} bytes to {usb_device}")
            return Response(ok("Print berhasil"), mimetype="text/plain")
        except Exception as e:
            log.error(f"Print error: {e}")
            return Response(err(str(e)), mimetype="text/plain")

    return Response(ok("Logged (printer not connected)"), mimetype="text/plain")


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "OPTIONS"])
def catch_all(path):
    """Tangkap semua request yang belum diketahui — untuk discovery."""
    raw = request.get_data(as_text=True)
    log.info(f"[UNKNOWN] /{path} | body={raw[:300]}")
    return Response(ok(""), mimetype="text/plain")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Ketoko Print Service starting on http://localhost:5488")
    log.info(f"Config: {CONFIG_FILE}")
    log.info(f"Log: {LOG_FILE}")
    app.run(host="127.0.0.1", port=5488, debug=False)
