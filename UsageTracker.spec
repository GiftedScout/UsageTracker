# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

proj = Path(SPECPATH)

# 显式收集 pystray（PyInstaller 经常漏掉纯 Python 包的后端模块）
def collect_pkg(name):
    from PyInstaller.utils.hooks import collect_submodules, collect_data_files
    return (collect_submodules(name), collect_data_files(name))

_pystray_modules, _pystray_data = collect_pkg('pystray')

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
    ] + _pystray_data,
    hiddenimports=[
        'psutil', 'pystray', 'pystray._win32', 'pystray._win32_common',
        'PIL', 'PIL.Image', 'PIL.ImageDraw',
    ] + _pystray_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(proj / 'hook-pystray.py')],
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
