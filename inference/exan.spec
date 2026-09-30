# PyInstaller spec for the Tauri inference sidecar.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("app")

a = Analysis(
    ["desktop_entrypoint.py"],
    pathex=["."],
    hiddenimports=hiddenimports,
    datas=[],
    binaries=[],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="exan-inference", console=True)
