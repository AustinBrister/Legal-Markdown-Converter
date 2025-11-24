#!/bin/bash
# Austin's Markdown Converter - Brave Web App Launcher
# Save as: launch-markdown-brave.command

cd "$HOME/DevHubs/AWB-MarkItDown" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  osascript -e 'display alert "Virtual Environment Missing" message "Virtual environment not found. Please run: python3.10 -m venv venv" as critical'
  exit 1
fi

# Activate virtual environment
source venv/bin/activate || {
  osascript -e 'display alert "Activation Failed" message "Failed to activate virtual environment." as critical'
  exit 1
}

# Check for Flask
if ! python -c "import flask" &> /dev/null; then
  osascript -e 'display alert "Flask Missing" message "Flask is not installed. Run: pip install flask" as critical'
  exit 1
fi

# Kill any process already on port 5050
PID=$(lsof -ti:5050)
[ -n "$PID" ] && kill -9 $PID && sleep 1

# Launch the Flask app silently
echo "🚀 Starting Austin Brister's Wonderful Markdown Converter..."
nohup python gui_launcher.py > /dev/null 2>&1 &

# Wait for Flask to start
echo "⏳ Waiting for server to start..."
while ! nc -z localhost 5050; do sleep 0.5; done
sleep 1

# Launch in Brave as a clean web app
echo "🌐 Launching in Brave Browser..."
"/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
  --app="http://127.0.0.1:5050" \
  --window-size=700,850 \
  --window-position=center \
  --enable-features=OverlayScrollbar \
  --disable-brave-rewards-extension \
  --disable-brave-wallet-extension \
  --user-data-dir="$HOME/Library/Application Support/AWB-MarkdownConverter" \
  2>/dev/null &

# Show success notification
osascript -e 'display notification "Markdown Converter is ready" with title "Austin Brister'"'"'s Wonderful Markdown Converter" subtitle "Running in Brave Browser"'

# Close terminal window after a delay
(sleep 3 && osascript -e 'tell application "Terminal" to close first window' &) &

echo "✅ Converter launched successfully!"
echo "📝 Your downloads will be saved to: ~/Downloads/Converted to MD"

exit 0