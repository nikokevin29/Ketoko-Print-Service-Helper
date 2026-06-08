# Ketoko POS Print Service

Cross-platform replacement for the Windows-only `KetokoPrnSvc.exe` — enables **Ketoko Web 2.0** (`pos.ketoko.co.id`) to print receipts on Linux, macOS, and Windows without the original binary.

Runs as an HTTP service on `localhost:5488`, reverse-engineered from the original installer since no public protocol documentation exists.

---

## Development Status

| Phase | Fitur | Status |
|-------|-------|--------|
| 1 | Core service, `/readconf`, discovery logging, cross-platform | ✅ Selesai |
| 2 | USB printing — RPP02 58mm (Windows ✅, Linux ✅, macOS ✅) | ✅ Selesai |
| 3 | Network printing via TCP/IP (port 9100) | ✅ Selesai |
| 4 | Bluetooth printing | ✅ Selesai (⚠️ *not tested* — unit RPP02 tanpa modul Bluetooth) |
| 5 | Peripheral control — cash drawer, auto cutter, `/testprint`, `/cashdrawer`, `/cut` | ✅ Selesai (⚠️ *not tested* — unit RPP02 tanpa port RJ11) |

---

## Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/readconf` | POST | Kembalikan konfigurasi printer ke Ketoko Web 2.0 |
| `/print` `/printusb` `/printnet` `/printbt` | POST | Terima `data_print` (base64 ESC/POS), kirim ke printer |
| `/testprint` | GET/POST | Cetak test receipt — verifikasi koneksi printer |
| `/cashdrawer` | GET/POST | Pulse buka cash drawer (`ESC p`) |
| `/cut` | GET/POST | Trigger auto cutter (`GS V`) |
| `/status` | GET | Health check + info konfigurasi aktif |

---

## Konfigurasi (`config.json`)

```json
{
  "printer": {
    "tipe_koneksi":       "1",
    "usb_device_linux":   "/dev/usb/lp0",
    "usb_device_mac":     "",
    "usb_device_windows": "Ecoprint MP58",
    "bt_com_port":        "",
    "bt_device_linux":    "/dev/rfcomm0",
    "bt_device_mac":      "",
    "bt_address":         "",
    "bt_name":            "",
    "ip_address":         "",
    "ip_address_port":    "9100",
    "ukuran_kertas":      "22",
    "jml_print_nota":     "1",
    "jml_baris_kosong":   "2",
    "autocutter":         "0",
    "cashdrawer":         "0",
    "logo_aktif":         "0",
    "align_header":       "2",
    "align_footer":       "1",
    "opsi_baris":         "1",
    "opsi_pelses":        "1",
    "keterangan":         "Terima Kasih telah berbelanja di toko kami."
  }
}
```

### `tipe_koneksi`
| Nilai | Mode |
|-------|------|
| `1` | USB |
| `2` | Network/IP |
| `3` | Bluetooth |

### `ukuran_kertas`
| Nilai | Ukuran |
|-------|--------|
| `22` | 58mm (RPP02, thermal) |
| `32` | 76mm (Epson TM-U220, dot matrix) |

### Bluetooth (`tipe_koneksi: "3"`)
- **Windows**: Pair printer via Bluetooth Settings → Windows buat virtual COM port → isi `bt_com_port` (contoh: `"COM5"`)
- **Linux**: `sudo rfcomm bind 0 <MAC>` → isi `bt_device_linux` (default: `/dev/rfcomm0`)
- **macOS**: isi `bt_device_mac` (contoh: `/dev/tty.RPP02-SerialPort`)

> ⚠️ **Not tested** — Bluetooth belum diuji. Unit RPP02 yang tersedia tidak memiliki modul Bluetooth.

### Cash Drawer & Auto Cutter
- `autocutter: "1"` — kirim `GS V` (partial cut) setelah setiap print
- `cashdrawer: "1"` — kirim `ESC p` (pulse pin 2) setelah setiap print
- Bisa juga trigger manual via endpoint `/cashdrawer` dan `/cut`

> ⚠️ **Not tested** — Unit RPP02 yang tersedia tidak memiliki port RJ11 untuk cash drawer dan auto cutter.

---

## Printer yang Didukung

| Printer | Kertas | Koneksi | Status |
|---------|--------|---------|--------|
| RPP02 | 58mm thermal | USB ✅ / BT ⚠️ | USB tested ✅ |
| Epson TM-U220 | 76mm dot matrix | USB / Network | Belum diuji |
| Generic ESC/POS | 58mm / 80mm | USB / Network / BT | Kompatibel |

---

## Instalasi

### Prasyarat
- Python 3.8+

### Install dependencies

```bash
# Windows
pip install flask pywin32 pyserial

# Linux / macOS
pip install flask pyserial
```

### Jalankan service

```bash
# Windows
py service.py

# Linux / macOS
python3 service.py
```

Service berjalan di `http://127.0.0.1:5488`.

### Install sebagai system service

**Windows** — jalankan `install.bat` sebagai Administrator.

**Linux (systemd)**:
```bash
chmod +x install.sh
sudo ./install.sh
sudo systemctl enable --now ketoko-print
```

**macOS (launchd)**:
```bash
chmod +x install.sh
./install.sh
```

---

## Cara Kerja

Ketoko Web 2.0 (`pos.ketoko.co.id`) berkomunikasi dengan service ini via HTTP ke `localhost:5488`:

1. **`/readconf`** — web app baca konfigurasi printer saat pertama buka POS
2. **`/print`** — web app kirim data receipt sebagai `data_print` (base64-encoded ESC/POS bytes)
3. Service decode base64 → kirim raw bytes ke printer sesuai `tipe_koneksi`

Semua request dicatat di `requests.log` dan `captured_print.log` untuk debugging.

---

## Struktur Project

```
ketoko-print-linux/
├── service.py                  # Main service
├── config.json                 # Konfigurasi printer
├── requirements.txt            # Python dependencies
├── install.sh                  # Installer Linux/macOS
├── install.bat                 # Installer Windows
├── ketoko-print.service        # systemd unit file
└── id.ketoko.print.plist       # launchd plist (macOS)
```

---

## Lisensi

MIT
