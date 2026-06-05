# Ketoko POS Print Service

Pengganti **KetokoPrnSvc.exe** (Windows Only) untuk **Ketoko Web 2.0** di semua platform.
Berjalan sebagai HTTP service di `localhost:5488`, kompatibel langsung dengan `pos.ketoko.co.id`.

**Platform yang didukung:**
- Linux (semua distro)
- macOS Intel (x86_64)
- macOS Apple Silicon (arm64 / M series)
- Windows 10/11

---

## Progress Pengembangan

```
Phase 1 — Core Service & Cross-platform  [████████████████████] 100%
Phase 2 — USB Print (TM-U220 & RPP02)    [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 3 — Bluetooth Print (RPP02)        [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 4 — Network Print                  [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 5 — Cash Drawer & Auto Cutter      [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Phase 1 — Core Service & Cross-platform ✅
- [x] Reverse engineering `KetokoPrnSvc.exe` (Inno Setup + .NET 4.7.1, obfuscated)
- [x] Identifikasi port `5488`, protocol HTTP POST, endpoint `/readconf`
- [x] Implementasi `/readconf` — format response kompatibel Ketoko Web 2.0
- [x] Discovery logger — tangkap endpoint print yang belum diketahui
- [x] Deteksi platform otomatis (Linux / macOS / Windows)
- [x] Backend print: Linux USB device node, macOS CUPS, Windows win32print, Network TCP
- [x] Auto-start: systemd user service (Linux), LaunchAgent (macOS), Task Scheduler (Windows)
- [x] Installer: `install.sh` (Linux/macOS), `install.bat` (Windows)

### Phase 2 — USB Print: TM-U220 & RPP02 🔜
> Membutuhkan real device untuk testing

- [ ] Identifikasi USB device path per platform
- [ ] Identifikasi endpoint & format `data_print` dari web app (via discovery log)
- [ ] Decode & forward ESC/POS ke printer
- [ ] Test cetak struk — Epson TM-U220 76mm (USB)
- [ ] Test cetak struk — RPP02 58mm (USB)

### Phase 3 — Bluetooth Print: RPP02 🔜
- [ ] Pairing RPP02 via BlueZ (Linux) / CoreBluetooth (macOS) / WinBluetooth
- [ ] Implementasi koneksi RFCOMM
- [ ] Routing print job ke BT

### Phase 4 — Network Print 🔜
- [ ] Test proxy TCP ke printer IP:9100
- [ ] Validasi lintas platform

### Phase 5 — Cash Drawer & Auto Cutter 🔜
- [ ] ESC/POS command trigger cash drawer
- [ ] Auto cutter command

---

## Instalasi

### Prasyarat
- Python 3.8+
- pip

### Linux & macOS
```bash
git clone https://github.com/nikokevin29/ketoko-print-linux.git
cd ketoko-print-linux
chmod +x install.sh
./install.sh
```

### Windows
```bat
git clone https://github.com/nikokevin29/ketoko-print-linux.git
cd ketoko-print-linux
install.bat
```

### Manual (semua platform)
```bash
pip install -r requirements.txt
python service.py
```

---

## Konfigurasi

Edit `config.json` sesuai printer dan platform Anda:

```json
{
  "printer": {
    "tipe_koneksi":      "1",
    "usb_device_linux":  "/dev/usb/lp0",
    "usb_device_mac":    "TM-U220",
    "usb_device_windows":"TM-U220",
    "ip_address":        "",
    "ip_address_port":   "9100",
    "ukuran_kertas":     "32"
  }
}
```

| `tipe_koneksi` | Keterangan |
|---|---|
| `1` | USB |
| `2` | Network / IP |
| `3` | Bluetooth (Phase 3) |

| `ukuran_kertas` | Printer |
|---|---|
| `32` | 75–80mm (TM-U220) |
| `22` | 58mm (RPP02) |

**Cara temukan nama printer di macOS:**
```bash
lpstat -p -d
```

**Cara temukan nama printer di Windows:**
```powershell
Get-Printer | Select-Object Name
```

---

## Printer yang Didukung

| Printer | Tipe | Koneksi | Status |
|---|---|---|---|
| Epson TM-U220 | Dot Matrix 76mm | USB | 🔜 Phase 2 |
| RPP02 | Thermal 58mm | USB | 🔜 Phase 2 |
| RPP02 | Thermal 58mm | Bluetooth | 🔜 Phase 3 |
| Generic ESC/POS | — | Network | 🔜 Phase 4 |

---

## Cara Kerja

```
pos.ketoko.co.id (browser)
        │
        │ POST /readconf → dapat config printer
        │ POST /print    → kirim data ESC/POS
        ▼
localhost:5488 (service ini)
        │
        ├── Linux  → /dev/usb/lp0 (direct write)
        ├── macOS  → CUPS lpr -P <name> -o raw
        ├── Windows→ win32print (raw mode)
        └── Network→ TCP socket IP:9100
```

---

## Cek Status

**Linux:**
```bash
systemctl --user status ketoko-print.service
```

**macOS:**
```bash
launchctl list | grep ketoko
```

**Windows:**
```powershell
Get-ScheduledTask -TaskName KetokoPrintService
```

---

## Discovery Log

Saat printer belum terhubung, semua request print dicatat untuk analisis format data:

```bash
tail -f captured_print.log
```
