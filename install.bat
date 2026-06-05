@echo off
:: Ketoko POS Print Service — installer for Windows
setlocal

echo === Ketoko POS Print Service Installer ===
echo Platform: Windows

:: Install Python deps
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo ERROR: pip gagal. Pastikan Python 3 sudah terinstall.
    pause & exit /b 1
)

:: Daftarkan sebagai Task Scheduler agar auto-start saat login
set TASK_NAME=KetokoPrintService
set SCRIPT_PATH=%~dp0service.py

schtasks /delete /tn "%TASK_NAME%" /f 2>nul

schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "pythonw.exe \"%SCRIPT_PATH%\"" ^
    /sc onlogon ^
    /rl limited ^
    /f

echo.
echo Service terdaftar di Task Scheduler sebagai: %TASK_NAME%
echo Jalankan sekarang:
python "%SCRIPT_PATH%"

pause
