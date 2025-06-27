# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules 
from PyInstaller.utils.hooks import collect_data_files
scipy_modules = collect_submodules('scipy')
scipy_data = collect_data_files('scipy')
 
added_files=[('../src/shg_frog/data', 'data'),
    ('../src/shg_frog/view/GUI','GUI')]

a = Analysis(
    ['..\\src\\shg_frog\\dist_scripts.py'],
    pathex=[],
    binaries=[],
    datas=added_files + scipy_data,
    hiddenimports=['hardware_comms'] + scipy_modules,
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
    a.binaries,
    a.datas,
    [],
    name='FROGware',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
