@echo off
cd /d "%~dp0"
set "PYINSTALLER_CONFIG_DIR=%~dp0work\pyinstaller-cache"
"%~dp0.venv\Scripts\python.exe" -m unittest test_core test_memory_picker test_release -v
if errorlevel 1 exit /b 1
"%~dp0.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name ICOM-7410-PC --add-data "%~dp0assets;assets" --add-data "%~dp0LICENSE;." --distpath . --workpath work\build --specpath work app.py
