import io 
import logging
import os 
import sys 
from I_document_handler import IDocumentHandler
from typing import List, Dict
from bs4 import BeautifulSoup

if __package__:
    from ...logging_utils import configure_json_logging, log, LogLevel
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import configure_json_logging, log, LogLevel
    from app.utils import sanitize_and_standardize_doc_id

class TextFromHtml(IDocumentHandler):
    def __init__(self):
        configure_json_logging()
    
    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from HTML"""
        try:
            content = stream.read()
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(separator="\n").strip()

            doc_metadata = {
                "source_filename": blob_name,
                "title": soup.title.string if soup.title else "",
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": 1, 
                "file_extension": "html",
                "url": source_url
            }

            page_content = {
                "id":sanitize_and_standardize_doc_id(f"{blob_name}"),
                "page_number": 1,
                "content": text,
                **doc_metadata
            }

            pages_data = [page_content]

            return pages_data
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message = {
                    "message":f"Failed to extract TXT content from , {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e)
                }
            )
            raise

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "demo.html")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromHtml()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.html",
            source_url=""
        )
        print(result)