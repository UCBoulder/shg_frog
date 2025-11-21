# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/shg_frog/scripts.py'],
    pathex=[],
    binaries=[],
    datas=[('src/shg_frog/data', 'data'), ('src/shg_frog/view/GUI', 'view/GUI')],
    hiddenimports=['imageio',
    'imageio.plugins',
    'imageio.plugins.tifffile',
    'imageio.v3_plugins',
    'tifffile'],
    hookspath=['hooks'],
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
    name='scripts',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='shg_frog',
)
