# Legal Markdown Converter - Email (EML/MSG) to PDF Converter
"""
Converts .eml and .msg email files to a combined PDF that includes:
1. The email body
2. Cover sheets before each attachment
3. All attachments converted/embedded

This PDF can then be processed by the main converter for markdown output.
"""

import os
import email
import tempfile
from email import policy
from email.parser import BytesParser
from datetime import datetime
from io import BytesIO

# PDF generation
import fitz  # PyMuPDF - already a dependency

# For MSG files (Outlook format)
try:
    import extract_msg
    HAS_EXTRACT_MSG = True
except ImportError:
    HAS_EXTRACT_MSG = False


def parse_eml(file_path_or_bytes):
    """Parse an EML file and extract headers, body, and attachments."""
    if isinstance(file_path_or_bytes, bytes):
        msg = BytesParser(policy=policy.default).parsebytes(file_path_or_bytes)
    else:
        with open(file_path_or_bytes, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)

    # Extract headers
    headers = {
        'from': msg.get('From', ''),
        'to': msg.get('To', ''),
        'cc': msg.get('Cc', ''),
        'subject': msg.get('Subject', '(No Subject)'),
        'date': msg.get('Date', ''),
    }

    # Extract body
    body = ''
    html_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))

            # Skip attachments when looking for body
            if 'attachment' in content_disposition:
                continue

            if content_type == 'text/plain':
                try:
                    body = part.get_content()
                except:
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
            elif content_type == 'text/html' and not body:
                try:
                    html_body = part.get_content()
                except:
                    html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
    else:
        content_type = msg.get_content_type()
        if content_type == 'text/plain':
            body = msg.get_content()
        elif content_type == 'text/html':
            html_body = msg.get_content()

    # Use HTML body if no plain text available
    if not body and html_body:
        # Simple HTML to text conversion
        import re
        body = re.sub(r'<[^>]+>', '', html_body)
        body = body.replace('&nbsp;', ' ').replace('&amp;', '&')
        body = body.replace('&lt;', '<').replace('&gt;', '>')

    # Extract attachments
    attachments = []
    for part in msg.walk():
        content_disposition = str(part.get('Content-Disposition', ''))
        if 'attachment' in content_disposition or part.get_filename():
            filename = part.get_filename()
            if filename:
                payload = part.get_payload(decode=True)
                if payload:
                    attachments.append({
                        'filename': filename,
                        'data': payload,
                        'content_type': part.get_content_type()
                    })

    return {
        'headers': headers,
        'body': body,
        'attachments': attachments
    }


def parse_msg(file_path_or_bytes):
    """Parse an MSG file (Outlook format) and extract headers, body, and attachments."""
    if not HAS_EXTRACT_MSG:
        raise ImportError("extract-msg library is required for MSG files. Install with: pip install extract-msg")

    # extract-msg needs a file path, so write bytes to temp file if needed
    if isinstance(file_path_or_bytes, bytes):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.msg') as tmp:
            tmp.write(file_path_or_bytes)
            tmp_path = tmp.name
        msg = extract_msg.Message(tmp_path)
        os.unlink(tmp_path)
    else:
        msg = extract_msg.Message(file_path_or_bytes)

    # Extract headers
    headers = {
        'from': msg.sender or '',
        'to': msg.to or '',
        'cc': msg.cc or '',
        'subject': msg.subject or '(No Subject)',
        'date': str(msg.date) if msg.date else '',
    }

    # Extract body
    body = msg.body or ''

    # Extract attachments
    attachments = []
    for attachment in msg.attachments:
        if hasattr(attachment, 'data') and attachment.data:
            attachments.append({
                'filename': attachment.longFilename or attachment.shortFilename or 'attachment',
                'data': attachment.data,
                'content_type': getattr(attachment, 'mimetype', 'application/octet-stream')
            })

    msg.close()

    return {
        'headers': headers,
        'body': body,
        'attachments': attachments
    }


def create_cover_sheet_pdf(title, subtitle=None):
    """Create a simple PDF cover sheet."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Letter size

    # Title
    title_rect = fitz.Rect(50, 300, 562, 400)
    page.insert_textbox(
        title_rect,
        title,
        fontsize=24,
        fontname="helv",
        align=fitz.TEXT_ALIGN_CENTER
    )

    # Subtitle
    if subtitle:
        subtitle_rect = fitz.Rect(50, 400, 562, 450)
        page.insert_textbox(
            subtitle_rect,
            subtitle,
            fontsize=14,
            fontname="helv",
            align=fitz.TEXT_ALIGN_CENTER,
            color=(0.4, 0.4, 0.4)
        )

    return doc


def create_email_body_pdf(email_data):
    """Create a PDF from the email headers and body."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Letter size

    headers = email_data['headers']
    body = email_data['body']

    # Build header text
    header_lines = []
    if headers.get('from'):
        header_lines.append(f"From: {headers['from']}")
    if headers.get('to'):
        header_lines.append(f"To: {headers['to']}")
    if headers.get('cc'):
        header_lines.append(f"Cc: {headers['cc']}")
    if headers.get('date'):
        header_lines.append(f"Date: {headers['date']}")
    if headers.get('subject'):
        header_lines.append(f"Subject: {headers['subject']}")

    header_text = '\n'.join(header_lines)

    # Insert headers
    y_pos = 50
    header_rect = fitz.Rect(50, y_pos, 562, y_pos + 120)
    page.insert_textbox(
        header_rect,
        header_text,
        fontsize=10,
        fontname="helv"
    )

    # Divider line
    y_pos = 180
    page.draw_line(fitz.Point(50, y_pos), fitz.Point(562, y_pos), color=(0.7, 0.7, 0.7))

    # Body text - handle long bodies across multiple pages
    y_pos = 200
    remaining_body = body

    while remaining_body:
        body_rect = fitz.Rect(50, y_pos, 562, 742)

        # Insert text and get overflow
        rc = page.insert_textbox(
            body_rect,
            remaining_body,
            fontsize=10,
            fontname="helv"
        )

        if rc < 0:
            # Text overflowed, need new page
            # Estimate how much text fit (rough approximation)
            chars_per_line = 90
            lines_per_page = int((742 - y_pos) / 12)
            chars_fit = chars_per_line * lines_per_page
            remaining_body = remaining_body[chars_fit:]

            if remaining_body.strip():
                page = doc.new_page(width=612, height=792)
                y_pos = 50
            else:
                break
        else:
            break

    return doc


def attachment_to_pdf(attachment_data, attachment_filename):
    """Convert an attachment to PDF format for merging.

    Returns a PyMuPDF document or None if conversion not possible.
    """
    ext = os.path.splitext(attachment_filename)[1].lower()
    data = attachment_data

    # If it's already a PDF, just open it
    if ext == '.pdf':
        try:
            return fitz.open(stream=data, filetype='pdf')
        except:
            return None

    # Images can be converted to PDF
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif']:
        try:
            doc = fitz.open()
            img_doc = fitz.open(stream=data, filetype=ext[1:])

            # Get image as a page
            pdfbytes = img_doc.convert_to_pdf()
            img_pdf = fitz.open(stream=pdfbytes, filetype='pdf')
            doc.insert_pdf(img_pdf)

            return doc
        except:
            return None

    # For other file types, create a placeholder page
    # The main converter will handle these separately
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    text_rect = fitz.Rect(50, 350, 562, 450)
    page.insert_textbox(
        text_rect,
        f"[Attachment: {attachment_filename}]\n\nThis attachment type requires separate processing.",
        fontsize=12,
        fontname="helv",
        align=fitz.TEXT_ALIGN_CENTER,
        color=(0.5, 0.5, 0.5)
    )

    return doc


def convert_email_to_pdf(file_path_or_bytes, original_filename):
    """
    Convert an EML or MSG file to a combined PDF with attachments.

    Returns:
        tuple: (pdf_bytes, list of non-convertible attachments for separate processing)
    """
    ext = os.path.splitext(original_filename)[1].lower()

    # Parse the email
    if ext == '.eml':
        email_data = parse_eml(file_path_or_bytes)
    elif ext == '.msg':
        email_data = parse_msg(file_path_or_bytes)
    else:
        raise ValueError(f"Unsupported email format: {ext}")

    # Create the combined PDF
    combined_pdf = fitz.open()
    separate_attachments = []

    # Add email body
    body_pdf = create_email_body_pdf(email_data)
    combined_pdf.insert_pdf(body_pdf)
    body_pdf.close()

    # Process attachments
    for i, attachment in enumerate(email_data['attachments'], 1):
        filename = attachment['filename']
        data = attachment['data']
        ext_att = os.path.splitext(filename)[1].lower()

        # Create cover sheet for this attachment
        cover = create_cover_sheet_pdf(
            f"# Begin Email Attachment {i}",
            f'Filename: "{filename}"'
        )
        combined_pdf.insert_pdf(cover)
        cover.close()

        # Try to convert attachment to PDF
        if ext_att in ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif']:
            att_pdf = attachment_to_pdf(data, filename)
            if att_pdf:
                combined_pdf.insert_pdf(att_pdf)
                att_pdf.close()
            else:
                # Couldn't convert, add to separate processing list
                separate_attachments.append(attachment)
        else:
            # Non-image/PDF attachments need separate processing
            # Add a placeholder in the combined PDF
            placeholder = fitz.open()
            page = placeholder.new_page(width=612, height=792)

            text_rect = fitz.Rect(50, 350, 562, 450)
            page.insert_textbox(
                text_rect,
                f"[See converted attachment below]\n\nOriginal file: {filename}",
                fontsize=12,
                fontname="helv",
                align=fitz.TEXT_ALIGN_CENTER,
                color=(0.5, 0.5, 0.5)
            )
            combined_pdf.insert_pdf(placeholder)
            placeholder.close()

            # Add to separate processing list for MarkItDown conversion
            separate_attachments.append(attachment)

    # Get PDF bytes
    pdf_bytes = combined_pdf.tobytes()
    combined_pdf.close()

    return pdf_bytes, separate_attachments


def process_email_file(file_path_or_bytes, original_filename):
    """
    Main entry point for email processing.

    Converts email to PDF and returns:
    - pdf_bytes: The combined PDF of email + attachment cover sheets
    - attachments: List of attachments that need separate MarkItDown processing
    """
    return convert_email_to_pdf(file_path_or_bytes, original_filename)
