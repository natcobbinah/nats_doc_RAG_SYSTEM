import io
import os
import shutil
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
from ocr_handler import OcrHandler


from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromImage(IDocumentHandler):
    def __init__(self, ocr_handler):
        self.ocr_hanlder = ocr_handler
        configure_json_logging()

    def extract_content_from_document(self, stream, blob_name, source_url):
        """
        Extract text from image using OCR, enrich with metadata
        """
        try:
            _, ext = os.path.splitext(blob_name.lower())
            ext = ext.lstrip(".")
            content_type = f"image/{ext}"
            if ext == "jpg":
                content_type = "image/jpeg"

            ocr_pages = self.ocr_hanlder.perform_ocr(stream, blob_name, content_type=content_type)

            if not ocr_pages:
                return []
            
            doc_metadata = {
                "source_filename": blob_name,
                "title": blob_name,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": len(ocr_pages),
                "file_extension": ext, 
                "url": source_url
            }

            for index, page in enumerate(ocr_pages, start=1):
                page.update(doc_metadata)
                page_number = page.get("page_number", index)
                page["id"] = sanitize_and_standardize_doc_id(f"{blob_name}-page-{page_number}")
            
            return ocr_pages

        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Error processing image OCR, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )


if __name__ == "__main__":
    ocr_handler = OcrHandler()

    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/laposte.png")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromImage(ocr_handler=ocr_handler)
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name=dummy_file_path,
            source_url=""
        )
        print(result)