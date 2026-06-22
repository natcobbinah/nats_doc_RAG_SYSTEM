import io 
import logging
import os 
import sys 
from I_document_handler import IDocumentHandler
from typing import List, Dict

if __package__:
    from ...logging_utils import configure_json_logging, log, LogLevel
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import configure_json_logging, log, LogLevel
    from app.utils import sanitize_and_standardize_doc_id

class TextFromText(IDocumentHandler):
    def __init__(self):
        configure_json_logging()
    
    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from TXT"""
        try:
            text = stream.read().decode("utf-8").strip()

            doc_metadata = {
                "source_filename": blob_name,
                "title": blob_name,
                "author": "",
                "creation_date": "",
                "modification_data":"",
                "total_pages": 1,
                "file_extension": "txt",
                "url": source_url
            }

            page_content = {
                "id": sanitize_and_standardize_doc_id(f"{blob_name}"),
                "page_number":1,
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
    dummy_file_path = os.path.join(os.path.dirname(__file__), "dummy.txt")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromText()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="dummy.txt",
            source_url=""
        )
        print(result)