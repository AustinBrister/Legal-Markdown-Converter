@echo off
REM Legal Markdown Converter - Windows Launch Script
REM Double-click this file to start the converter

cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check for Tesseract
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Tesseract OCR is not installed or not in PATH.
    echo Scanned PDF conversion will not work without it.
    echo.
    echo To install Tesseract:
    echo 1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo 2. Run the installer
    echo 3. IMPORTANT: Check "Add to PATH" during installation
    echo    Or manually add: C:\Program Files\Tesseract-OCR to your PATH
    echo.
    pause
)

REM Check for Pandoc
pandoc --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Pandoc is not installed or not in PATH.
    echo Some document formats may not convert properly.
    echo.
    echo To install Pandoc:
    echo 1. Download from: https://pandoc.org/installing.html
    echo 2. Run the Windows installer (adds to PATH automatically)
    echo.
    pause
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Installing Python dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check for Flask and install if missing
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
)

REM Kill any process already on port 5050
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5050 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo ============================================
echo  Legal Markdown Converter
echo ============================================
echo.
echo Starting server...
echo.

REM Open browser after a short delay (in background)
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5050"

REM Run the Flask server (this keeps the window open)
python gui_launcher.py

echo.
echo Server stopped.
pause
