@echo off
REM Legal Markdown Converter - Windows Launch Script
REM Double-click this file to start the converter

cd /d "%~dp0"

REM Check for winget (Windows Package Manager)
winget --version >nul 2>&1
if errorlevel 1 (
    set HAVE_WINGET=0
) else (
    set HAVE_WINGET=1
)

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed.
    if %HAVE_WINGET%==1 (
        echo Installing Python via winget...
        winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo Failed to install Python automatically.
            echo Please install manually from https://www.python.org/downloads/
            echo Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
        echo Python installed. Please close this window and run launch.bat again.
        pause
        exit /b 0
    ) else (
        echo Please install Python 3.10+ from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

REM Check for Tesseract
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo Tesseract OCR is not installed.
    if %HAVE_WINGET%==1 (
        echo Installing Tesseract via winget...
        winget install UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo Failed to install Tesseract automatically.
            echo Please install manually from https://github.com/UB-Mannheim/tesseract/wiki
            pause
        ) else (
            echo Tesseract installed. You may need to restart this script for PATH to update.
        )
    ) else (
        echo Please install from https://github.com/UB-Mannheim/tesseract/wiki
        echo Make sure to check "Add to PATH" during installation.
        pause
    )
)

REM Check for Pandoc
pandoc --version >nul 2>&1
if errorlevel 1 (
    echo Pandoc is not installed.
    if %HAVE_WINGET%==1 (
        echo Installing Pandoc via winget...
        winget install JohnMacFarlane.Pandoc --silent --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo Failed to install Pandoc automatically.
            echo Please install manually from https://pandoc.org/installing.html
            pause
        ) else (
            echo Pandoc installed. You may need to restart this script for PATH to update.
        )
    ) else (
        echo Please install from https://pandoc.org/installing.html
        pause
    )
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
