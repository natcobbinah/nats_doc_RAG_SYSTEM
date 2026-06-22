import io
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromEpub(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def _process_item(self, args: Tuple[bytes, int, str]) -> Dict:
        content, page_number, name = args
        text = BeautifulSoup(content, "html.parser").get_text(separator="\n").strip()
        return {
            "id": sanitize_and_standardize_doc_id(f"{name}-{page_number}"),
            "page_number": page_number,
            "entry_name": name,
            "content": text,
        }

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from EPUB."""
        temp_path = ""
        try:
            stream.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as temp_file:
                temp_file.write(stream.read())
                temp_path = temp_file.name

            book = epub.read_epub(temp_path)
            docs = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

            title_meta = book.get_metadata("DC", "title")
            title = title_meta[0][0] if title_meta else blob_name

            doc_metadata = {
                "source_filename": blob_name,
                "title": title,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": len(docs),
                "file_extension": "epub",
                "url": source_url,
            }

            pages_data: List[Dict] = []
            with ThreadPoolExecutor() as executor:
                futures = []
                for i, item in enumerate(docs):
                    futures.append(executor.submit(self._process_item, (item.get_content(), i + 1, item.get_name())))

                for future in as_completed(futures):
                    pages_data.append({**future.result(), **doc_metadata})

            return sorted(pages_data, key=lambda item: int(item["page_number"]))
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from EPUB file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.epub")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromEpub()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)