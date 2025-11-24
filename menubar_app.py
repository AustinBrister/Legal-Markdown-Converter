import rumps
import subprocess
import socket
import time
import webbrowser
import os
import threading

class MarkdownConverterApp(rumps.App):
    def __init__(self):
        super(MarkdownConverterApp, self).__init__("⚖️", quit_button="Quit Converter")
        self.project_dir = os.path.expanduser("~/DevHubs/AWB-MarkItDown")
        self.port = 5050
        self.server_process = None
        self.menu = [
            rumps.MenuItem("Open Converter", callback=self.open_converter),
            rumps.MenuItem("Restart Server", callback=self.restart_server),
            None,  # Separator
            rumps.MenuItem("Server Status: Checking...", callback=None)
        ]
        
        # Start server on launch
        threading.Thread(target=self.start_server, daemon=True).start()
        
        # Check server status periodically
        rumps.Timer(self.check_status, 5).start()
    
    def is_server_running(self):
        """Check if server is running"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', self.port))
            sock.close()
            return result == 0
        except:
            return False
    
    def start_server(self):
        """Start the Flask server"""
        if self.is_server_running():
            self.update_status("Server Status: Already Running ✅")
            return
        
        self.update_status("Server Status: Starting...")
        
        # Kill any existing process
        subprocess.run(f"lsof -ti:{self.port} | xargs kill -9", shell=True, capture_output=True)
        time.sleep(0.5)
        
        # Start Flask server
        cmd = f"cd {self.project_dir} && source venv/bin/activate && python gui_launcher.py"
        self.server_process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # Wait for server to start
        for _ in range(30):
            if self.is_server_running():
                self.update_status("Server Status: Running ✅")
                rumps.notification(
                    "Markdown Converter Ready",
                    "Server is running",
                    "Click the ⚖️ icon to open"
                )
                return
            time.sleep(0.5)
        
        self.update_status("Server Status: Failed ❌")
    
    def update_status(self, status):
        """Update the status menu item"""
        self.menu["Server Status: Checking..."].title = status
    
    def check_status(self, _):
        """Periodically check server status"""
        if self.is_server_running():
            self.update_status("Server Status: Running ✅")
        else:
            self.update_status("Server Status: Not Running ❌")
    
    @rumps.clicked("Open Converter")
    def open_converter(self, _):
        """Open the converter in default browser"""
        if not self.is_server_running():
            rumps.notification(
                "Server Not Running",
                "Starting server...",
                "Please wait a moment"
            )
            threading.Thread(target=self.start_server, daemon=True).start()
            time.sleep(3)
        
        # Open in default browser
        webbrowser.open(f"http://127.0.0.1:{self.port}")
    
    @rumps.clicked("Restart Server")
    def restart_server(self, _):
        """Restart the Flask server"""
        rumps.notification(
            "Restarting Server",
            "Please wait...",
            "This may take a few seconds"
        )
        
        # Kill existing process
        subprocess.run(f"lsof -ti:{self.port} | xargs kill -9", shell=True, capture_output=True)
        time.sleep(1)
        
        # Start again
        threading.Thread(target=self.start_server, daemon=True).start()
    
    def quit(self):
        """Clean shutdown"""
        # Kill server process
        subprocess.run(f"lsof -ti:{self.port} | xargs kill -9", shell=True, capture_output=True)
        rumps.quit_application()

if __name__ == "__main__":
    app = MarkdownConverterApp()
    app.run()