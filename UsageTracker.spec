# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

proj = Path(SPECPATH)

a = Analysis(
    ['src/main.py'],
    pathex=[str(proj / 'src')],
    binaries=[],
    datas=[
        (str(proj / 'assets' / 'themes'), 'assets/themes'),
        (str(proj / 'assets' / 'chart.umd.min.js'), 'assets'),
        (str(proj / 'assets' / 'icon.ico'), 'assets'),
        (str(proj / 'locales'), 'locales'),
    ],
    hiddenimports=['psutil', 'pystray', 'PIL', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UsageTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(proj / 'assets' / 'icon.ico')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UsageTracker',
)
