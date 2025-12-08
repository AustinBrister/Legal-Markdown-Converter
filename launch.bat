@echo off
REM Legal Markdown Converter - Windows Launch Script

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Make sure Python is installed.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check for Flask
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Flask is not installed. Installing dependencies...
    pip install -r requirements.txt
)

REM Kill any process already on port 5050
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5050 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo Starting Legal Markdown Converter...
start /b python gui_launcher.py

REM Wait for server to start
:waitloop
timeout /t 1 /nobreak >nul
netstat -an | findstr :5050 | findstr LISTENING >nul
if errorlevel 1 goto waitloop

REM Read browser config and open
python -c "import json; c=json.load(open('config.json')); b=c.get('browser',{}); p=c.get('server',{}); import webbrowser; webbrowser.open(f'http://{p.get(\"host\",\"127.0.0.1\")}:{p.get(\"port\",5050)}')" 2>nul
if errorlevel 1 (
    start http://127.0.0.1:5050
)

echo.
echo Legal Markdown Converter is running at http://127.0.0.1:5050
echo Press Ctrl+C to stop the server, or close this window.
echo.

REM Keep window open and wait for the Flask process
python gui_launcher.py
