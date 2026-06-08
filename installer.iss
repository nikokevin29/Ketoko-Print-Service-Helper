; Ketoko POS Print Service — Inno Setup Script
; Requires: build.bat sudah dijalankan (dist\ berisi kedua .exe)

#define AppName      "Ketoko POS Print Service"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "xbnn29"
#define AppURL       "https://github.com/nikokevin29/ketoko-print-linux"
#define ServiceExe   "KetokoPrintService.exe"
#define ConfigExe    "KetokoPrintConfig.exe"

[Setup]
AppId={{B3A1C2D4-5E6F-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\KetokoPrintService
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=KetokoPrintService_Setup_{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#ServiceExe}
CloseApplications=yes

[Languages]
Name: "indonesian"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "Jalankan otomatis saat Windows login"; GroupDescription: "Opsi tambahan:"

[Files]
; Executables
Source: "dist\{#ServiceExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#ConfigExe}";  DestDir: "{app}"; Flags: ignoreversion
; Config — hanya install jika belum ada (jaga konfigurasi user)
Source: "config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\Ketoko POS Print Service";     Filename: "{app}\{#ServiceExe}"
Name: "{group}\Pengaturan Printer";           Filename: "{app}\{#ConfigExe}"
Name: "{group}\Uninstall {#AppName}";         Filename: "{uninstallexe}"
Name: "{commondesktop}\Pengaturan Printer";   Filename: "{app}\{#ConfigExe}"; Tasks: not autostart

[Registry]
; Autostart di HKCU Run
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "KetokoPrintService"; \
    ValueData: """{app}\{#ServiceExe}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Jalankan service setelah install selesai
Filename: "{app}\{#ServiceExe}"; Description: "Jalankan {#AppName} sekarang"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Matikan service sebelum uninstall
Filename: "taskkill"; Parameters: "/f /im {#ServiceExe}"; Flags: runhidden; RunOnceId: "KillService"
Filename: "taskkill"; Parameters: "/f /im {#ConfigExe}";  Flags: runhidden; RunOnceId: "KillConfig"
