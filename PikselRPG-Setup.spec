# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['installer/install.py'],
    pathex=['C:/Users/macie/Downloads/PikselRPG (3)/PikselRPG'],
    binaries=[],
    datas=[('C:/Users/macie/Downloads/PikselRPG (3)/PikselRPG/installer/payload.zip', '.'), ('C:/Users/macie/Downloads/PikselRPG (3)/PikselRPG/pikselrpg/assets', 'pikselrpg/assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PikselRPG-Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/macie/Downloads/PikselRPG (3)/PikselRPG/pikselrpg/assets/icon.ico'],
)
