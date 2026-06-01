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
        (str(proj / 'assets' / 'banner.png'), 'assets'),
        (str(proj / 'assets' / 'logo.png'), 'assets'),
        (str(proj / 'locales'), 'locales'),
        (str(proj / 'ui' / 'web'), 'ui/web'),
    ],
    hiddenimports=['psutil', 'pystray', 'PIL', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'tkinter.simpledialog', 'ui.styled_widgets', 'ui.settings_window', 'ui.onboarding', 'ui.tab_general', 'ui.tab_categories', 'ui.tab_browsers', 'ui.tab_games', 'ui.tab_ignore', 'ui.tab_database', 'ui.tab_feedback'],
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
