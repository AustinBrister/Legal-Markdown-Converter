import os
import sys
import time
import threading
import subprocess
import socket
import webview

# Configuration
APP_TITLE = "Austin Brister's Wonderful Markdown Converter"
APP_URL = "http://127.0.0.1:5050"
APP_PORT = 5050
PROJECT_DIR = os.path.expanduser("~/DevHubs/Legal-Markdown-Converter")

def is_port_open(port):
    """Check if a port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def kill_existing_process(port):
    """Kill any process using the specified port"""
    try:
        result = subprocess.run(f"lsof -ti:{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            subprocess.run(f"kill -9 {result.stdout.strip()}", shell=True)
            time.sleep(0.5)
    except:
        pass

def start_flask_server():
    """Start the Flask server in background"""
    kill_existing_process(APP_PORT)
    
    # Start Flask in the virtual environment
    cmd = f"cd {PROJECT_DIR} && source venv/bin/activate && python gui_launcher.py"
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for server to start
    print("Starting server...")
    for i in range(30):
        if is_port_open(APP_PORT):
            print("Server is ready!")
            time.sleep(0.5)
            return True
        time.sleep(0.5)
        print(".", end="", flush=True)
    
    return False

def main():
    # Check if server is already running
    if not is_port_open(APP_PORT):
        if not start_flask_server():
            print("Failed to start server!")
            sys.exit(1)
    
    # Create native window
    window = webview.create_window(
        title=APP_TITLE,
        url=APP_URL,
        width=700,
        height=850,
        resizable=True,
        background_color='#0f0f1e'
    )
    
    # Start the window
    webview.start(debug=False, gui='cocoa')  # cocoa = native macOS
    
    # Cleanup on exit
    kill_existing_process(APP_PORT)

if __name__ == "__main__":
    main()