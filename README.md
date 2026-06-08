# Ketoko Print Service Helper — Cross-Platform

> Pengganti lintas platform untuk `KetokoPrnSvc.exe` yang hanya tersedia di Windows.
> Memungkinkan **Ketoko Web 2.0** (`pos.ketoko.co.id`) mencetak nota di Linux, macOS, dan Windows tanpa binary asli.

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-yellow)
![License](https://img.shields.io/badge/license-MIT-green)
![Port](https://img.shields.io/badge/port-5488-orange)

---

## Cara Kerja

```
Ketoko Web 2.0  ──HTTP──►  localhost:5488  ──ESC/POS──►  Printer
(pos.ketoko.co.id)          service.py                  (USB / Network / BT)
```

Service berjalan di `localhost:5488` dan meniru protokol `KetokoPrnSvc.exe` yang di-*reverse-engineer* dari installer aslinya.

---

## Download & Install

### Windows (Recommended)

| File | Keterangan |
|------|------------|
| `KetokoPrintService_Setup_*_windows.exe` | Installer lengkap — double click, ikuti wizard |

**Langkah install:**
1. Download installer dari [Releases](../../releases/latest)
2. Jalankan sebagai **Administrator**
3. Centang *"Jalankan otomatis saat Windows login"*
4. Service langsung aktif di port 5488

> Shortcut **Pengaturan Printer** tersedia di Start Menu untuk memilih printer USB dan cek status.

---

### Linux x64

```bash
tar -xzf KetokoPrintService-*-linux-x64.tar.gz
cd KetokoPrintService-*/
chmod +x install.sh
sudo ./install.sh
sudo systemctl enable --now ketoko-print
```

---

### macOS

> ⚠️ **Not tested** — binary tersedia di Releases, belum diuji di hardware nyata. Silakan laporkan hasil uji via Issues.

```bash
unzip KetokoPrintService-*-macos-x64.zip
cd KetokoPrintService-*/
chmod +x install.sh KetokoPrintService
./install.sh
```

---

## Fitur

| Fitur | Windows | Linux | macOS |
|-------|:-------:|:-----:|:-----:|
| Core service HTTP (port 5488) | ✅ | ✅ | ✅ |
| USB printing (ESC/POS) | ✅ | ✅ | ✅ |
| Network printing (TCP/IP) | ✅ | ✅ | ✅ |
| Bluetooth printing | ✅ | ⚠️ *not tested* | ⚠️ *not tested* |
| Auto cutter / Cash drawer | ✅ | ⚠️ *not tested* | ⚠️ *not tested* |
| Config GUI (tkinter) | ✅ | ⚠️ *not tested* | ⚠️ *not tested* |
| System tray (pystray) | ✅ | ⚠️ *not tested* | ⚠️ *not tested* |
| Windows installer (Inno Setup) | ✅ | — | — |

---

## Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/readconf` | POST | Baca konfigurasi printer |
| `/prtraw` | POST | Print nota (ESC/POS base64 JSON) |
| `/print` `/printusb` `/printnet` `/printbt` | POST | Print via jalur spesifik |
| `/saveconf` | POST | Simpan konfigurasi dari web |
| `/testprint` | GET/POST | Cetak test receipt |
| `/cashdrawer` | GET/POST | Buka cash drawer |
| `/cut` | GET/POST | Trigger auto cutter |
| `/status` | GET | Health check + info config aktif |

---

## Konfigurasi (`config.json`)

```json
{
  "printer": {
    "tipe_koneksi":       "1",
    "usb_device_windows": "Ecoprint MP58",
    "usb_device_linux":   "/dev/usb/lp0",
    "usb_device_mac":     "",
    "ip_address":         "",
    "ip_address_port":    "9100",
    "bt_com_port":        "",
    "bt_device_linux":    "/dev/rfcomm0",
    "ukuran_kertas":      "32",
    "autocutter":         "1",
    "cashdrawer":         "1",
    "keterangan":         "Terima Kasih telah berbelanja di toko kami."
  }
}
```

| Key | Nilai | Keterangan |
|-----|-------|------------|
| `tipe_koneksi` | `1` = USB, `2` = Network, `3` = Bluetooth | Mode koneksi printer |
| `ukuran_kertas` | `22` = 58mm, `32` = 76mm | Lebar kertas |

> Konfigurasi utama (ukuran kertas, keterangan, dll.) diatur langsung dari **Ketoko Web** — tidak perlu ubah manual.

---

## Build dari Source

### Prasyarat

```bash
pip install flask pyserial                         # semua platform
pip install pywin32 pystray pillow                 # Windows only
pip install pyinstaller                            # untuk build exe
```

### Windows (build installer)

```bat
build.bat          # PyInstaller → dist\*.exe
iscc installer.iss # Inno Setup → dist\KetokoPrintService_Setup_*.exe
```

### Semua Platform (jalankan langsung)

```bash
python service.py          # headless service
python tray.py             # Windows: service + system tray
python gui.py              # config GUI
```

### CI/CD

Build otomatis via GitHub Actions. Buat release baru:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Workflow akan build Windows installer + Linux tar.gz + macOS zip lalu buat GitHub Release.

---

## Struktur Project

```
ketoko-print-linux/
├── service.py                  # Core HTTP service (port 5488)
├── gui.py                      # Config GUI — tkinter, cross-platform
├── tray.py                     # Windows system tray launcher
├── config.json                 # Konfigurasi printer
├── requirements.txt            # Python dependencies
├── KetokoPrintService.spec     # PyInstaller spec (tray + service)
├── KetokoPrintConfig.spec      # PyInstaller spec (config GUI)
├── build.bat                   # Build script Windows
├── installer.iss               # Inno Setup script
├── install.sh                  # Installer Linux/macOS
├── ketoko-print.service        # systemd unit file
├── id.ketoko.print.plist       # launchd plist (macOS)
└── .github/workflows/
    └── build.yml               # CI/CD GitHub Actions
```

---

## Printer yang Didukung

| Printer | Kertas | Koneksi | Status |
|---------|--------|---------|--------|
| Ecoprint MP58 / RPP02 | 58mm thermal | USB | ✅ Tested |
| Epson TM-U220 | 76mm dot matrix | USB / Network | Belum diuji |
| Generic ESC/POS | 58mm / 80mm | USB / Network / BT | Kompatibel |

---

## Troubleshooting

**"Koneksi gagal" di Ketoko Web**
→ Pastikan `service.py` atau `tray.py` sedang berjalan. Cek `http://127.0.0.1:5488/status`.

**Port 5488 sudah dipakai (Error 503)**
→ Service asli `KetokoPrnSvc.exe` mendaftarkan port ke http.sys. Hapus dengan:
```bat
netsh http delete urlacl url="http://127.0.0.1:5488/"
netsh http delete urlacl url="http://+:5488/"
```
Jalankan sebagai Administrator.

**Printer tidak muncul di dropdown GUI**
→ Pastikan printer sudah terpasang di Windows (Printers & Scanners). Klik **Refresh**.

---

## Lisensi

MIT — by [xbnn29](https://github.com/nikokevin29)
