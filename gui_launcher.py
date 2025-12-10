# Legal Markdown Converter - Main Flask Application
from flask import Flask, request, render_template_string, jsonify, send_file
import os
import tempfile
import re
import subprocess
import zipfile
import socket
from markitdown import MarkItDown
from markdown_it import MarkdownIt
from markdown_it.token import Token
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import json
import uuid
import threading
import time
from werkzeug.utils import secure_filename
from email_converter import process_email_file

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()

# Load config for output folder
def get_output_folder():
    """Get output folder from config or use default."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            path = config.get('local_save', {}).get('path', '~/Downloads/Converted to MD')
            return os.path.expanduser(path)
    except:
        return os.path.expanduser("~/Downloads/Converted to MD")

OUTPUT_FOLDER = get_output_folder()
DEBUG_FOLDER = os.path.join(OUTPUT_FOLDER, "debug")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def is_debug_enabled():
    """Check if debug mode is enabled in config."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return config.get('debug', {}).get('save_intermediate_pdf', False)
    except:
        return False

def get_local_ip():
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Store converted files in memory for remote downloads
converted_files = {}

PANDOC_FORMATS = {
    ".docx", ".odt", ".html", ".htm", ".tex", ".epub", ".rst", ".org", ".rtf"}

# Store processing status
processing_status = {}

def is_rtf_file(filepath):
    """Check if a file is actually RTF format by looking at its content."""
    try:
        with open(filepath, 'rb') as f:
            # Read first few bytes to check for RTF signature
            header = f.read(10)
            return header.startswith(b'{\\rtf')
    except:
        return False

def needs_ocr(pdf_path):
    """Check if a PDF needs OCR by testing if it has extractable text."""
    try:
        doc = fitz.open(pdf_path)
        # Check first few pages for text
        pages_to_check = min(3, len(doc))
        total_text = ""
        
        for i in range(pages_to_check):
            page = doc[i]
            text = page.get_text().strip()
            total_text += text
            
        doc.close()
        
        # If we have very little text relative to the page count, probably needs OCR
        # This is a heuristic - adjust threshold as needed
        return len(total_text) < 50 * pages_to_check
    except:
        return True  # If we can't read it, assume it needs OCR

def ocr_pdf(pdf_path):
    """Perform OCR on a PDF and return the extracted text."""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Convert page to image
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            text = pytesseract.image_to_string(img)
            
            if text.strip():
                full_text.append(f"## Page {page_num + 1}\n\n{text}")
        
        doc.close()
        return "\n\n---\n\n".join(full_text)
    except Exception as e:
        raise Exception(f"OCR failed: {str(e)}")

def strip_westlaw_links(text):
    # Fix broken lines inside [label] text first
    text = re.sub(r'\[([^\]].*?)\n([^\]].*?)\]\(', lambda m: f"[{m.group(1)} {m.group(2)}](", text)

    # Remove markdown links starting with http
    # Pattern handles nested parentheses
    pattern = r'\[([^\]]+(?:\[[^\]]*\][^\]]*)*)\]\(http(?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)'

    text = re.sub(pattern, r'\1', text, flags=re.DOTALL)

    # Only clean up multiple spaces (2 or more), preserving all line breaks
    text = re.sub(r'  +', ' ', text)

    return text.strip()


def convert_file_to_markdown(file_path_or_data, filename, is_data=False):
    """
    Convert a single file to markdown content.

    Args:
        file_path_or_data: Either a file path (str) or file bytes
        filename: The original filename (used for extension detection)
        is_data: If True, file_path_or_data is bytes; if False, it's a path

    Returns:
        str: The converted markdown content
    """
    ext = os.path.splitext(filename)[1].lower()

    # If we have bytes, write to temp file
    if is_data:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_path_or_data)
            file_path = tmp.name
        cleanup_needed = True
    else:
        file_path = file_path_or_data
        cleanup_needed = False

    try:
        # Handle PDFs
        if ext == ".pdf":
            if needs_ocr(file_path):
                return ocr_pdf(file_path)
            else:
                with open(file_path, "rb") as stream:
                    result = MarkItDown().convert_stream(stream)
                    content = strip_westlaw_links(result.markdown)
                    if len(content.strip()) < 50:
                        # Fall back to OCR if text extraction yielded little content
                        return ocr_pdf(file_path)
                    return content

        # Handle RTF (check actual content, not just extension)
        if is_rtf_file(file_path):
            try:
                pandoc_output = subprocess.run(
                    ["pandoc", file_path, "-f", "rtf", "-t", "markdown"],
                    capture_output=True, check=True, text=True
                )
                return strip_westlaw_links(pandoc_output.stdout)
            except:
                pass  # Fall through to MarkItDown

        # Handle Pandoc formats
        if ext in PANDOC_FORMATS:
            try:
                pandoc_output = subprocess.run(
                    ["pandoc", file_path, "-f", ext[1:], "-t", "markdown"],
                    capture_output=True, check=True, text=True
                )
                return strip_westlaw_links(pandoc_output.stdout)
            except:
                pass  # Fall through to MarkItDown

        # Default: use MarkItDown
        with open(file_path, "rb") as stream:
            result = MarkItDown().convert_stream(stream)
            return strip_westlaw_links(result.markdown)

    finally:
        if cleanup_needed and os.path.exists(file_path):
            os.unlink(file_path)


def process_zip_file(zip_data, zip_filename, status_callback=None):
    """
    Extract and convert all files from a ZIP archive.

    Args:
        zip_data: The ZIP file as bytes
        zip_filename: Original ZIP filename
        status_callback: Optional function to call with status updates

    Returns:
        str: Combined markdown content with headers for each file
    """
    content_parts = []
    content_parts.append(f"## Begin ZIP Contents\n**Archive:** {zip_filename}\n")

    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        tmp_zip.write(zip_data)
        tmp_zip_path = tmp_zip.name

    try:
        with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
            # Get list of files (skip directories and hidden files)
            file_list = [f for f in zf.namelist()
                        if not f.endswith('/')
                        and not os.path.basename(f).startswith('.')
                        and not f.startswith('__MACOSX')]

            for i, inner_filename in enumerate(file_list, 1):
                if status_callback:
                    status_callback(f"Processing ZIP file {i}/{len(file_list)}: {inner_filename}")

                inner_ext = os.path.splitext(inner_filename)[1].lower()
                display_name = os.path.basename(inner_filename)

                try:
                    inner_data = zf.read(inner_filename)

                    # Handle nested ZIPs recursively
                    if inner_ext == '.zip':
                        nested_content = process_zip_file(inner_data, display_name, status_callback)
                        content_parts.append(f"\n### ZIP File {i}: {display_name}\n\n{nested_content}")

                    # Handle nested emails
                    elif inner_ext in ['.eml', '.msg']:
                        try:
                            pdf_bytes, attachments = process_email_file(inner_data, display_name)
                            # For simplicity, just note it's an email - full processing would be recursive
                            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                                tmp_pdf.write(pdf_bytes)
                                tmp_pdf_path = tmp_pdf.name
                            try:
                                email_content = convert_file_to_markdown(tmp_pdf_path, "email.pdf")
                            finally:
                                os.unlink(tmp_pdf_path)
                            content_parts.append(f"\n### File {i}: {display_name}\n\n{email_content}")
                        except Exception as e:
                            content_parts.append(f"\n### File {i}: {display_name}\n\n[Error processing email: {str(e)}]")

                    # Handle all other files
                    else:
                        file_content = convert_file_to_markdown(inner_data, display_name, is_data=True)
                        content_parts.append(f"\n### File {i}: {display_name}\n\n{file_content}")

                except Exception as e:
                    content_parts.append(f"\n### File {i}: {display_name}\n\n[Error converting file: {str(e)}]")

    finally:
        os.unlink(tmp_zip_path)

    content_parts.append("\n## End ZIP Contents")
    return "\n".join(content_parts)

def process_single_file(filename, file_data, session_id, save_locally=True):
    """Process a single file and update status.

    Args:
        filename: Original filename
        file_data: File bytes
        session_id: Session ID for status updates
        save_locally: If True, save to local folder. If False, only store in memory for download.
    """
    ext = os.path.splitext(filename)[1].lower()
    input_path = os.path.join(UPLOAD_FOLDER, secure_filename(filename))

    # Save the file
    with open(input_path, 'wb') as f:
        f.write(file_data)

    output_filename = os.path.splitext(filename)[0] + ".md"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    file_id = str(uuid.uuid4())

    def save_output(content):
        """Save output based on whether this is a local or remote request."""
        if save_locally:
            # Local user - save to folder
            with open(output_path, "w", encoding="utf-8") as f_out:
                f_out.write(content)
        else:
            # Remote user - store in memory for download
            converted_files[file_id] = {
                'filename': output_filename,
                'content': content
            }

    try:
        # Handle ZIP files - extract and convert all contents
        if ext == ".zip":
            processing_status[session_id]['current_status'] = f'{filename} is a ZIP archive, extracting and converting contents...'

            try:
                def status_cb(msg):
                    processing_status[session_id]['current_status'] = f'{filename}: {msg}'

                content = process_zip_file(file_data, filename, status_cb)
                save_output(content)
                return {'type': 'success', 'message': f'{filename} ZIP archive converted successfully', 'file_id': file_id, 'filename': output_filename}

            except Exception as zip_err:
                return {'type': 'error', 'message': f'{filename} ZIP processing failed: {str(zip_err)}'}

        # Handle email files (EML/MSG) - convert to PDF first, then process
        if ext in [".eml", ".msg"]:
            processing_status[session_id]['current_status'] = f'{filename} is an email file, extracting content and attachments...'

            try:
                # Convert email to PDF (includes body + attachment cover sheets)
                pdf_bytes, separate_attachments = process_email_file(file_data, filename)

                # Save debug copy of the intermediate PDF (if enabled in config)
                if is_debug_enabled():
                    os.makedirs(DEBUG_FOLDER, exist_ok=True)
                    debug_pdf_path = os.path.join(DEBUG_FOLDER, os.path.splitext(filename)[0] + "_email_debug.pdf")
                    with open(debug_pdf_path, 'wb') as debug_file:
                        debug_file.write(pdf_bytes)
                    processing_status[session_id]['current_status'] = f'{filename} debug PDF saved to {debug_pdf_path}'

                # Process the combined PDF through our normal pipeline
                combined_content_parts = []

                # First, convert the main email PDF to markdown
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                    tmp_pdf.write(pdf_bytes)
                    tmp_pdf_path = tmp_pdf.name

                try:
                    if needs_ocr(tmp_pdf_path):
                        processing_status[session_id]['current_status'] = f'{filename} email body requires OCR...'
                        email_content = ocr_pdf(tmp_pdf_path)
                    else:
                        with open(tmp_pdf_path, "rb") as stream:
                            result = MarkItDown().convert_stream(stream)
                            email_content = strip_westlaw_links(result.markdown)
                finally:
                    os.unlink(tmp_pdf_path)

                combined_content_parts.append(email_content)

                # Process any attachments that couldn't be embedded in the PDF
                for i, attachment in enumerate(separate_attachments, 1):
                    att_filename = attachment['filename']
                    att_data = attachment['data']
                    att_ext = os.path.splitext(att_filename)[1].lower()

                    processing_status[session_id]['current_status'] = f'{filename}: Processing attachment {i} ({att_filename})...'

                    try:
                        # Handle ZIP attachments specially
                        if att_ext == ".zip":
                            def status_cb(msg):
                                processing_status[session_id]['current_status'] = f'{filename}: {msg}'
                            att_content = process_zip_file(att_data, att_filename, status_cb)
                        else:
                            # Use the helper function for all other types
                            att_content = convert_file_to_markdown(att_data, att_filename, is_data=True)

                        # Add attachment content with header
                        combined_content_parts.append(f"\n\n---\n\n# Begin Email Attachment {i}\n**Filename:** {att_filename}\n\n{att_content}")
                    except Exception as att_err:
                        combined_content_parts.append(f"\n\n---\n\n# Begin Email Attachment {i}\n**Filename:** {att_filename}\n\n[Error converting attachment: {str(att_err)}]")

                # Combine all content
                content = "\n".join(combined_content_parts)
                save_output(content)

                att_count = len(separate_attachments)
                att_msg = f" with {att_count} attachment(s)" if att_count > 0 else ""
                return {'type': 'success', 'message': f'{filename} converted successfully{att_msg}', 'file_id': file_id, 'filename': output_filename}

            except Exception as email_err:
                return {'type': 'error', 'message': f'{filename} email processing failed: {str(email_err)}'}

        # Handle PDFs specially
        if ext == ".pdf":
            if needs_ocr(input_path):
                processing_status[session_id]['current_status'] = f'{filename} appears to be a scanned PDF, performing OCR...'
                content = ocr_pdf(input_path)
                save_output(content)
                return {'type': 'success', 'message': f'{filename} converted successfully (via OCR)', 'file_id': file_id, 'filename': output_filename}
            else:
                # Try regular text extraction first with MarkItDown
                try:
                    with open(input_path, "rb") as stream:
                        result = MarkItDown().convert_stream(stream)
                        content = strip_westlaw_links(result.markdown)

                        # Check if we got meaningful content
                        if len(content.strip()) < 50:
                            raise Exception("Extracted text too short, trying OCR")

                        save_output(content)
                        return {'type': 'success', 'message': f'{filename} converted successfully (text extraction)', 'file_id': file_id, 'filename': output_filename}
                except:
                    # Fall back to OCR
                    processing_status[session_id]['current_status'] = f'{filename} text extraction failed, trying OCR...'
                    content = ocr_pdf(input_path)
                    save_output(content)
                    return {'type': 'success', 'message': f'{filename} converted successfully (via OCR fallback)', 'file_id': file_id, 'filename': output_filename}
        
        # Check if this is actually an RTF file (common with Westlaw .doc files)
        actual_format = None
        if is_rtf_file(input_path):
            actual_format = "rtf"
            processing_status[session_id]['current_status'] = f'{filename} detected as RTF format'
        
        # Try Pandoc first for non-PDF files
        if ext in PANDOC_FORMATS or actual_format == "rtf":
            try:
                # Use detected format if available, otherwise use extension-based format
                input_format = actual_format or ext[1:]
                
                pandoc_output = subprocess.run(
                    ["pandoc", input_path, "-f", input_format, "-t", "markdown"],
                    capture_output=True,
                    check=True,
                    text=True
                )
                cleaned = strip_westlaw_links(pandoc_output.stdout)
                save_output(cleaned)
                return {'type': 'success', 'message': f'{filename} converted successfully' +
                          (f' (as {input_format})' if actual_format else ''), 'file_id': file_id, 'filename': output_filename}
            except subprocess.CalledProcessError as e:
                error_msg = f"Pandoc failed on {filename}"
                if e.stderr:
                    error_msg += f": {e.stderr[:100]}"
                processing_status[session_id]['current_status'] = error_msg + ", falling back to MarkItDown"
        
        # Fallback to MarkItDown
        with open(input_path, "rb") as stream:
            result = MarkItDown().convert_stream(stream)
            content = strip_westlaw_links(result.markdown)

        save_output(content)
        return {'type': 'success', 'message': f'{filename} converted successfully (via MarkItDown)', 'file_id': file_id, 'filename': output_filename}
        
    except Exception as e:
        return {'type': 'error', 'message': f'{filename} failed to convert: {str(e)}'}
        
    finally:
        # Clean up temp file
        if os.path.exists(input_path):
            os.remove(input_path)

@app.route("/process", methods=["POST"])
def process_files():
    """Process files and return a session ID for status polling."""
    files = request.files.getlist("files")
    session_id = str(uuid.uuid4())
    
    # Initialize status
    processing_status[session_id] = {
        'total': len(files),
        'current': 0,
        'results': [],
        'current_status': 'Starting conversion...',
        'complete': False
    }
    
    # Save files for processing
    file_data_list = []
    for file in files:
        file_data_list.append((file.filename, file.read()))

    # Determine if this is a local request (must capture now, before thread starts)
    save_locally = is_local_request()

    # Process files in background
    def process_all():
        for index, (filename, data) in enumerate(file_data_list):
            processing_status[session_id]['current'] = index + 1
            processing_status[session_id]['current_status'] = f'Processing {filename}...'

            result = process_single_file(filename, data, session_id, save_locally)
            processing_status[session_id]['results'].append(result)

        processing_status[session_id]['complete'] = True
        processing_status[session_id]['current_status'] = 'All files converted!'

    thread = threading.Thread(target=process_all)
    thread.start()
    
    return jsonify({'session_id': session_id})

def is_local_request():
    """Check if the request is from localhost."""
    remote_addr = request.remote_addr
    return remote_addr in ['127.0.0.1', '::1', 'localhost']

@app.route("/status/<session_id>", methods=["GET"])
def get_status(session_id):
    """Get the current processing status."""
    if session_id not in processing_status:
        return jsonify({'error': 'Invalid session ID'}), 404

    status = processing_status[session_id].copy()

    # Add flag indicating if this is a local request (files saved locally)
    status['is_local'] = is_local_request()

    # Clean up completed sessions after returning status
    if status['complete']:
        # Return status one last time before cleanup
        response = jsonify(status)
        # Clean up after a delay
        def cleanup():
            time.sleep(30)  # Keep session alive for 30 seconds after completion
            if session_id in processing_status:
                del processing_status[session_id]
        threading.Thread(target=cleanup).start()
        return response

    return jsonify(status)

@app.route("/download/<file_id>", methods=["GET"])
def download_file(file_id):
    """Download a converted file."""
    if file_id not in converted_files:
        return jsonify({'error': 'File not found'}), 404
    
    file_data = converted_files[file_id]
    
    # Create a temporary file to send
    temp_file = io.BytesIO()
    temp_file.write(file_data['content'].encode('utf-8'))
    temp_file.seek(0)
    
    # Clean up after sending
    def cleanup():
        time.sleep(60)  # Keep file available for 60 seconds
        if file_id in converted_files:
            del converted_files[file_id]
    threading.Thread(target=cleanup).start()
    
    return send_file(
        temp_file,
        as_attachment=True,
        download_name=file_data['filename'],
        mimetype='text/markdown'
    )

@app.route("/", methods=["GET"])
def index():
    html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Legal Markdown Converter</title>
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #0f0f1e 100%) fixed;
          color: #e0e0e0;
          min-height: 100vh;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding: 20px;
          position: relative;
          overflow-y: auto;
        }
        
        /* Animated background effect */
        body::before {
          content: '';
          position: fixed;
          top: -50%;
          left: -50%;
          width: 200%;
          height: 200%;
          background: radial-gradient(circle, rgba(56, 124, 43, 0.1) 0%, transparent 70%);
          animation: pulse 20s ease-in-out infinite;
          pointer-events: none;
        }
        
        @keyframes pulse {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50% { transform: scale(1.1) rotate(180deg); }
        }
        
        .container {
          background: rgba(255, 255, 255, 0.03);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 3rem;
          border-radius: 24px;
          box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
          max-width: 700px;
          width: 100%;
          text-align: center;
          position: relative;
          z-index: 1;
          animation: fadeInUp 0.8s ease-out;
          margin: 40px 0;
        }
        
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .logo {
          width: 60px;
          height: 60px;
          margin: 0 auto 1.5rem;
          background: linear-gradient(135deg, #387c2b 0%, #5cb85c 100%);
          border-radius: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 28px;
          box-shadow: 0 8px 16px rgba(56, 124, 43, 0.3);
          animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        
        h1 {
          font-size: 1.5rem;
          font-weight: 300;
          margin-bottom: 0.5rem;
          color: #888;
          letter-spacing: -0.5px;
        }

        .subtitle {
          font-size: 2rem;
          background: linear-gradient(135deg, #ffffff 0%, #e0e0e0 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin-bottom: 2.5rem;
          font-weight: 400;
        }
        
        form {
          margin-top: 2rem;
        }
        
        input[type="file"] {
          display: none;
        }
        
        .upload-area {
          position: relative;
          margin-bottom: 1.5rem;
          background: rgba(56, 124, 43, 0.05);
          border: 2px dashed rgba(56, 124, 43, 0.3);
          border-radius: 16px;
          padding: 3rem 2rem;
          cursor: pointer;
          transition: all 0.3s ease;
          overflow: hidden;
        }
        
        .upload-area::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(56, 124, 43, 0.1), transparent);
          transition: left 0.5s ease;
        }
        
        .upload-area:hover {
          border-color: rgba(56, 124, 43, 0.6);
          background: rgba(56, 124, 43, 0.08);
        }
        
        .upload-area:hover::before {
          left: 100%;
        }
        
        .upload-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
          opacity: 0.8;
        }
        
        .upload-text {
          font-size: 1.1rem;
          color: #b0b0b0;
          margin-bottom: 0.5rem;
        }
        
        .upload-subtext {
          font-size: 0.9rem;
          color: #666;
        }
        
        .file-list {
          margin: 1.5rem 0;
          text-align: left;
          max-height: 300px;
          overflow-y: auto;
        }
        
        .file-list::-webkit-scrollbar {
          width: 8px;
        }
        
        .file-list::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 4px;
        }
        
        .file-list::-webkit-scrollbar-thumb {
          background: rgba(56, 124, 43, 0.3);
          border-radius: 4px;
        }
        
        .file-list::-webkit-scrollbar-thumb:hover {
          background: rgba(56, 124, 43, 0.5);
        }
        
        .file-list ul {
          list-style: none;
          padding: 0;
        }
        
        .file-list li {
          background: rgba(255, 255, 255, 0.05);
          padding: 0.75rem 1rem;
          margin-bottom: 0.5rem;
          border-radius: 8px;
          font-size: 0.9rem;
          display: flex;
          align-items: center;
          animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        .file-list li::before {
          content: '📄';
          margin-right: 0.75rem;
        }
        
        .submit-button {
          background: linear-gradient(135deg, #387c2b 0%, #5cb85c 100%);
          color: white;
          padding: 1rem 3rem;
          border: none;
          border-radius: 12px;
          font-size: 1.1rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 12px rgba(56, 124, 43, 0.3);
          position: relative;
          overflow: hidden;
        }
        
        .submit-button::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          width: 0;
          height: 0;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          transform: translate(-50%, -50%);
          transition: width 0.6s, height 0.6s;
        }
        
        .submit-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(56, 124, 43, 0.4);
        }
        
        .submit-button:active {
          transform: translateY(0);
        }
        
        .submit-button:hover::before {
          width: 300px;
          height: 300px;
        }
        
        .submit-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }
        
        .progress-bar {
          display: none;
          margin: 2rem 0;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          overflow: hidden;
          height: 8px;
        }
        
        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #387c2b 0%, #5cb85c 100%);
          transition: width 0.3s ease;
          width: 0%;
        }
        
        .progress-text {
          margin-top: 1rem;
          font-size: 0.9rem;
          color: #888;
        }
        
        .results {
          margin-top: 2.5rem;
          text-align: left;
          animation: fadeIn 0.5s ease-out;
          max-height: 400px;
          overflow-y: auto;
        }
        
        .results::-webkit-scrollbar {
          width: 8px;
        }
        
        .results::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 4px;
        }
        
        .results::-webkit-scrollbar-thumb {
          background: rgba(56, 124, 43, 0.3);
          border-radius: 4px;
        }
        
        .results::-webkit-scrollbar-thumb:hover {
          background: rgba(56, 124, 43, 0.5);
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        .results h2 {
          font-size: 1.3rem;
          font-weight: 400;
          margin-bottom: 1rem;
          color: #e0e0e0;
        }
        
        .result-item {
          padding: 1rem;
          margin-bottom: 0.75rem;
          border-radius: 10px;
          font-size: 0.95rem;
          display: flex;
          align-items: center;
          animation: slideIn 0.3s ease-out;
          backdrop-filter: blur(10px);
        }
        
        .result-success {
          background: rgba(56, 124, 43, 0.1);
          border: 1px solid rgba(56, 124, 43, 0.2);
          color: #90EE90;
        }
        
        .result-error {
          background: rgba(220, 53, 69, 0.1);
          border: 1px solid rgba(220, 53, 69, 0.2);
          color: #ff6b6b;
        }
        
        .result-warning {
          background: rgba(255, 193, 7, 0.1);
          border: 1px solid rgba(255, 193, 7, 0.2);
          color: #ffd93d;
        }
        
        .result-info {
          background: rgba(0, 123, 255, 0.1);
          border: 1px solid rgba(0, 123, 255, 0.2);
          color: #74c0fc;
        }
        
        .result-icon {
          margin-right: 0.75rem;
          font-size: 1.2rem;
        }
        
        .download-link {
          margin-left: auto;
          color: #5cb85c;
          text-decoration: none;
          font-weight: 500;
          padding: 0.25rem 0.75rem;
          border: 1px solid rgba(92, 184, 92, 0.3);
          border-radius: 6px;
          transition: all 0.3s ease;
        }
        
        .download-link:hover {
          background: rgba(92, 184, 92, 0.1);
          border-color: rgba(92, 184, 92, 0.5);
        }
        
        .reset-button {
          display: block;
          margin: 1rem auto 0;
          background: none;
          color: #888;
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 0.5rem 1.5rem;
          border-radius: 8px;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        
        .reset-button:hover {
          color: #e0e0e0;
          border-color: rgba(255, 255, 255, 0.2);
          background: rgba(255, 255, 255, 0.05);
        }
        
        .footer {
          margin-top: 3rem;
          font-size: 0.85rem;
          color: #666;
        }

        .disclaimer-link {
          color: #888;
          text-decoration: underline;
          cursor: pointer;
          transition: color 0.3s ease;
        }

        .disclaimer-link:hover {
          color: #aaa;
        }

        .modal-overlay {
          display: none;
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.8);
          z-index: 1000;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }

        .modal-overlay.active {
          display: flex;
        }

        .modal-content {
          background: linear-gradient(135deg, #1a1a2e 0%, #16162a 100%);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          max-width: 700px;
          width: 100%;
          max-height: 80vh;
          overflow-y: auto;
          padding: 2rem;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
          animation: modalSlideIn 0.3s ease-out;
        }

        @keyframes modalSlideIn {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .modal-content h2 {
          color: #ff6b6b;
          margin-bottom: 1.5rem;
          font-size: 1.5rem;
          text-align: center;
        }

        .modal-body {
          color: #ccc;
          font-size: 0.9rem;
          line-height: 1.6;
        }

        .modal-body p {
          margin-bottom: 1rem;
        }

        .modal-body ul {
          margin: 1rem 0 1rem 1.5rem;
        }

        .modal-body li {
          margin-bottom: 0.5rem;
        }

        .modal-body h3 {
          color: #5cb85c;
          font-size: 1.1rem;
          margin-top: 1.5rem;
          margin-bottom: 0.5rem;
        }

        .modal-body h3:first-of-type {
          margin-top: 0.5rem;
        }

        .modal-body a {
          color: #74c0fc;
          text-decoration: none;
        }

        .modal-body a:hover {
          text-decoration: underline;
        }

        .modal-close {
          display: block;
          width: 100%;
          margin-top: 1.5rem;
          padding: 1rem;
          background: linear-gradient(135deg, #387c2b 0%, #5cb85c 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .modal-close:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(56, 124, 43, 0.4);
        }
        
        /* Drag and drop styles */
        .upload-area.dragover {
          background: rgba(56, 124, 43, 0.15);
          border-color: #5cb85c;
          transform: scale(1.02);
        }
        
        .hidden {
          display: none !important;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="logo">⚖️</div>
        <h1>Austin Brister's</h1>
        <div class="subtitle">Legal Markdown Converter</div>
        
        <form id="upload-form">
          <div class="upload-area" onclick="document.getElementById('file-upload').click()">
            <div class="upload-icon">📁</div>
            <div class="upload-text">Drop files here or click to browse</div>
            <div class="upload-subtext">Supports Word, RTF, HTML, PDFs (including scanned), Emails (EML/MSG), ZIP archives, and more</div>
          </div>
          
          <input id="file-upload" type="file" name="files" multiple onchange="showFileNames(this)">
          
          <div class="file-list">
            <ul id="selected-files"></ul>
          </div>
          
          <button type="submit" class="submit-button">Convert to Markdown</button>
          <button class="reset-button hidden" id="reset-button" onclick="clearResults()">Clear and Start New Conversion</button>
        </form>
        
        <div class="progress-bar" id="progress-bar">
          <div class="progress-fill" id="progress-fill"></div>
        </div>
        <div class="progress-text" id="progress-text"></div>
        
        <div class="results hidden" id="results">
          <h2>Conversion Results</h2>
          <div id="results-list"></div>
        </div>
        
        <div class="footer">
          Austin Brister - Houston, Texas
          <br><br>
          <a href="#" class="disclaimer-link" onclick="showDisclaimer(); return false;">Disclaimer</a>
          &nbsp;&bull;&nbsp;
          <a href="#" class="disclaimer-link" onclick="showLicenses(); return false;">Open Source Licenses</a>
        </div>
      </div>

      <!-- Licenses Modal -->
      <div class="modal-overlay" id="licenses-modal">
        <div class="modal-content">
          <h2>Open Source Licenses</h2>
          <div class="modal-body">
            <p>This software incorporates the following open source components:</p>

            <h3>Microsoft MarkItDown</h3>
            <p>Core document conversion library<br>
            <em>MIT License - Copyright (c) Microsoft Corporation</em><br>
            <a href="https://github.com/microsoft/markitdown" target="_blank">github.com/microsoft/markitdown</a></p>

            <h3>Flask</h3>
            <p>Web framework<br>
            <em>BSD-3-Clause License - Copyright (c) Pallets</em><br>
            <a href="https://flask.palletsprojects.com/" target="_blank">flask.palletsprojects.com</a></p>

            <h3>PyMuPDF</h3>
            <p>PDF processing<br>
            <em>AGPL-3.0 License (or Commercial) - Copyright (c) Artifex Software</em><br>
            <a href="https://pymupdf.readthedocs.io/" target="_blank">pymupdf.readthedocs.io</a></p>

            <h3>Tesseract OCR</h3>
            <p>Optical character recognition<br>
            <em>Apache-2.0 License - Copyright (c) Google</em><br>
            <a href="https://github.com/tesseract-ocr/tesseract" target="_blank">github.com/tesseract-ocr/tesseract</a></p>

            <h3>Pandoc</h3>
            <p>Document format conversion<br>
            <em>GPL-2.0 License - Copyright (c) John MacFarlane</em><br>
            <a href="https://pandoc.org/" target="_blank">pandoc.org</a></p>

            <h3>Pillow</h3>
            <p>Image processing<br>
            <em>HPND License - Copyright (c) Jeffrey A. Clark and contributors</em><br>
            <a href="https://python-pillow.org/" target="_blank">python-pillow.org</a></p>

            <h3>extract-msg</h3>
            <p>Outlook MSG file parsing<br>
            <em>GPL-3.0 License</em><br>
            <a href="https://github.com/TeamMsgExtractor/msg-extractor" target="_blank">github.com/TeamMsgExtractor/msg-extractor</a></p>

            <h3>markdown-it-py</h3>
            <p>Markdown parsing<br>
            <em>MIT License</em><br>
            <a href="https://github.com/executablebooks/markdown-it-py" target="_blank">github.com/executablebooks/markdown-it-py</a></p>

            <hr style="border-color: #333; margin: 1.5rem 0;">

            <h3>Network Access</h3>
            <p>Others on your local network can access this tool at:<br>
            <strong style="color: #5cb85c; font-size: 1.1rem;">http://{{ local_ip }}:5050</strong></p>
            <p style="font-size: 0.8rem; color: #888;">(This address may change if your network assigns a new IP)</p>

            <hr style="border-color: #333; margin: 1.5rem 0;">

            <h3>Legal Markdown Converter</h3>
            <p>This application<br>
            <em>Copyright (c) 2025 Austin Brister. All rights reserved.</em></p>
          </div>
          <button class="modal-close" onclick="hideLicenses()">Close</button>
        </div>
      </div>

      <!-- Disclaimer Modal -->
      <div class="modal-overlay" id="disclaimer-modal">
        <div class="modal-content">
          <h2>Disclaimer</h2>
          <div class="modal-body">
            <p><strong>USE AT YOUR OWN RISK</strong></p>
            <p>This software is provided "as is" without warranty of any kind, express or implied. This is experimental code that may not properly convert all files or filetypes, and the lack of debugging and error messages means it likely will not make errors and omissions obvious to the end user. In addition, this tool is intended for convenient document conversion purposes only to be used in temporary AI/LLM uses, and should not be used for any backup or file retention purposes.</p>
            <p>The author(s) and contributors make no representations or warranties regarding:</p>
            <ul>
              <li>The accuracy, completeness, or reliability of any conversions</li>
              <li>The fitness of this software for any particular purpose</li>
              <li>The preservation of document formatting, content, or structure</li>
              <li>The security or confidentiality of any documents processed</li>
            </ul>
            <p><strong>LIMITATION OF LIABILITY</strong></p>
            <p>In no event shall the author(s), contributors, or McGinnis Lochridge LLP be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, loss of data, business interruption, or any other commercial damages or losses) arising out of or in connection with the use or inability to use this software.</p>
            <p>By using this software, you acknowledge that you have read this disclaimer and agree to assume all risks associated with its use. You are solely responsible for verifying the accuracy of any converted documents.</p>
            <p><strong>This tool is not a substitute for professional document review.</strong></p>
          </div>
          <button class="modal-close" onclick="hideDisclaimer()">I Understand</button>
        </div>
      </div>
      
      <script>
        const form = document.getElementById('upload-form');
        const fileInput = document.getElementById('file-upload');
        const progressBar = document.getElementById('progress-bar');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const results = document.getElementById('results');
        const resultsList = document.getElementById('results-list');
        const submitButton = form.querySelector('.submit-button');
        
        const icons = {
          'success': '✅',
          'error': '❌',
          'warning': '⚠️',
          'info': 'ℹ️'
        };
        
        let statusInterval = null;
        let lastResultCount = 0;
        let isLocalRequest = false; // Track if user is on localhost
        
        function showFileNames(input) {
          const list = document.getElementById("selected-files");
          list.innerHTML = "";
          for (let i = 0; i < input.files.length; i++) {
            const li = document.createElement("li");
            li.textContent = input.files[i].name;
            list.appendChild(li);
          }
        }
        
        function clearResults() {
          window.location.href = "/";
        }
        
        function downloadFile(fileId, filename) {
          const link = document.createElement('a');
          link.href = `/download/${fileId}`;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
        
        function addResult(result) {
          const resultItem = document.createElement('div');
          resultItem.className = `result-item result-${result.type}`;

          let content = `
            <span class='result-icon'>${icons[result.type] || '•'}</span>
            <span>${result.message}</span>
          `;

          // For successful conversions, show different UI based on local vs remote
          if (result.type === 'success' && result.file_id) {
            if (isLocalRequest) {
              // Local user - file is saved to folder, show indicator
              content += `<span class="download-link" style="cursor: default; opacity: 0.7;">Saved to folder</span>`;
            } else {
              // Remote user - show download button
              content += `<a href="#" class="download-link" onclick="downloadFile('${result.file_id}', '${result.filename}'); return false;">Download</a>`;
            }
          }

          resultItem.innerHTML = content;
          resultsList.appendChild(resultItem);

          // Auto-download only for remote users
          if (result.type === 'success' && result.file_id && !isLocalRequest) {
            setTimeout(() => {
              downloadFile(result.file_id, result.filename);
            }, 500); // Small delay to ensure UI updates first
          }

          // Auto-scroll to latest result
          resultsList.scrollTop = resultsList.scrollHeight;
        }
        
        async function checkStatus(sessionId) {
          try {
            const response = await fetch(`/status/${sessionId}`);
            const data = await response.json();

            if (data.error) {
              throw new Error(data.error);
            }

            // Track if this is a local request (files saved to folder)
            isLocalRequest = data.is_local || false;

            // Update progress
            const percent = (data.current / data.total) * 100;
            progressFill.style.width = percent + '%';
            progressText.textContent = data.current_status || 'Processing...';

            // Add new results
            if (data.results.length > lastResultCount) {
              for (let i = lastResultCount; i < data.results.length; i++) {
                addResult(data.results[i]);
              }
              lastResultCount = data.results.length;
            }

            // Check if complete
            if (data.complete) {
              clearInterval(statusInterval);
              submitButton.disabled = false;
              submitButton.textContent = 'Convert to Markdown';
            }
          } catch (error) {
            console.error('Status check error:', error);
            clearInterval(statusInterval);
            progressText.textContent = 'Error checking status';
            submitButton.disabled = false;
            submitButton.textContent = 'Convert to Markdown';
          }
        }
        
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          
          if (fileInput.files.length === 0) {
            alert('Please select files to convert');
            return;
          }
          
          // Disable submit button
          submitButton.disabled = true;
          submitButton.textContent = 'Converting...';
          
          // Show progress bar
          progressBar.style.display = 'block';
          progressFill.style.width = '0%';
          progressText.textContent = 'Starting conversion...';
          
          // Clear previous results
          resultsList.innerHTML = '';
          lastResultCount = 0;
          results.classList.remove('hidden');
          document.getElementById('reset-button').classList.remove('hidden');

          // Create FormData
          const formData = new FormData();
          for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('files', fileInput.files[i]);
          }
          
          try {
            // Send files for processing
            const response = await fetch('/process', {
              method: 'POST',
              body: formData
            });
            
            const data = await response.json();
            
            if (!data.session_id) {
              throw new Error('No session ID received');
            }
            
            // Start polling for status
            statusInterval = setInterval(() => {
              checkStatus(data.session_id);
            }, 500); // Poll every 500ms
          
          } catch (error) {
            console.error('Upload error:', error);
            progressText.textContent = 'Error during upload';
            submitButton.disabled = false;
            submitButton.textContent = 'Convert to Markdown';
          }
        });
        
        // Drag and drop functionality
        const uploadArea = document.querySelector('.upload-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
          uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
          e.preventDefault();
          e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
          uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
          uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
          uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
          uploadArea.classList.remove('dragover');
        }
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
          const dt = e.dataTransfer;
          const files = dt.files;
          fileInput.files = files;
          showFileNames(fileInput);
        }

        // Disclaimer modal functions
        function showDisclaimer() {
          document.getElementById('disclaimer-modal').classList.add('active');
        }

        function hideDisclaimer() {
          document.getElementById('disclaimer-modal').classList.remove('active');
        }

        // Licenses modal functions
        function showLicenses() {
          document.getElementById('licenses-modal').classList.add('active');
        }

        function hideLicenses() {
          document.getElementById('licenses-modal').classList.remove('active');
        }

        // Close modals when clicking outside
        document.getElementById('disclaimer-modal').addEventListener('click', function(e) {
          if (e.target === this) {
            hideDisclaimer();
          }
        });

        document.getElementById('licenses-modal').addEventListener('click', function(e) {
          if (e.target === this) {
            hideLicenses();
          }
        });
      </script>
    </body>
    </html>
    """
    return render_template_string(html, local_ip=get_local_ip())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
