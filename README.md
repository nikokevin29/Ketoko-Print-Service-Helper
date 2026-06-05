# Ketoko POS Print Service

Pengganti **KetokoPrnSvc.exe** (Windows Only) untuk **Ketoko Web 2.0** di semua platform.
Berjalan sebagai HTTP service di `localhost:5488`, kompatibel langsung dengan `pos.ketoko.co.id`.

> Proyek ini lahir dari hasil reverse engineering installer Windows milik Ketoko,
> karena tidak ada dokumentasi publik mengenai protokol komunikasi antara
> `pos.ketoko.co.id` dengan print service lokal.

**Platform yang didukung:**

| Platform | Status |
|---|---|
| Linux (semua distro) | ✅ Siap |
| macOS Intel (x86_64) | ✅ Siap |
| macOS Apple Silicon (M series) | ✅ Siap |
| Windows 10/11 | ✅ Siap |

---

## Progress Pengembangan

```
Phase 1 — Core Service & Cross-platform  [████████████████████] 100%
Phase 2 — USB Print (TM-U220 & RPP02)    [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 3 — Bluetooth Print (RPP02)        [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 4 — Network Print                  [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 5 — Cash Drawer & Auto Cutter      [░░░░░░░░░░░░░░░░░░░░]   0%
```

---

## Detail Per Phase

### Phase 1 — Core Service & Cross-platform ✅

**Apa yang sudah dikerjakan:**

Dilakukan reverse engineering terhadap `KetokoPrnSvc.exe` menggunakan `innoextract`
(Inno Setup) dan `monodis` (Mono IL disassembler). Binary menggunakan .NET Framework 4.7.1
dengan obfuskasi string, sehingga analisis dilanjutkan via source JavaScript di
`pos.ketoko.co.id`.

Hasil yang ditemukan:
- Service berjalan di port **5488** via **HTTP POST** (bukan WebSocket)
- Satu-satunya endpoint yang terkonfirmasi: `POST /readconf` — web app membaca konfigurasi printer dari sini
- Format response: `{ "number": 0, "data": [{confname, confvalue}, ...] }`
- Endpoint print belum terkonfirmasi — akan ditemukan via **discovery logger** saat printer real dicolok

**Yang sudah diimplementasikan:**
- [x] Endpoint `/readconf` dengan format response kompatibel Ketoko Web 2.0
- [x] Discovery logger — semua request yang masuk dicatat ke `captured_print.log`
- [x] Deteksi platform otomatis (Linux / macOS / Windows / ARM)
- [x] Backend print per platform: Linux USB node, macOS CUPS, Windows win32print, Network TCP
- [x] Auto-start: systemd user service (Linux), LaunchAgent (macOS), Task Scheduler (Windows)
- [x] Installer: `install.sh` (Linux/macOS), `install.bat` (Windows)

---

### Phase 2 — USB Print: TM-U220 & RPP02 🔜

**Apa yang perlu dilakukan:**

Printer belum tersedia saat Phase 1 dikerjakan. Begitu printer dicolok via USB:

1. **Temukan device path** — jalankan setelah colok USB:
   ```bash
   # Linux
   ls /dev/usb/lp* atau dmesg | tail -20

   # macOS
   ls /dev/usb/* atau system_profiler SPUSBDataType
   ```

2. **Temukan endpoint print** — jalankan service, buka `pos.ketoko.co.id`,
   lalu coba cetak. Semua request masuk akan tercatat di `captured_print.log`:
   ```bash
   tail -f captured_print.log
   ```
   Yang perlu dicatat dari log:
   - Nama endpoint (misal `/print`, `/printusb`, dsb.)
   - Format field `data_print` (base64? raw ESC/POS? JSON?)

3. **Implementasikan endpoint print** berdasarkan temuan log di atas.

4. **Test per printer:**
   - Epson TM-U220 76mm — dot matrix, USB
   - RPP02 58mm — thermal, USB

**Apa yang perlu diupdate di `config.json`:**
```json
"usb_device_linux":   "/dev/usb/lp0",  ← sesuaikan dari dmesg
"usb_device_mac":     "TM-U220",        ← dari: lpstat -p
"usb_device_windows": "TM-U220",        ← dari: Get-Printer
"ukuran_kertas":      "32"              ← 32=76mm, 22=58mm
```

---

### Phase 3 — Bluetooth Print: RPP02 🔜

**Apa yang perlu dilakukan:**

RPP02 mendukung Bluetooth di samping USB. Untuk mengaktifkannya:

1. **Pairing** RPP02 terlebih dahulu:
   ```bash
   # Linux
   bluetoothctl
   > scan on
   > pair <MAC_ADDRESS>
   > trust <MAC_ADDRESS>
   ```

2. **Temukan MAC address** RPP02 dari scan Bluetooth.

3. **Implementasikan koneksi RFCOMM** — Bluetooth serial profile untuk printer thermal
   menggunakan Python library `PyBluez` atau socket RFCOMM langsung.

4. **Update config.json:**
   ```json
   "tipe_koneksi": "3",
   "bt_address":   "XX:XX:XX:XX:XX:XX",
   "bt_name":      "RPP02"
   ```

---

### Phase 4 — Network Print 🔜

**Apa yang perlu dilakukan:**

Untuk printer yang terhubung via LAN/WiFi (port 9100 / JetDirect protocol):

1. Backend TCP socket sudah diimplementasikan di `service.py`.
2. Yang dibutuhkan hanya **testing** dengan printer network nyata.
3. Update config:
   ```json
   "tipe_koneksi":    "2",
   "ip_address":      "192.168.1.x",
   "ip_address_port": "9100"
   ```

---

### Phase 5 — Cash Drawer & Auto Cutter 🔜

**Apa yang perlu dilakukan:**

Cash drawer dan auto cutter dikendalikan via perintah ESC/POS yang disisipkan
sebelum/sesudah data struk:

- **Cash drawer:** ESC/POS command `\x1b\x70\x00\x19\xfa` (pulse pin 2)
- **Auto cutter:** ESC/POS command `\x1d\x56\x42\x00` (partial cut)

Perlu diverifikasi apakah web app sudah menyertakan command ini di `data_print`,
atau service ini yang harus menambahkannya berdasarkan config `autocutter` dan `cashdrawer`.

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

Edit `config.json`:

```json
{
  "printer": {
    "tipe_koneksi":      "1",
    "usb_device_linux":  "/dev/usb/lp0",
    "usb_device_mac":    "TM-U220",
    "usb_device_windows":"TM-U220",
    "ip_address":        "",
    "ip_address_port":   "9100",
    "bt_address":        "",
    "bt_name":           "",
    "ukuran_kertas":     "32"
  }
}
```

| `tipe_koneksi` | Mode |
|---|---|
| `1` | USB |
| `2` | Network / IP |
| `3` | Bluetooth (Phase 3) |

| `ukuran_kertas` | Printer |
|---|---|
| `32` | 75–80mm (TM-U220) |
| `22` | 58mm (RPP02) |

---

## Cara Kerja

```
pos.ketoko.co.id (browser)
        │
        │ POST /readconf → baca config printer
        │ POST /print    → kirim data ESC/POS
        ▼
localhost:5488  ← service ini
        │
        ├── Linux   → /dev/usb/lp0      (direct write)
        ├── macOS   → lpr -P <name> -o raw  (CUPS)
        ├── Windows → win32print RAW mode
        └── Network → TCP socket IP:9100
```

---

## Cek Status Service

**Linux:**
```bash
systemctl --user status ketoko-print.service
journalctl --user -u ketoko-print.service -f
```

**macOS:**
```bash
launchctl list | grep ketoko
tail -f ~/.local/share/ketoko-print-svc/requests.log
```

**Windows:**
```powershell
Get-ScheduledTask -TaskName KetokoPrintService
```

---

## Printer yang Didukung

| Printer | Tipe | Koneksi | Phase |
|---|---|---|---|
| Epson TM-U220 | Dot Matrix 76mm | USB | 2 |
| RPP02 | Thermal 58mm | USB | 2 |
| RPP02 | Thermal 58mm | Bluetooth | 3 |
| Generic ESC/POS | — | Network (LAN/WiFi) | 4 |
