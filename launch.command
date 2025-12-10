#!/bin/bash
# Legal Markdown Converter - macOS Launch Script
# Double-click this file to start the converter

cd "$(dirname "$0")" || exit 1

echo "============================================"
echo " Legal Markdown Converter"
echo "============================================"
echo ""

# Check for Homebrew
if ! command -v brew &> /dev/null; then
  echo "Homebrew is not installed."
  echo "Installing Homebrew (this may take a few minutes)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Add Homebrew to PATH for this session (Apple Silicon vs Intel)
  if [ -f "/opt/homebrew/bin/brew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -f "/usr/local/bin/brew" ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
  echo "Python 3 is not installed."
  echo "Installing Python via Homebrew..."
  brew install python
fi

# Check for Tesseract
if ! command -v tesseract &> /dev/null; then
  echo "Tesseract OCR is not installed."
  echo "Installing Tesseract via Homebrew..."
  brew install tesseract
fi

# Check for Pandoc
if ! command -v pandoc &> /dev/null; then
  echo "Pandoc is not installed."
  echo "Installing Pandoc via Homebrew..."
  brew install pandoc
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  echo "Installing Python dependencies..."
  venv/bin/pip install -r requirements.txt
else
  source venv/bin/activate
fi

# Check for Flask and install if missing
if ! venv/bin/python -c "import flask" &> /dev/null; then
  echo "Installing Python dependencies..."
  venv/bin/pip install -r requirements.txt
fi

# Kill any process already on port 5050
PID=$(lsof -ti:5050)
[ -n "$PID" ] && kill -9 $PID && sleep 1

# Launch the app
echo "Starting Legal Markdown Converter..."
venv/bin/python gui_launcher.py &

# Wait for Flask to start up
while ! nc -z localhost 5050; do sleep 0.5; done
sleep 1

# Read browser from config, or use default
BROWSER_PATH=$(venv/bin/python -c "import json; c=json.load(open('config.json')); print(c.get('browser',{}).get('path',''))" 2>/dev/null)

if [ -n "$BROWSER_PATH" ] && [ -e "$BROWSER_PATH" ]; then
  # Use configured browser
  "$BROWSER_PATH" "http://127.0.0.1:5050" &
else
  # Use system default browser
  open "http://127.0.0.1:5050"
fi

echo "Legal Markdown Converter is running at http://127.0.0.1:5050"
wait
