# Legal Markdown Converter

A document-to-markdown conversion tool built for legal professionals preparing documents for AI and LLM workflows.

## Why This Exists

Large Language Models work best with clean markdown text. But legal documents come in messy formats - scanned PDFs, Westlaw downloads with embedded links everywhere, RTF files disguised as .doc files, and more. This tool handles all of that automatically.

## Features

### Smart OCR
- Automatically detects when a PDF is scanned (image-based) vs. text-based
- Only runs OCR when actually needed, saving time on text-based PDFs
- Uses Tesseract for reliable text extraction from scanned documents

### Legal-Specific Handling
- **Westlaw Link Stripping**: Removes the excessive citation hyperlinks that Westlaw embeds in documents (these waste context window tokens and confuse LLMs)
- **RTF Detection**: Identifies RTF files masquerading as .doc files (a common Westlaw quirk)

### Email Support (EML/MSG)
- Converts Outlook .msg and standard .eml email files
- Automatically extracts and converts all attachments
- Combines email body and attachments into a single markdown file
- Adds clear separator headers (e.g., "# Begin Email Attachment 1") so LLMs know where attachments start
- Handles nested attachments of any supported format

### ZIP Archive Support
- Extracts and converts all files within ZIP archives
- Handles nested ZIPs (ZIPs within ZIPs)
- Adds clear headers for each file (e.g., "### File 1: contract.pdf")
- Works with ZIP attachments in emails too

### Multi-Format Support
- Email files (.eml, .msg) with attachments
- ZIP archives (with recursive extraction)
- PDF (with automatic OCR when needed)
- Word (.docx)
- RTF
- HTML
- PowerPoint, Excel, and more via Pandoc

### Clean Interface
- Drag-and-drop web interface
- Works on macOS and Windows
- Configure your preferred browser in `config.json`

## Installation

### Prerequisites
- Python 3.10 or higher
- Pandoc (document conversion)
- Tesseract OCR (for scanned PDFs)

---

### Windows Installation

#### Step 1: Install Python
1. Download Python from [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer
3. **IMPORTANT:** Check the box that says "Add Python to PATH" before clicking Install

#### Step 2: Install Tesseract OCR
1. Download from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer
3. **IMPORTANT:** During installation, check the option to "Add to PATH"
4. If you missed the PATH option, manually add `C:\Program Files\Tesseract-OCR` to your system PATH:
   - Search "Environment Variables" in Windows
   - Click "Environment Variables"
   - Under "System Variables", find "Path" and click "Edit"
   - Click "New" and add `C:\Program Files\Tesseract-OCR`
   - Click OK on all dialogs

#### Step 3: Install Pandoc
1. Download from [pandoc.org/installing.html](https://pandoc.org/installing.html)
2. Run the Windows installer (it adds to PATH automatically)

#### Step 4: Download Legal Markdown Converter
```powershell
git clone https://github.com/AustinBrister/Legal-Markdown-Converter.git
cd Legal-Markdown-Converter
git submodule init
git submodule update
```

Or download and extract the ZIP from GitHub.

#### Step 5: Run the Converter
Double-click `launch.bat` - it will:
- Create a virtual environment (first time only)
- Install Python dependencies (first time only)
- Check for Tesseract and Pandoc
- Start the server and open your browser

---

### macOS Installation

#### Step 1: Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Step 2: Install Dependencies
```bash
brew install python pandoc tesseract
```

#### Step 3: Download Legal Markdown Converter
```bash
git clone https://github.com/AustinBrister/Legal-Markdown-Converter.git
cd Legal-Markdown-Converter
git submodule init
git submodule update
```

#### Step 4: Run the Converter
Double-click `launch.command` or run:
```bash
./launch.command
```

## Usage

**Just double-click the launch file each time you want to use the converter:**
- **Windows:** Double-click `launch.bat`
- **macOS:** Double-click `launch.command`

The launch script handles everything - it starts the server and opens your browser automatically. When you're done, just close the terminal window.

### Troubleshooting

**"Python is not recognized"** - Python isn't in your PATH. Reinstall Python and check "Add to PATH".

**"Tesseract is not recognized"** - Add `C:\Program Files\Tesseract-OCR` to your system PATH (see installation steps above).

**Port already in use** - The launch script will automatically kill any existing process on port 5050.

## Configuration

Edit `config.json` to customize:

```json
{
  "browser": {
    "enabled": true,
    "path": "",
    "use_app_mode": true
  },
  "server": {
    "port": 5050,
    "host": "127.0.0.1"
  }
}
```

- **browser.path**: Set a specific browser path (leave empty for system default)
- **server.port**: Change the port if 5050 is in use

## Output

Converted files are saved to:
```
~/Downloads/Converted to MD/
```

## Roadmap

Future features planned:
- Additional legal-specific file format handling
- More context-optimized conversion settings for different LLM use cases
- Batch processing improvements

## Credits

Built by Austin W. Brister, Partner at McGinnis Lochridge LLP

Uses Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) library for core conversion functionality.

## License

Copyright (c) 2025 Austin Brister. All rights reserved.

This software incorporates open source components which are subject to their respective licenses. See the "Open Source Licenses" section in the application for details.
