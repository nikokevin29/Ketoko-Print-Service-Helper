# Ketoko POS Print Service — Linux

Pengganti **KetokoPrnSvc.exe** (Windows Only) untuk Ketoko Web 2.0 di Linux.
Berjalan sebagai HTTP service di `localhost:5488`, kompatibel langsung dengan `pos.ketoko.co.id`.

---

## Progress Pengembangan

```
Phase 1 — Discovery & Core Service       [████████████████████] 100%
Phase 2 — USB Print (Real Device)        [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 3 — Bluetooth Print (RPP02)        [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 4 — Network Print                  [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 5 — Cash Drawer & Auto Cutter      [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Phase 1 — Discovery & Core Service ✅
- [x] Reverse engineering `KetokoPrnSvc.exe` (Inno Setup + .NET 4.7.1, obfuscated)
- [x] Identifikasi port: `5488`, protocol: HTTP POST
- [x] Implementasi endpoint `/readconf`
- [x] Response format kompatibel dengan Ketoko Web 2.0
- [x] Discovery logger — tangkap endpoint print yang belum diketahui
- [x] Systemd user service (auto-start saat login)
- [x] Config via `config.json`

### Phase 2 — USB Print: TM-U220 & RPP02 🔜
> Membutuhkan real device untuk testing

- [ ] Identifikasi USB device path (`/dev/usb/lp0`)
- [ ] Implementasi endpoint print (ditemukan via discovery log)
- [ ] Decode format `data_print` dari web app
- [ ] Forward ESC/POS ke USB device
- [ ] Test cetak struk — Epson TM-U220 76mm
- [ ] Test cetak struk — RPP02 58mm

### Phase 3 — Bluetooth Print: RPP02 🔜
- [ ] Pairing RPP02 via BlueZ
- [ ] Implementasi koneksi BT RFCOMM
- [ ] Routing print job ke BT

### Phase 4 — Network Print 🔜
- [ ] Proxy TCP ke printer IP:9100
- [ ] Test dengan printer network

### Phase 5 — Cash Drawer & Auto Cutter 🔜
- [ ] Implementasi trigger cash drawer via ESC/POS
- [ ] Auto cutter command

---

## Instalasi

### Dependensi
```bash
sudo pacman -S python-flask
```

### Setup Service
```bash
# Clone repo
git clone https://github.com/nikokevin29/ketoko-print-linux.git
cd ketoko-print-linux

# Install systemd user service
mkdir -p ~/.config/systemd/user
cp ketoko-print.service ~/.config/systemd/user/

# Enable & start
systemctl --user daemon-reload
systemctl --user enable --now ketoko-print.service
```

### Cek Status
```bash
systemctl --user status ketoko-print.service
```

---

## Konfigurasi

Edit `config.json` sesuai printer Anda:

```json
{
  "printer": {
    "tipe_koneksi": "1",        // 1=USB, 2=Network, 3=Bluetooth
    "usb_device": "/dev/usb/lp0",
    "ip_address": "",
    "ip_address_port": "9100",
    "ukuran_kertas": "32"       // 32=75mm, 22=58mm
  }
}
```

---

## Printer yang Didukung

| Printer | Tipe | Koneksi | Status |
|---|---|---|---|
| Epson TM-U220 | Dot Matrix 76mm | USB | 🔜 Phase 2 |
| RPP02 | Thermal 58mm | USB / BT | 🔜 Phase 2 & 3 |

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
        ├── USB  → /dev/usb/lp0
        ├── BT   → RFCOMM socket
        └── NET  → TCP IP:9100
```

---

## Discovery Log

Saat printer belum terhubung, semua request print dicatat di `captured_print.log` untuk analisis format data dari web app.

```bash
tail -f ~/.local/share/ketoko-print-svc/captured_print.log
```
