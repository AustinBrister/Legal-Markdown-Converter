#!/bin/bash
cd "$HOME/DevHubs/AWB-MarkItDown" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo "❌ Virtual environment not found. Run: python3.10 -m venv venv"
  exit 1
fi

# Activate virtual environment
source venv/bin/activate || {
  echo "❌ Failed to activate virtual environment."
  exit 1
}

# Check for Flask and warn if missing
if ! python -c "import flask" &> /dev/null; then
  echo "❌ Flask is not installed in this virtual environment."
  echo "Run: pip install flask"
  exit 1
fi

# Kill any process already on port 5050
PID=$(lsof -ti:5050)
[ -n "$PID" ] && kill -9 $PID && sleep 1

# Launch the app
echo "🚀 Starting MarkItDown GUI..."
python gui_launcher.py &

# Wait for Flask to start up
while ! nc -z localhost 5050; do sleep 0.5; done
sleep 2
open http://127.0.0.1:5050
wait