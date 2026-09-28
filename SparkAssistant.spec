# Build both entry points into one folder with shared libraries and Chromium.
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
licenses = []
for package in ("PySide6_Essentials", "shiboken6", "playwright", "greenlet", "pyee"):
    licenses += copy_metadata(package)

gui = Analysis([str(root / "windows_app.py")], pathex=[str(root)],
               datas=licenses, excludes=["tkinter"], hiddenimports=[])
worker = Analysis([str(root / "windows_worker.py")], pathex=[str(root)],
                  datas=[(str(root / ".windows-browsers"), "browsers")],
                  excludes=["PySide6", "tkinter"], hiddenimports=[])
gui_exe = EXE(PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
              name="SparkAssistant", console=False, upx=False)
worker_exe = EXE(PYZ(worker.pure), worker.scripts, [], exclude_binaries=True,
                 name="SparkWorker", console=True, upx=False)
bundle = COLLECT(gui_exe, worker_exe, gui.binaries, gui.datas, worker.binaries, worker.datas,
                 name="SparkAssistant-Windows-x64", upx=False)
