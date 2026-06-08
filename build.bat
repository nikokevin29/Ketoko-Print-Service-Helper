@echo off
echo ============================================
echo  Ketoko POS Print Service — Build Script
echo ============================================

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller tidak ditemukan. Jalankan:
    echo         pip install pyinstaller
    pause & exit /b 1
)

echo.
echo [1/2] Build KetokoPrintService.exe ...
pyinstaller --clean KetokoPrintService.spec
if errorlevel 1 ( echo [ERROR] Build service gagal. & pause & exit /b 1 )

echo.
echo [2/2] Build KetokoPrintConfig.exe ...
pyinstaller --clean KetokoPrintConfig.spec
if errorlevel 1 ( echo [ERROR] Build config gagal. & pause & exit /b 1 )

echo.
echo [OK] Build selesai. Output di folder dist\
echo      - dist\KetokoPrintService.exe
echo      - dist\KetokoPrintConfig.exe
echo.
echo Selanjutnya: jalankan installer.iss dengan Inno Setup Compiler
pause
