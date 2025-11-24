# AWB MarkItDown - Attorney Document Converter

A custom macOS application wrapper around Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) library, specifically designed for legal document conversion workflows.

## Features

- **Beautiful Web Interface**: Dark-themed Flask web app for drag-and-drop document conversion
- **macOS Menubar Integration**: Persistent menubar app for quick access
- **Smart PDF Handling**: 
  - Automatic detection of scanned PDFs requiring OCR
  - Fallback OCR processing with Tesseract
  - Text extraction optimization
- **Westlaw Link Stripping**: Automatically removes citation links from converted documents
- **RTF Detection**: Identifies RTF files masquerading as .doc files (common with Westlaw downloads)
- **Multi-Format Support**: 
  - PDF (with OCR)
  - Word (.docx)
  - RTF
  - HTML
  - And more via Pandoc

## Prerequisites

- Python 3.10 or higher
- Homebrew (for system dependencies)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AWB-MarkItDown.git
   cd AWB-MarkItDown
   ```

2. **Install system dependencies:**
   ```bash
   brew install pandoc tesseract
   ```

3. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize the MarkItDown submodule:**
   ```bash
   git submodule init
   git submodule update
   ```

## Usage

### Option 1: Launch Script (Recommended)

Double-click `launch_MarkItDown_gui.command` or run:
```bash
./launch_MarkItDown_gui.command
```

This will:
- Activate the virtual environment
- Start the Flask server
- Open the web interface in your default browser

### Option 2: Menubar App

Run the menubar app for persistent access:
```bash
python menubar_app.py
```

This creates a ⚖️ icon in your menubar with options to:
- Open the converter
- Restart the server
- Check server status

### Option 3: Manual Launch

```bash
source venv/bin/activate
python gui_launcher.py
```

Then navigate to `http://127.0.0.1:5050`

## Output

Converted files are automatically saved to:
```
~/Downloads/Converted to MD/
```

## Project Structure

```
AWB-MarkItDown/
├── gui_launcher.py              # Main Flask web application
├── menubar_app.py               # macOS menubar app
├── launch_MarkItDown_gui.command # Launch script
├── requirements.txt             # Python dependencies
├── src/                         # Microsoft MarkItDown (git submodule)
└── venv/                        # Virtual environment (not in git)
```

## Development Notes

- The `src/` directory is a git submodule pointing to Microsoft's MarkItDown repository
- All converted documents include automatic Westlaw link removal
- OCR is triggered automatically when PDFs have insufficient text content
- The web interface includes real-time progress updates and automatic downloads

## Credits

Built by Austin W. Brister, Partner at McGinnis Lochridge LLP

Based on Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) library.

## License

This wrapper is MIT licensed. See Microsoft's MarkItDown repository for its license terms.
