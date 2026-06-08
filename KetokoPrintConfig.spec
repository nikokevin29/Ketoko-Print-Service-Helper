# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — KetokoPrintConfig.exe (config GUI)

a = Analysis(
    ['gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32print',
        'win32api',
        'tkinter',
        'tkinter.ttk',
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
    name='KetokoPrintConfig',
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
