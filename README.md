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
- Pandoc and Tesseract (for OCR)

### macOS
```bash
# Install system dependencies
brew install pandoc tesseract

# Clone and setup
git clone https://github.com/AustinBrister/Legal-Markdown-Converter.git
cd Legal-Markdown-Converter
git submodule init
git submodule update
```

### Windows
```powershell
# Install Pandoc: https://pandoc.org/installing.html
# Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki

# Clone and setup
git clone https://github.com/AustinBrister/Legal-Markdown-Converter.git
cd Legal-Markdown-Converter
git submodule init
git submodule update
```

## Usage

### macOS
Double-click `launch.command` or run:
```bash
./launch.command
```

### Windows
Double-click `launch.bat` or run:
```cmd
launch.bat
```

The launch scripts will:
- Create a virtual environment if needed
- Install dependencies automatically
- Start the server
- Open your browser to the converter

### Manual Launch
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run the server
python gui_launcher.py
```
Then open http://127.0.0.1:5050

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

MIT License. See Microsoft's MarkItDown repository for its license terms.
