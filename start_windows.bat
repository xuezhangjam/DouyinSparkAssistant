@echo off
cd /d "%~dp0"
if not exist ".venv-win\Scripts\pythonw.exe" (
  echo First run: install Python 3.11 or later, then follow WINDOWS.md.
  pause
  exit /b 1
)
start "" ".venv-win\Scripts\pythonw.exe" "windows_app.py"
