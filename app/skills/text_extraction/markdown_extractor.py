import io
import os
import sys
from typing import Dict, List

import markdown
from bs4 import BeautifulSoup

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromMarkdown(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from Markdown."""
        try:
            stream.seek(0)
            raw_markdown = stream.read().decode("utf-8", errors="ignore")
            html = markdown.markdown(raw_markdown)
            text = BeautifulSoup(html, "html.parser").get_text(separator="\n").strip()

            doc_metadata = {
                "source_filename": blob_name,
                "title": blob_name,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": 1,
                "file_extension": "md",
                "url": source_url,
            }

            return [{
                "id": sanitize_and_standardize_doc_id(f"{blob_name}"),
                "page_number": 1,
                "content": text,
                **doc_metadata,
            }]
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from Markdown file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.md")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromMarkdown()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)