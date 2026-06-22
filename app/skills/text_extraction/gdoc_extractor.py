import io
import json
import os
import sys
from typing import Dict, List

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromGoogleDocShortcut(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract available metadata from downloaded .gdoc shortcut files."""
        try:
            stream.seek(0)
            raw = stream.read().decode("utf-8", errors="ignore")
            data = json.loads(raw)

            title = data.get("title") or blob_name
            url = data.get("url") or source_url
            doc_id = data.get("doc_id") or data.get("resource_id") or ""

            content_lines = [
                f"title: {title}",
                f"url: {url}",
                f"doc_id: {doc_id}",
            ]

            doc_metadata = {
                "source_filename": blob_name,
                "title": title,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": 1,
                "file_extension": "gdoc",
                "url": url,
            }

            return [{
                "id": sanitize_and_standardize_doc_id(f"{blob_name}"),
                "page_number": 1,
                "content": "\n".join(content_lines),
                **doc_metadata,
            }]
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from GDOC file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.gdoc")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromGoogleDocShortcut()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)