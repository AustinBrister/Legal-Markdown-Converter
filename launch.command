#!/bin/bash
# Legal Markdown Converter - macOS Launch Script

cd "$(dirname "$0")" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Creating one..."
  python3 -m venv venv
  source venv/bin/activate
  venv/bin/pip install -r requirements.txt
else
  source venv/bin/activate
fi

# Check for Flask and install if missing
if ! venv/bin/python -c "import flask" &> /dev/null; then
  echo "Installing dependencies..."
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
