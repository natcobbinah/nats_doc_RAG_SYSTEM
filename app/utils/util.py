import re
import mimetypes
import os

def sanitize_and_standardize_doc_id(doc_id: str) -> str:
    """
    Standardizes uploaded document name
    """
    if not doc_id:
        return "unknown_doc"
    
    doc_id = str(doc_id).strip()

    # Replace invalid characters with underscores
    # valid characters: letters, digits, underscores, dash and equals sign
    # Forward/backward slashes are replaced with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_\-=]', '_', doc_id)

    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing underscores or dashes
    sanitized = sanitized.strip('_-')

    # ensure it is not empty after sanitization
    if not sanitized:
        sanitized = "unknown_doc"

    # ensure it doesn't exceed 1024
    if len(sanitized) > 1024:
        sanitized = sanitized[:512] + "_" + sanitized[-511:]
    
    return sanitized

def get_mimetype(filename) -> str:
    guessed_mime_type, _ = mimetypes.guess_type(filename, strict=True)
    return guessed_mime_type or "application/octet-stream"


def extract_filename(file_path: str) -> str:
    """
    Extract a file name from a path using os.path utilities.
    """
    if not file_path:
        return ""

    return os.path.basename(os.path.normpath(file_path))
