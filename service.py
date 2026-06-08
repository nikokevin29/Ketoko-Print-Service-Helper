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
from urllib.parse import parse_qs
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
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
# Fix Windows console encoding for non-ASCII chars
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
log = logging.getLogger(__name__)

app = Flask(__name__)


def get_form_field(field: str) -> str:
    """Get form field — works even if Content-Type header is missing/wrong."""
    val = request.form.get(field, "")
    if not val:
        # Flask won't parse form if Content-Type isn't application/x-www-form-urlencoded.
        # Ketoko Web sends raw body without proper Content-Type — parse manually.
        raw = request.get_data(as_text=True)
        parsed = parse_qs(raw, keep_blank_values=True)
        val = parsed.get(field, [""])[0]
    return val


def b64decode(s: str) -> bytes:
    """base64 decode with automatic padding fix."""
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)["printer"]


MIME = "text/html"


def ok(data=""):
    return json.dumps({"ret": [{"num": 0, "msg": "", "data": data}]})


def err(msg):
    return json.dumps({"ret": [{"num": -1, "msg": msg, "data": ""}]})


# ── ESC/POS helpers ───────────────────────────────────────────────────────────

ESC_INIT        = b"\x1b\x40"
ESC_CUT_FULL    = b"\x1d\x56\x00"
ESC_CUT_PARTIAL = b"\x1d\x56\x42\x00"
# ESC p m t1 t2 — pulse cash drawer on pin 2 (m=0) or pin 5 (m=1)
ESC_DRAWER_PIN2 = b"\x1b\x70\x00\x19\xfa"
ESC_DRAWER_PIN5 = b"\x1b\x70\x01\x19\xfa"
ESC_FEED        = b"\x1b\x64\x04"          # feed 4 lines


def build_cut_command(cfg: dict) -> bytes:
    """Return cut ESC/POS bytes based on config, or empty if disabled."""
    if cfg.get("autocutter", "0") == "1":
        return ESC_CUT_PARTIAL
    return b""


def build_drawer_command(cfg: dict) -> bytes:
    """Return cash drawer pulse bytes if enabled in config."""
    if cfg.get("cashdrawer", "0") == "1":
        return ESC_DRAWER_PIN2
    return b""


def build_test_receipt(cfg: dict) -> bytes:
    """Generate a self-test ESC/POS receipt for RPP02/TM-U220."""
    paper = cfg.get("ukuran_kertas", "22")
    width = 32 if paper == "32" else 28   # chars per line

    def center(text: str) -> bytes:
        return b"\x1b\x61\x01" + text.encode() + b"\n"

    def left(text: str) -> bytes:
        return b"\x1b\x61\x00" + text.encode() + b"\n"

    def bold(text: str) -> bytes:
        return b"\x1b\x21\x08" + text.encode() + b"\x1b\x21\x00"

    def divider() -> bytes:
        return left("-" * width)

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    data  = ESC_INIT
    data += center("KETOKO POS")
    data += center("Test Print Phase 2")
    data += divider()
    data += left(f"Printer : {'RPP02 58mm' if paper == '22' else 'TM-U220 76mm'}")
    data += left(f"Platform: {PLATFORM} / {ARCH}")
    data += left(f"Waktu   : {now}")
    data += divider()
    data += center("Print berhasil!")
    data += ESC_FEED
    data += build_cut_command(cfg)
    data += build_drawer_command(cfg)
    return data


# ── Print backends ────────────────────────────────────────────────────────────

def print_usb_linux(data: bytes, device: str) -> None:
    """Write raw ESC/POS bytes directly to USB device node."""
    with open(device, "wb") as f:
        f.write(data)


def print_usb_mac(data: bytes, printer_name: str) -> None:
    """Send raw bytes via CUPS on macOS."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        subprocess.run(["lpr", "-P", printer_name, "-o", "raw", tmp_path], check=True)
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
    """Send raw ESC/POS to network printer via TCP (port 9100 / JetDirect)."""
    with socket.create_connection((ip, port), timeout=5) as s:
        s.sendall(data)


def print_bluetooth(data: bytes, cfg: dict) -> None:
    """
    Send ESC/POS bytes to Bluetooth printer.

    Windows: pairs Bluetooth printer → Windows creates virtual COM port (e.g. COM5).
             Set bt_com_port in config.json (e.g. "COM5").
    Linux  : rfcomm bind creates /dev/rfcomm0 — write directly.
    macOS  : /dev/tty.PrinterName — write directly.
    """
    if PLATFORM == "win32":
        com_port = cfg.get("bt_com_port", "")
        if not com_port:
            raise RuntimeError(
                "bt_com_port belum diisi di config.json. "
                "Pair printer Bluetooth di Windows, lalu cek COM port di Device Manager."
            )
        try:
            import serial
            with serial.Serial(com_port, baudrate=9600, timeout=3) as ser:
                ser.write(data)
            log.info(f"Print → Bluetooth Windows {com_port} ({len(data)} bytes)")
        except ImportError:
            raise RuntimeError("pyserial tidak terinstall. Run: pip install pyserial")

    elif PLATFORM.startswith("linux"):
        device = cfg.get("bt_device_linux", "/dev/rfcomm0")
        log.info(f"Print → Bluetooth Linux {device} ({len(data)} bytes)")
        # rfcomm0 harus sudah di-bind: sudo rfcomm bind 0 <MAC>
        with open(device, "wb") as f:
            f.write(data)

    elif PLATFORM == "darwin":
        device = cfg.get("bt_device_mac", "")
        if not device:
            raise RuntimeError(
                "bt_device_mac belum diisi di config.json (contoh: /dev/tty.RPP02-SerialPort)"
            )
        log.info(f"Print → Bluetooth macOS {device} ({len(data)} bytes)")
        with open(device, "wb") as f:
            f.write(data)

    else:
        raise RuntimeError(f"Bluetooth tidak didukung di platform: {PLATFORM}")


def send_to_printer(data: bytes, cfg: dict) -> None:
    tipe = cfg.get("tipe_koneksi", "1")

    # Fallback: kalau Network dipilih tapi IP kosong, pakai USB
    if tipe == "2" and not cfg.get("ip_address", "").strip():
        log.warning("[PRINT] tipe=Network tapi ip_address kosong — fallback ke USB")
        tipe = "1"

    if tipe == "1":
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

    elif tipe == "2":
        ip   = cfg["ip_address"]
        port = int(cfg.get("ip_address_port", 9100))
        log.info(f"Print → Network {ip}:{port} ({len(data)} bytes)")
        print_network(data, ip, port)

    elif tipe == "3":
        log.info(f"Print → Bluetooth ({len(data)} bytes)")
        print_bluetooth(data, cfg)

    else:
        raise RuntimeError(f"tipe_koneksi '{tipe}' tidak dikenal (1=USB, 2=Network, 3=BT)")


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
        cfg = load_config()
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
        # data harus double-encoded (JSON string) sesuai format service asli
        return Response(ok(json.dumps(data, indent=2)), mimetype=MIME)
    except Exception as e:
        log.error(f"readconf error: {e}")
        return Response(err(str(e)), mimetype=MIME)


@app.route("/print",    methods=["POST", "OPTIONS"])
@app.route("/printusb", methods=["POST", "OPTIONS"])
@app.route("/printnet", methods=["POST", "OPTIONS"])
@app.route("/printbt",  methods=["POST", "OPTIONS"])
def handle_print():
    if request.method == "OPTIONS":
        return Response(status=200)

    endpoint  = request.path
    form_data = get_form_field("data_print")

    log.info(f"[PRINT] endpoint={endpoint}")

    with open(os.path.join(BASE_DIR, "captured_print.log"), "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Time:     {datetime.now()}\n")
        f.write(f"Platform: {PLATFORM} / {ARCH}\n")
        f.write(f"Endpoint: {endpoint}\n")
        f.write(f"data_print:\n{form_data[:2000]}\n")

    if not form_data:
        return Response(ok("Logged (no data)"), mimetype=MIME)

    try:
        cfg        = load_config()
        data_bytes = b64decode(form_data)

        # Append cash drawer pulse after print data if enabled
        data_bytes += build_drawer_command(cfg)

        send_to_printer(data_bytes, cfg)
        return Response(ok("Print berhasil"), mimetype=MIME)
    except Exception as e:
        log.warning(f"Print error: {e}")
        return Response(err(str(e)), mimetype=MIME)


@app.route("/testprint", methods=["POST", "GET", "OPTIONS"])
def testprint():
    """Kirim test receipt ke printer — berguna untuk verifikasi koneksi."""
    if request.method == "OPTIONS":
        return Response(status=200)
    try:
        cfg  = load_config()
        data = build_test_receipt(cfg)
        send_to_printer(data, cfg)
        log.info("testprint → OK")
        return Response(ok("Test print berhasil"), mimetype=MIME)
    except Exception as e:
        log.error(f"testprint error: {e}")
        return Response(err(str(e)), mimetype=MIME)


@app.route("/cashdrawer", methods=["POST", "GET", "OPTIONS"])
def cashdrawer():
    """Buka cash drawer secara manual (tanpa print)."""
    if request.method == "OPTIONS":
        return Response(status=200)
    try:
        cfg = load_config()
        # Force kirim pulse meski config cashdrawer=0
        send_to_printer(ESC_INIT + ESC_DRAWER_PIN2, cfg)
        log.info("cashdrawer → pulse sent")
        return Response(ok("Cash drawer terbuka"), mimetype=MIME)
    except Exception as e:
        log.error(f"cashdrawer error: {e}")
        return Response(err(str(e)), mimetype=MIME)


@app.route("/cut", methods=["POST", "GET", "OPTIONS"])
def cut():
    """Trigger auto cutter secara manual."""
    if request.method == "OPTIONS":
        return Response(status=200)
    try:
        cfg = load_config()
        send_to_printer(ESC_FEED + ESC_CUT_PARTIAL, cfg)
        log.info("cut → OK")
        return Response(ok("Cut berhasil"), mimetype=MIME)
    except Exception as e:
        log.error(f"cut error: {e}")
        return Response(err(str(e)), mimetype=MIME)


@app.route("/status", methods=["GET", "OPTIONS"])
def status():
    """Health check — kembalikan status service dan config aktif."""
    if request.method == "OPTIONS":
        return Response(status=200)
    try:
        cfg = load_config()
        tipe_map = {"1": "USB", "2": "Network", "3": "Bluetooth"}
        info = {
            "status":    "running",
            "platform":  f"{PLATFORM}/{ARCH}",
            "koneksi":   tipe_map.get(cfg["tipe_koneksi"], "unknown"),
            "kertas":    f"{'58mm' if cfg['ukuran_kertas'] == '22' else '76mm'}",
            "autocutter": cfg.get("autocutter") == "1",
            "cashdrawer": cfg.get("cashdrawer") == "1",
        }
        return Response(ok(info), mimetype=MIME)
    except Exception as e:
        return Response(err(str(e)), mimetype=MIME)


@app.route("/prtraw", methods=["POST", "OPTIONS"])
def prtraw():
    """
    Endpoint print utama Ketoko Web 2.0.
    Payload: data_print = base64(JSON)
    JSON format: {"dataprint": [{"row": "<ESC/POS string>"}, ...]}
    Tiap row berisi string dengan unicode escapes untuk kontrol ESC/POS (u001b = ESC, dll).
    """
    if request.method == "OPTIONS":
        return Response(status=200)

    content_type = request.content_type or ""
    raw_body     = request.get_data(as_text=True)
    form_data    = get_form_field("data_print")
    log.info(f"[PRTRAW] ct={content_type!r} | form_data_len={len(form_data)} | raw_len={len(raw_body)}")

    with open(os.path.join(BASE_DIR, "captured_print.log"), "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Time:        {datetime.now()}\n")
        f.write(f"Endpoint:    /prtraw\n")
        f.write(f"ContentType: {content_type}\n")
        f.write(f"RawBody:\n{raw_body[:3000]}\n")
        f.write(f"data_print:\n{form_data[:500]}\n")

    if not form_data:
        log.warning("[PRTRAW] data_print kosong — Ketoko Web tidak kirim data?")
        return Response(ok(""), mimetype=MIME)

    try:
        payload    = json.loads(b64decode(form_data).decode("utf-8"))
        rows       = payload.get("dataprint", [])
        cfg        = load_config()

        # Gabungkan semua row menjadi satu stream bytes
        # Setiap row adalah string ESC/POS — encode latin-1 agar byte value = unicode code point
        data_bytes = b""
        for item in rows:
            row = item.get("row", "")
            data_bytes += row.encode("latin-1", errors="replace")

        data_bytes += build_drawer_command(cfg)

        log.info(f"[PRTRAW] {len(rows)} rows, {len(data_bytes)} bytes -> printer")
        send_to_printer(data_bytes, cfg)
        return Response(ok("Print berhasil"), mimetype=MIME)

    except Exception as e:
        log.error(f"[PRTRAW] error: {e}")
        return Response(err(str(e)), mimetype=MIME)


# Config key mapping dari Ketoko ke config.json internal
_CFG_MAP = {
    "PRT_TIPE_KONEKSI":      "tipe_koneksi",
    "PRT_USB_DEVICE":        "usb_device_windows",
    "PRT_IP_ADDRESS":        "ip_address",
    "PRT_IP_ADDRESS_PORT":   "ip_address_port",
    "PRT_BT_PRINTER_ADDRESS":"bt_address",
    "PRT_BT_PRINTER_NAME":   "bt_name",
    "PRT_UKURAN_KERTAS":     "ukuran_kertas",
    "PRT_JML_PRINT_NOTA":    "jml_print_nota",
    "PRT_JML_BARIS_KOSONG":  "jml_baris_kosong",
    "PRT_AUTOCUTTER":        "autocutter",
    "PRT_CASHDRAWER":        "cashdrawer",
    "PRT_LOGO_AKTIF":        "logo_aktif",
    "PRT_ALIGN_HEADER":      "align_header",
    "PRT_ALIGN_FOOTER":      "align_footer",
    "PRT_OPSI_BARIS":        "opsi_baris",
    "PRT_OPSI_PELSES":       "opsi_pelses",
    "PRT_KETERANGAN":        "keterangan",
}


@app.route("/saveconf", methods=["POST", "OPTIONS"])
def saveconf():
    """
    Simpan konfigurasi dari Ketoko Web 2.0 ke config.json.
    Payload: data_print = base64(JSON)
    JSON format: {"datacfg": [{"KEY": "value", ...}]} atau {"datacfg": [{key: val}, ...]}
    """
    if request.method == "OPTIONS":
        return Response(status=200)

    form_data = get_form_field("data_print")
    log.info("[SAVECONF] request diterima")

    if not form_data:
        return Response(ok(""), mimetype=MIME)

    try:
        payload = json.loads(b64decode(form_data).decode("utf-8"))
        datacfg = payload.get("datacfg", [])

        # datacfg bisa berupa list of dict {KEY: val} atau list of {confname, confvalue}
        with open(CONFIG_FILE) as f:
            full_cfg = json.load(f)
        cfg = full_cfg["printer"]

        for item in datacfg:
            if isinstance(item, dict):
                # Format: {"PRT_TIPE_KONEKSI": "1", ...} (semua dalam 1 dict)
                for k, v in item.items():
                    internal_key = _CFG_MAP.get(k)
                    if internal_key:
                        # Jangan timpa string koneksi dengan nilai kosong dari web
                        if internal_key in ("usb_device_windows", "ip_address", "bt_address") and not str(v).strip():
                            continue
                        cfg[internal_key] = str(v)

        full_cfg["printer"] = cfg
        with open(CONFIG_FILE, "w") as f:
            json.dump(full_cfg, f, indent=2, ensure_ascii=False)

        log.info(f"[SAVECONF] config disimpan: tipe={cfg.get('tipe_koneksi')} kertas={cfg.get('ukuran_kertas')}")
        return Response(ok("Config disimpan"), mimetype=MIME)

    except Exception as e:
        log.error(f"[SAVECONF] error: {e}")
        return Response(err(str(e)), mimetype=MIME)


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/<path:path>",             methods=["GET", "POST", "OPTIONS"])
def catch_all(path):
    raw = request.get_data(as_text=True)
    log.info(f"[UNKNOWN] /{path} | body={raw[:300]}")
    return Response(ok(""), mimetype=MIME)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info(f"Ketoko Print Service — platform={PLATFORM} arch={ARCH}")
    log.info(f"Listening on http://127.0.0.1:5488")
    log.info(f"Endpoints: /readconf /prtraw /saveconf /print /testprint /cashdrawer /cut /status")
    app.run(host="127.0.0.1", port=5488, debug=False)
