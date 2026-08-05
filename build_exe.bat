@echo off
echo ==========================================
echo  Proxy Collector Pro - Build Script
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Running tests...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo WARNING: Some tests failed. Continuing anyway...
)

echo.
echo [3/4] Building executable...
pyinstaller --clean --onefile --windowed ^
    --name "ProxyCollectorPro" ^
    --add-data "data;data" ^
    --add-data "assets;assets" ^
    --hidden-import=customtkinter ^
    --hidden-import=requests ^
    --hidden-import=socks ^
    --hidden-import=sqlite3 ^
    main.py

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Copying additional files...
if not exist "dist\data" mkdir "dist\data"
if not exist "dist\assets" mkdir "dist\assets"
if not exist "dist\exports" mkdir "dist\exports"
if not exist "dist\logs" mkdir "dist\logs"

echo.
echo ==========================================
echo  Build Complete!
echo  Output: dist\ProxyCollectorPro.exe
echo ==========================================
pause
