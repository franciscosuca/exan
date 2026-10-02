# PyInstaller spec for the Exan engine (sidecar). Build with: pyinstaller --noconfirm --clean exan-sidecar.spec
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("uvicorn") + collect_submodules("exan_sidecar")

a = Analysis(
    ["sidecar_entry.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter", "IPython", "matplotlib", "numpy", "pytest", "PyInstaller"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="exan-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
