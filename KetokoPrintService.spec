# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — KetokoPrintService.exe (tray + service)

a = Analysis(
    ['tray.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'service',
        'win32print',
        'win32api',
        'pystray._win32',
        'PIL._tkinter_finder',
        'flask',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'click',
        'serial',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KetokoPrintService',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)
