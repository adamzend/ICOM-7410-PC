@echo off
cd /d "%~dp0"
if exist "%~dp0ICOM-7410-PC\ICOM-7410-PC.exe" (
  start "" "%~dp0ICOM-7410-PC\ICOM-7410-PC.exe"
) else (
  start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py"
)
